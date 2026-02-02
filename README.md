# 🤖 Browser Autofy: Intelligent AI Web Agent

**Browser Autofy** is an autonomous web research agent built with **LangGraph**, **Playwright**, and **Google Gemini 1.5 Flash**. 

Unlike simple scrapers, this agent uses **Hybrid Intelligence** (Vision + Raw Text) to "read" websites like a human. It intelligently navigates, decides when to scroll for more information, handles rate limits automatically, and compiles its findings into a structured Markdown report.

## 🚀 Key Features

* **👁️ Hybrid Vision + Text Analysis:** The agent captures both screenshots (for layout context) and raw DOM text (for data precision) simultaneously, drastically reducing hallucinations.
* **🧠 Autonomous Decision Making:** It uses a logic router to decide: *"Do I have the answer? Or should I scroll deeper?"* It features aggressive scrolling logic to bypass headers and intros.
* **🛡️ Bulletproof Stability:** Built-in **Auto-Pacing** and **Smart Retry** wrappers ensure the agent runs smoothly on the Google Gemini Free Tier without crashing from `429 Rate Limit` errors.
* **📝 Automated Reporting:** Aggregates findings from multiple scroll depths into a coherent `report.md` file.

## 🛠️ Tech Stack

* **Core Logic:** Python, LangGraph (State Management)
* **AI Model:** Google Gemini 1.5 Flash (via LangChain)
* **Browser Automation:** Playwright (Async)
* **Data Validation:** Pydantic

## ⚙️ Installation

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/yourusername/browser-autofy.git](https://github.com/yourusername/browser-autofy.git)
    cd browser-autofy
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    python -m venv .venv
    # Windows
    .venv\Scripts\activate
    # Mac/Linux
    source .venv/bin/activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Install Playwright browsers:**
    ```bash
    python -m playwright install
    ```

5.  **Set up your API Key:**
    Create a `.env` file in the root directory and add your Google Gemini key:
    ```env
    GOOGLE_API_KEY=your_actual_api_key_here
    ```

## 🏃‍♂️ Usage

Run the agent:
```bash
python auto.py
