# 🤖  Browsify — Intelligent Web Research AI Agent

<p align="center">
  <img src="https://user-images.githubusercontent.com/your_username/project_screenshot.png" alt="Project screenshot" width="700">
</p>

[![License](https://img.shields.io/github/license/nick2726/browsify)](https://github.com/nick2726/browsify/blob/main/LICENSE)
[![Made with Python](https://img.shields.io/badge/Python-%233776AB.svg?style=flat&logo=python&logoColor=white)](#tech-stack)
[![Stars](https://img.shields.io/github/stars/nick2726/browsify?style=social)](https://github.com/nick2726/browsify/stargazers)

---

## 🧠 What is Browsify?

**Browsify** is an autonomous web research agent that uses AI + browser automation to intelligently explore websites, extract structured data, and generate human-readable reports.

Unlike basic scrapers, Browsify:

✔ reads pages like a human  
✔ scrolls dynamically  
✔ handles rate-limits & page logic  
✔ produces structured markdown reports  

---

## 🧩 Features

✨ **Hybrid Vision & DOM Parsing** — combines screenshots with raw HTML for better context  
📄 **Autonomous Decision Logic** — intelligently decides what to scroll or extract  
📊 **Structured Reports** — outputs context-rich markdown notes  
⚙️ **Easy Python Setup** — minimal dependencies  

---

## 🛠️ Tech Stack

| Technology | Purpose |
|------------|---------|
| Python | Core language |
| Playwright | Browser automation |
| LangGraph | AI workflow |
| Gemini 1.5 | Language model |

---

## 🔧 Installation

```bash
git clone https://github.com/nick2726/browsify.git
cd browsify
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt


Browser Autofy: Intelligent AI Web Agent

**Browser Autofy** is an autonomous web research agent built with **LangGraph**, **Playwright**, and **Google Gemini 1.5 Flash**. 

Unlike simple scrapers, this agent uses **Hybrid Intelligence** (Vision + Raw Text) to "read" websites like a human. It intelligently navigates, decides when to scroll for more information, handles rate limits automatically, and compiles its findings into a structured Markdown report.

## 🚀 Key Features

* **👁️ Hybrid Vision + Text Analysis:** The agent captures both screenshots (for layout context) and raw DOM text (for data precision) simultaneously, drastically reducing hallucinations.
* **🧠 Autonomous Decision Making:** It uses a logic router to decide: *"Do I have the answer? Or should I scroll deeper?"* It features aggressive scrolling logic to bypass headers and intros.
* **🛡️ Bulletproof Stability:** Built-in **Auto-Pacing** and **Smart Retry** wrappers ensure the agent runs smoothly on the Google Gemini Free Tier without crashing from errors.
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
