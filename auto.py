import base64
import asyncio
import os
import sys
import time
import csv
from datetime import datetime
from typing import Annotated, Sequence, List, TypedDict, Union, Optional

from dotenv import load_dotenv
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage
from langchain_core.tools import tool
from pydantic import BaseModel, Field, ValidationError
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from playwright.async_api import async_playwright, Page, Browser

# --- CRITICAL: DO NOT CHANGE EVENT LOOP POLICY ON WINDOWS ---
load_dotenv()

# Global browser state
browser: Union[Browser, None] = None
page: Union[Page, None] = None

# --- CONFIGURATION ---
PACING_DELAY = 5  # Seconds to wait between calls (Safety for Free Tier)

# --- 0. Power BI Logger ---

def log_to_csv(url, task, summary_text, status):
    """Saves run details to a CSV file for Power BI analysis."""
    file_name = "agent_history.csv"
    file_exists = os.path.isfile(file_name)
    
    try:
        with open(file_name, mode='a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Write header only if the file is new
            if not file_exists:
                writer.writerow(["Timestamp", "Target URL", "Task", "Summary Length", "Status", "Full Report"])
            
            # Write the data row
            writer.writerow([
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                url,
                task,
                len(summary_text),
                status,
                summary_text[:5000] # Truncate slightly to keep CSV size manageable
            ])
        print(f">> Power BI Data: Logged to '{file_name}'")
    except Exception as e:
        print(f">> Warning: CSV Logging failed: {e}")

# --- 1. Data Models ---

class PageAnalysis(BaseModel):
    summary: str = Field(description="A concise summary of the content found. Include specific facts, dates, or technical details found in the text.")
    should_scroll: bool = Field(description="True if we need to scroll down to find more unique content. False if we reached the footer or have enough info.")

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    url: Union[str, None]
    current_context: Optional[dict]
    summaries: List[str]
    task: str

# --- 2. Smart Retry Wrapper ---

async def call_llm_with_retry(llm_func, *args, **kwargs):
    """Calls LLM with auto-retry, auto-pacing, and clean error handling."""
    
    print(f"   (Pacing for {PACING_DELAY}s...)")
    await asyncio.sleep(PACING_DELAY)

    max_retries = 3
    for attempt in range(max_retries):
        try:
            return await llm_func(*args, **kwargs)
        except Exception as e:
            error_msg = str(e)
            
            if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
                wait_time = 30 * (attempt + 1)
                print(f"\n!!! Rate Limit Hit. Cooling down for {wait_time}s... !!!")
                await asyncio.sleep(wait_time)
                continue
            
            if "PERMISSION_DENIED" in error_msg:
                print("\n!!! CRITICAL: API Key Invalid or Leaked. Check .env !!!")
                return None

            if "ValidationError" in error_msg or "validation error" in error_msg:
                print(f"\n   [Attempt {attempt+1}] Model output parsing failed. Retrying...")
                continue

            print(f"   [Attempt {attempt+1}] Unexpected error: {e}")
            
    print("!!! Max retries exceeded. Moving on.")
    return None

# --- 3. Smart Tools ---

async def initialize_browser():
    global browser, page
    print('>> Init Browser')
    pw = await async_playwright().start()
    browser = await pw.chromium.launch(headless=False)
    page = await browser.new_page()
    await page.set_viewport_size({"width": 1280, "height": 1200}) 

async def close_browser():
    global browser
    if browser:
        try: await browser.close()
        except: pass

@tool
async def navigate_url(url: str) -> str:
    """Navigates the browser to the specified URL."""
    global page
    print(f'>> Navigating: {url}')
    if page:
        try:
            await page.goto(url, wait_until='domcontentloaded', timeout=60000)
        except Exception as e:
            print(f">> Navigation warning: {e}")
    return "Done"

@tool
async def capture_page_context() -> dict:
    """Captures BOTH the screenshot (vision) and raw text (precision)."""
    global page
    if not page: return {}
    
    print(">> Capturing Hybrid Context (Image + Text)...")
    try:
        # 1. Image
        binary = await page.screenshot(full_page=False, timeout=5000)
        b64_ss = base64.b64encode(binary).decode("utf-8")
        
        # 2. Text (Reduced to 12k chars to save tokens/quota)
        text_content = await page.evaluate("document.body.innerText")
        text_preview = text_content[:12000] 
        
        return {
            "image": b64_ss,
            "text": text_preview
        }
    except Exception as e:
        print(f"Capture failed: {e}")
        return {}

@tool
async def scroll_down() -> str:
    """Scrolls the web page down by 1000 pixels."""
    global page
    if not page: return ""
    try:
        await page.evaluate("window.scrollBy(0, 1000);")
        await asyncio.sleep(0.5) 
        print(">> Scrolled")
        return "Scrolled"
    except: return ""

# --- 4. Logic Nodes ---

llm = ChatGoogleGenerativeAI(
    model='gemini-flash-latest', 
    temperature=0,
    stop=["\n\n\n\n\n"] 
)

async def init_node(state: AgentState) -> AgentState:
    target_url = state.get("url") or "https://en.wikipedia.org/wiki/Large_language_model"
    await initialize_browser()
    await navigate_url.ainvoke(target_url)
    return {**state, 'url': target_url, 'summaries': []}

async def analyze_node(state: AgentState) -> AgentState:
    """Smart Analysis using Hybrid Vision + Text + Aggressive Logic."""
    
    context_data = await capture_page_context.ainvoke({})
    if not context_data or "image" not in context_data:
        return {**state, "current_context": None}

    task = state.get("task")
    current_scrolls = len(state.get("summaries", []))
    
    prompt_text = f"""
    You are a thorough researcher.
    USER TASK: "{task}"
    
    INPUTS:
    1. IMAGE: Current viewport.
    2. TEXT: Visible text (~12k chars).
    
    CRITICAL INSTRUCTIONS:
    - You MUST set 'should_scroll' to TRUE unless you see the 'References', 'External Links', or Copyright Footer.
    - If you only see a Table of Contents or Introduction, you MUST scroll.
    - If you are unsure, scroll.
    - Only stop if you have found the COMPLETE answer and verified it in the text.
    
    Current Scroll Count: {current_scrolls}
    """
    
    msg = HumanMessage(content=[
        {"type": "text", "text": prompt_text},
        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{context_data['image']}"}}
    ])

    structured_llm = llm.with_structured_output(PageAnalysis)
    result = await call_llm_with_retry(structured_llm.ainvoke, [msg])

    if result:
        print(f"   Summary: {result.summary[:60]}...")
        print(f"   AI Decision: {'SCROLLING' if result.should_scroll else 'STOPPING'}")
        
        new_summaries = state.get("summaries", []) + [str(result.summary)]
        status = "SCROLL_REQUIRED" if result.should_scroll else "DONE"
        
        return {
            **state,
            "summaries": new_summaries,
            "current_context": status
        }
    else:
        print(">> Analysis gave up. Moving to report generation.")
        return {**state, "current_context": "DONE"}

async def scroll_node(state: AgentState) -> AgentState:
    await scroll_down.ainvoke({})
    return state

async def aggregate_node(state: AgentState) -> AgentState:
    print(">> Generating Final Clean Report")
    summaries = state.get("summaries", [])
    task = state.get("task")
    
    clean_summaries = [str(s) for s in summaries if s]
    combined_text = "\n\n".join(clean_summaries)
    
    if not combined_text: combined_text = "No content gathered."

    # --- FAIL-SAFE: Save Raw Notes ---
    try:
        with open("raw_notes_backup.txt", "w", encoding="utf-8") as f:
            f.write(f"--- RAW NOTES for: {task} ---\n\n")
            f.write(combined_text)
        print(">> (Safety) Saved 'raw_notes_backup.txt'.")
    except: pass

    # --- POWER BI LOGGING ---
    log_to_csv(
        url=state.get("url"),
        task=task,
        summary_text=combined_text,
        status="Success"
    )

    # --- STRICT TEXT-ONLY PROMPT ---
    prompt = f"""
    You are a professional editor. Your goal is to produce a clean, organized text report.
    
    TASK: "{task}"
    
    INSTRUCTIONS:
    1. Read the notes below.
    2. Write a final report in standard Markdown format (Headings, Paragraphs, Bullet points).
    3. STRICTLY FORBIDDEN: Do not output JSON, dictionaries, objects, or code blocks.
    4. Do not include metadata like "Summary:" or braces {{ }}.
    5. Just give the clear, readable content.
    
    NOTES:
    {combined_text}
    """
    
    response = await call_llm_with_retry(llm.ainvoke, prompt)
    
    if response:
        with open("report.md", "w", encoding="utf-8") as f:
            f.write(str(response.content))
        print(">> SUCCESS: Saved clean 'report.md'")
    else:
        print(">> Failed to generate final report.")
    
    return state

# --- 5. Routing ---

def router(state: AgentState) -> str:
    status = state.get("current_context")
    summaries = state.get("summaries", [])
    scroll_count = len(summaries)
    
    if scroll_count >= 7:
        print(">> Limit reached (7). Finishing.")
        return "aggregate"
    
    if scroll_count < 1:
        print(">> Force Scroll (Rule: Minimum 1 Scroll)")
        return "scroll"
    
    if status == "SCROLL_REQUIRED":
        return "scroll"
    
    print(">> AI decided to stop.")
    return "aggregate"

# --- 6. Graph ---

workflow = StateGraph(AgentState)
workflow.add_node("init", init_node)
workflow.add_node("analyze", analyze_node)
workflow.add_node("scroll", scroll_node)
workflow.add_node("aggregate", aggregate_node)

workflow.set_entry_point("init")
workflow.add_edge("init", "analyze")
workflow.add_conditional_edges("analyze", router, {"scroll": "scroll", "aggregate": "aggregate"})
workflow.add_edge("scroll", "analyze")
workflow.add_edge("aggregate", END)

app = workflow.compile()

async def run_interactive():
    print("\n=== AUTO-PACED AI Browser Agent (Power BI Ready) ===")
    user_url = input("1. Enter URL: ").strip()
    if not user_url: user_url = "https://en.wikipedia.org/wiki/Large_language_model"
    
    user_task = input("2. Enter Task: ").strip()
    if not user_task: user_task = "Summarize the history of LLMs."

    print("\n--- Starting Agent (With Pacing) ---")
    try:
        await app.ainvoke({
            "messages": [], 
            "url": user_url, 
            "current_context": None, 
            "summaries": [],
            "task": user_task
        })
    except asyncio.CancelledError:
        print("\n\n>> Agent stopped by user.")
    except Exception as e:
        print(f"Fatal Error: {e}")
    finally:
        await close_browser()

if __name__ == "__main__":
    try:
        asyncio.run(run_interactive())
    except KeyboardInterrupt:
        print("\n\n>> Script interrupted. Exiting...")
