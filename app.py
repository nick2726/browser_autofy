import streamlit as st
import asyncio
import base64
import os
import sys
import csv
from datetime import datetime
from dotenv import load_dotenv
from typing import TypedDict, Annotated, List, Optional, Sequence, Union

# LangGraph & AI Imports
from langchain_core.messages import BaseMessage, HumanMessage
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from playwright.async_api import async_playwright

# --- CRITICAL FIX FOR WINDOWS ---
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# --- 1. MODERN UI SETUP ---
st.set_page_config(page_title="Browser Autofy Pro", page_icon="⚡", layout="wide")
load_dotenv()

st.markdown("""
    <style>
    .stApp { background-color: #0f1116; color: #e0e0e0; }
    .metric-card { background-color: #1e212b; border: 1px solid #2e3342; border-radius: 10px; padding: 15px; margin-bottom: 10px; }
    .log-container { font-family: 'JetBrains Mono', monospace; background-color: #0a0c10; color: #00e676; padding: 15px; border-radius: 8px; height: 400px; overflow-y: auto; border: 1px solid #333; font-size: 13px; line-height: 1.6; }
    </style>
""", unsafe_allow_html=True)

# --- SESSION STATE ---
if "logs" not in st.session_state: st.session_state.logs = []
if "latest_image" not in st.session_state: st.session_state.latest_image = None
if "agent_status" not in st.session_state: st.session_state.agent_status = "IDLE"

# --- UI COMPONENTS ---
st.title("⚡ Browser Autofy: Robust Vision")

metric_col1, metric_col2 = st.columns([1, 3])
with metric_col1:
    st.markdown(f"""
    <div class="metric-card">
        <small style="color:#888">Current Status</small><br>
        <span style="font-size:18px; font-weight:bold; color:#2962ff">{st.session_state.agent_status}</span>
    </div>
    """, unsafe_allow_html=True)

col_vision, col_logs = st.columns([1, 1])

with col_vision:
    st.subheader("👁️ Robot Vision (Cleaned)")
    vision_container = st.empty()
    if st.session_state.latest_image:
        vision_container.image(st.session_state.latest_image, caption="What the Agent Sees", use_container_width=True)
    else:
        vision_container.info("Waiting for visual feed...")

with col_logs:
    st.subheader("🧠 Neural Logs")
    log_container = st.empty()

# --- HELPER FUNCTIONS ---
def update_ui(msg, image_b64=None, status=None, toast=None):
    if msg:
        timestamp = datetime.now().strftime("%H:%M:%S")
        st.session_state.logs.append(f"[{timestamp}] {msg}")
        logs_html = "<br>".join([f"<span style='opacity:0.8'>{l}</span>" for l in st.session_state.logs])
        log_container.markdown(f'<div class="log-container">{logs_html}</div>', unsafe_allow_html=True)
    
    if image_b64:
        img_data = base64.b64decode(image_b64)
        st.session_state.latest_image = img_data
        vision_container.image(img_data, caption=f"Snapshot at {datetime.now().strftime('%H:%M:%S')}", use_container_width=True)
    
    if status: st.session_state.agent_status = status
    if toast: st.toast(toast, icon="🤖")

# --- BACKEND LOGIC ---
browser_context = {"browser": None, "page": None}

class PageAnalysis(BaseModel):
    summary: str = Field(description="Summary of visible content.")
    should_scroll: bool = Field(description="True if more content is needed.")

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    url: Union[str, None]
    current_context: Optional[dict]
    summaries: List[str]
    task: str

async def call_llm_safe(func, *args, **kwargs):
    for attempt in range(3):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            if "429" in str(e):
                update_ui("⚠️ Rate Limit Hit. Cooling down...", toast="❄️ Cooling...")
                await asyncio.sleep(10 * (attempt + 1))
            else:
                return None
    return None

# --- ROBUST TOOLS ---

async def init_browser_tool(headless_mode):
    update_ui(">> Booting High-Res Browser...", status="BOOTING")
    try:
        pw = await async_playwright().start()
        browser = await pw.chromium.launch(
            headless=headless_mode,
            # Stealth Args
            args=["--disable-blink-features=AutomationControlled", "--start-maximized", "--no-sandbox"]
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            # FORCE DESKTOP RESOLUTION
            viewport={"width": 1920, "height": 1080},
            device_scale_factor=1
        )
        page = await context.new_page()
        browser_context["browser"] = browser
        browser_context["page"] = page
        return pw
    except Exception as e:
        update_ui(f"❌ Init Failed: {e}", status="ERROR")
        raise e

async def navigate_tool(url):
    page = browser_context["page"]
    if page:
        update_ui(f">> Navigating to: {url}", status="NAVIGATING", toast="🚀 Navigating...")
        try:
            await page.goto(url, wait_until='domcontentloaded', timeout=60000)
            await asyncio.sleep(3) # Let JS settle
        except Exception as e:
            update_ui(f"⚠️ Nav Warning: {e}")

async def capture_tool():
    """
    Enhanced Capture: 
    1. Removes Cookie Banners/Popups
    2. Takes clean screenshot
    """
    page = browser_context["page"]
    if not page: return {}
    update_ui(">> Cleaning & Capturing...", status="SEEING")
    
    try:
        if page.is_closed(): return {}
        
        # --- DECLUTTER PROTOCOL ---
        # This JS removes sticky headers, cookie banners, and overlays that block vision
        await page.evaluate("""
            () => {
                // Remove generic cookie banners
                const selectors = [
                    '#onetrust-banner-sdk', '.cookie-banner', '#cookie-banner', 
                    '.fc-consent-root', '#accept-cookies', '.popup-overlay'
                ];
                selectors.forEach(s => {
                    const el = document.querySelector(s);
                    if (el) el.remove();
                });
                
                // Force fixed elements to static so they don't block screenshots
                const all = document.querySelectorAll('*');
                for (const el of all) {
                    const style = window.getComputedStyle(el);
                    if (style.position === 'fixed' || style.position === 'sticky') {
                        el.style.position = 'absolute'; 
                        el.style.zIndex = '-1';
                    }
                }
            }
        """)
        await asyncio.sleep(0.5) # Wait for cleanup
        
        # Capture
        binary = await page.screenshot(full_page=False, timeout=5000)
        b64_ss = base64.b64encode(binary).decode("utf-8")
        update_ui("📸 View Captured", image_b64=b64_ss)
        
        text = await page.evaluate("document.body.innerText")
        return {"image": b64_ss, "text": text[:10000]} # Limit text for rate limits
    except Exception as e:
        update_ui(f"⚠️ Capture Failed: {e}")
        return {}

async def scroll_tool():
    """
    Smart Scroll: Scrolls and checks if movement actually happened.
    """
    page = browser_context["page"]
    if page:
        try:
            # Scroll down by 80% of the viewport height (approx 800px on 1080p)
            await page.evaluate("window.scrollBy(0, window.innerHeight * 0.8);")
            update_ui(">> Scrolled Down (Smart)", status="SCROLLING")
            
            # Wait for lazy loading content
            await asyncio.sleep(2) 
        except: pass

async def robust_google_search(task):
    page = browser_context["page"]
    if not page: return None
    
    update_ui(f"🧠 Planner: Searching Google for '{task}'...", status="PLANNING")
    try:
        await page.goto(f"https://www.google.com/search?q={task.replace(' ', '+')}", wait_until='domcontentloaded')
        
        update_ui("👀 Checking results... (Solve CAPTCHA if needed!)", toast="⚠️ Check Browser!")
        
        try:
            await page.wait_for_selector("div#search", state="attached", timeout=60000)
            update_ui("✅ Results found! Analyzing...", toast="✅ Resuming...")
        except:
            update_ui("⚠️ Timeout. No results found.")
            return None

        best_url = await page.evaluate("""
            () => {
                const anchors = Array.from(document.querySelectorAll('div#search a'));
                for (const a of anchors) {
                    if (a.href && a.href.startsWith('http') && !a.href.includes('google.com')) {
                        return a.href;
                    }
                }
                return null;
            }
        """)

        if best_url:
            update_ui(f"🎯 Target Acquired: {best_url}")
            return best_url
            
    except Exception as e:
        update_ui(f"⚠️ Search Logic Failed: {e}")
    
    return None

# --- NODES ---
llm = ChatGoogleGenerativeAI(model='gemini-flash-latest', temperature=0)

async def planner_node(state: AgentState):
    current_url = state.get("url")
    if not current_url:
        new_url = await robust_google_search(state["task"])
        if new_url: return {**state, "url": new_url}
        else: 
            update_ui("🛑 Planner Failed. Aborting.")
            return {**state, "current_context": "ABORT"}
    return state

def planner_router(state):
    return END if state.get("current_context") == "ABORT" else "init"

async def init_node(state: AgentState):
    if state.get("url"): await navigate_tool(state["url"])
    return state

async def analyze_node(state: AgentState):
    delay = st.session_state.get("pacing_delay", 2)
    if delay > 0: await asyncio.sleep(delay)

    data = await capture_tool()
    if not data: return {**state, "current_context": "DONE"}
    
    update_ui("🤖 Analyzing Content...", status="THINKING")

    task = state["task"]
    scrolls = len(state.get("summaries", []))
    
    # AGGRESSIVE PROMPT FOR SCROLLING
    prompt = f"""
    Task: "{task}"
    
    1. EXTRACT facts from the image/text.
    2. IMPORTANT: If the answer is NOT fully visible, or if you see a 'Table of Contents' or 'Introduction', you MUST scroll.
    3. Set should_scroll=True to read more.
    4. Only set should_scroll=False if you have the COMPLETE detailed answer.
    
    Current Scrolls: {scrolls}
    """
    
    msg = HumanMessage(content=[{"type": "text", "text": prompt}, {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{data['image']}"}}])

    structured = llm.with_structured_output(PageAnalysis)
    res = await call_llm_safe(structured.ainvoke, [msg])

    if res:
        update_ui(f"💡 Insight: {res.summary[:50]}...")
        new_sums = state.get("summaries", []) + [res.summary]
        status = "SCROLL_REQUIRED" if res.should_scroll else "DONE"
        update_ui(f"Decided: {status}")
        return {**state, "summaries": new_sums, "current_context": status}
    
    return {**state, "current_context": "DONE"}

async def scroll_node(state: AgentState):
    await scroll_tool()
    return state

async def aggregate_node(state: AgentState):
    update_ui("📝 Writing Final Report...", status="WRITING", toast="📝 Generating...")
    summaries = "\n\n".join(state["summaries"])
    if not summaries: summaries = "No content."
    
    prompt = f"Create a final answer for '{state['task']}' using these notes:\n{summaries}"
    res = await call_llm_safe(llm.ainvoke, prompt)
    
    report_text = str(res.content) if res else f"AI Failed. Raw Notes:\n{summaries}"
    
    st.session_state.final_report = report_text
    update_ui("🎉 Report Complete!", status="DONE", toast="🎉 Done!")
    return state

def router(state: AgentState):
    if not state.get("url"): return "aggregate"
    if len(state["summaries"]) >= st.session_state.get("max_scrolls", 5): 
        update_ui("🛑 Max Depth Reached.")
        return "aggregate"
    if len(state["summaries"]) < 1: return "scroll"
    if state["current_context"] == "SCROLL_REQUIRED": return "scroll"
    return "aggregate"

# --- GRAPH ---
workflow = StateGraph(AgentState)
workflow.add_node("planner", planner_node)
workflow.add_node("init", init_node)
workflow.add_node("analyze", analyze_node)
workflow.add_node("scroll", scroll_node)
workflow.add_node("aggregate", aggregate_node)
workflow.set_entry_point("planner")
workflow.add_conditional_edges("planner", planner_router, {"init": "init", END: END})
workflow.add_edge("init", "analyze")
workflow.add_conditional_edges("analyze", router, {"scroll": "scroll", "aggregate": "aggregate"})
workflow.add_edge("scroll", "analyze")
workflow.add_edge("aggregate", END)
app_graph = workflow.compile()

# --- SIDEBAR & RUN ---
with st.sidebar:
    st.header("⚙️ Controls")
    headless = st.checkbox("Headless Mode", value=False)
    pacing = st.slider("Thinking Speed", 0, 5, 2)
    max_scrolls = st.slider("Depth (Scrolls)", 1, 10, 5)
    st.session_state.pacing_delay = pacing
    st.session_state.max_scrolls = max_scrolls
    
    st.divider()
    target_url = st.text_input("Target URL (Optional)", "")
    user_task = st.text_input("Mission Objective", "Who is the CEO of OpenAI?")
    run_btn = st.button("🚀 Start Mission", type="primary", use_container_width=True)

async def run_main():
    st.session_state.logs = []
    st.session_state.final_report = None
    update_ui("🚀 Initializing...", status="STARTING")
    
    pw = None
    try:
        pw = await init_browser_tool(headless)
        inputs = {"messages": [], "url": target_url, "task": user_task, "current_context": None, "summaries": []}
        async for output in app_graph.astream(inputs): pass 
    except Exception as e:
        update_ui(f"❌ Critical Error: {e}", status="CRASHED")
    finally:
        if browser_context["browser"]:
            try: await browser_context["browser"].close()
            except: pass
        if pw:
            try: await pw.stop()
            except: pass
        update_ui("🏁 Mission Ended.", status="IDLE")

if run_btn:
    if not os.getenv("GOOGLE_API_KEY"): st.error("Missing API Key")
    else: asyncio.run(run_main())

if st.session_state.get("final_report"):
    st.divider()
    st.subheader("📝 Mission Report")
    with st.container(border=True):
        st.markdown(st.session_state.final_report)
    st.download_button("💾 Download Report", st.session_state.final_report, file_name="mission_report.md")
