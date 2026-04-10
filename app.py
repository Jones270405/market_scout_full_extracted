# app.py — Market Scout · Chat UI (Gradio Chatbot, dark purple)
import os, sys, re
from pathlib import Path

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from dotenv import load_dotenv
load_dotenv()

import gradio as gr
from market_scout_agent.agent import run_pipeline
from guardrails.callbacks import (
    HARMFUL_PATTERNS, INJECTION_PATTERNS, OUT_OF_SCOPE,
    MIN_QUERY_LEN, MAX_QUERY_LEN,
)

OUTPUT_DIR = os.environ.get("MARKET_SCOUT_OUTPUT_DIR", os.path.join(_HERE, "outputs"))
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ─── Helpers ──────────────────────────────────────────────────────────────────

_ACTION_PREFIXES = re.compile(
    r"^(track|monitor|research|analyse|analyze|check|find|get|show|give me|"
    r"look up|search for|tell me about|what about|latest features? (?:of|for)?|"
    r"(?:latest |recent )?(?:updates?|news|features?|releases?) (?:for|of|on|about)?)\s+",
    re.IGNORECASE,
)
_COMPARE_PATTERN = re.compile(r"^(?:compare|vs\.?|versus)\s+", re.IGNORECASE)
_AND_PATTERN     = re.compile(r"\s+(?:and|vs\.?|versus)\s+", re.IGNORECASE)

def _extract_companies(text):
    text = text.strip()
    for _ in range(3):
        new = _ACTION_PREFIXES.sub("", text).strip()
        new = _COMPARE_PATTERN.sub("", new).strip()
        if new == text: break
        text = new
    text = _AND_PATTERN.sub(", ", text)
    text = re.sub(
        r"\s+(?:latest|recent|new|updates?|features?|releases?|news|info|information)$",
        "", text, flags=re.IGNORECASE).strip()
    return text

def _check_input(text):
    if len(text) < MIN_QUERY_LEN: return f"⚠️ Query too short (min {MIN_QUERY_LEN} chars)."
    if len(text) > MAX_QUERY_LEN: return f"⚠️ Query too long (max {MAX_QUERY_LEN} chars)."
    lower = text.lower()
    for p in HARMFUL_PATTERNS:
        if re.search(p, lower): return "🚫 Harmful intent detected. I only help with competitor intelligence."
    for p in INJECTION_PATTERNS:
        if re.search(p, lower): return "🚫 Prompt injection detected."
    for p in OUT_OF_SCOPE:
        if re.search(p, lower): return "ℹ️ I only track competitor updates. Try: `Track Stripe`"
    return None

GREETINGS = {"hi","hello","hey","greetings","good morning","good afternoon","good evening","howdy","sup","yo"}

WELCOME_MSG = """👋 **Welcome to Market Scout — Competitive Intelligence Assistant!**

I help you track and analyse competitor product updates in real time.

**Here's what you can ask me:**

| Example Query | What happens |
|:---|:---|
| `Track Stripe` | Full intelligence run for Stripe |
| `What's new at Tesla?` | Latest feature updates for Tesla |
| `Compare Stripe and PayPal` | Side-by-side analysis of both |
| `Nike latest features` | Recent product moves by Nike |
| `OpenAI, Anthropic` | Track multiple companies at once |

After each run I generate a **PDF report**, **Excel workbook**, **text briefing**, and an **HTML dashboard** — all available to download below the chat.

---
*Type a company name below or click an example to get started.*"""

# ─── Chat handler ─────────────────────────────────────────────────────────────

def respond(message, history):
    """Yields (history, file_list) tuples for streaming."""
    text = message.strip()
    history = history or []

    # Greeting
    if text.lower() in GREETINGS:
        history.append((text, "👋 Hello! Type a company name to get started, e.g. `Track Stripe`."))
        yield history, []
        return

    # Guardrail
    block = _check_input(text)
    if block:
        history.append((text, block))
        yield history, []
        return

    # Extract company
    query = _extract_companies(text)
    if not query:
        history.append((text, "Please enter a company name. Example: `Stripe`"))
        yield history, []
        return

    # Thinking message
    history.append((text, f"🔎 Analysing **{query}** — please wait 20–40 seconds…"))
    yield history, []

    # Run pipeline
    try:
        result = run_pipeline(query)
    except Exception as exc:
        history[-1] = (text,
            f"❌ **Pipeline error:** `{str(exc)}`\n\n"
            "Please ensure **TAVILY_API_KEY** and **GROQ_API_KEY** are set in Render → Environment.")
        yield history, []
        return

    summary          = result.get("summary", {})
    top_features     = result.get("top_features", [])
    files            = result.get("files", {})
    comparison_table = result.get("comparison_table", "")

    status_icons = {"WEEK":"🟢","MONTH":"🟡","YEAR":"🔵","UNVERIFIED":"⚪","STALE":"🔴"}

    if top_features:
        features_md = ""
        for i, f in enumerate(top_features, 1):
            icon = status_icons.get(f.get("status",""), "⚪")
            url_md = f" · [🔗 Source]({f['url']})" if f.get("url") else ""
            features_md += (
                f"**{i}. {f['feature']}**  \n"
                f"&nbsp;&nbsp;`{f.get('category','—')}` &nbsp;·&nbsp; "
                f"{f.get('date','unknown')} &nbsp;·&nbsp; "
                f"{icon} `{f.get('status','—')}`{url_md}\n\n"
            )
    else:
        features_md = "> ⚠️ No features found. Ensure **TAVILY_API_KEY** is set in Render → Environment.\n"

    comparison_md = f"\n### ⚖️ Comparison\n\n{comparison_table}\n" if comparison_table else ""

    response = f"""## 📊 {result['company']} — Intelligence Report
*{result['run_date']} &nbsp;·&nbsp; {result['version']}*

---

### 📈 Summary

| Timeframe | Count | Status |
|:---|---:|:---|
| **Total Features** | **{summary.get('total',0)}** | — |
| Last 7 Days | {summary.get('week',0)} | 🟢 WEEK |
| Last 30 Days | {summary.get('month',0)} | 🟡 MONTH |
| Last 365 Days | {summary.get('year',0)} | 🔵 YEAR |
| Unverified | {summary.get('unver',0)} | ⚪ |

---

### 🔑 Top Features

{features_md}{comparison_md}---

📁 **Reports saved** — download below 👇  
*Powered by Google ADK · Groq LLaMA 3.3 · Tavily Search*"""

    # Collect downloadable files
    file_list = []
    for key in ("pdf", "excel", "briefing", "dashboard"):
        p = files.get(key, "")
        if p and Path(p).exists():
            file_list.append(p)

    history[-1] = (text, response)
    yield history, file_list


def use_example(example_text):
    return example_text


# ─── CSS ──────────────────────────────────────────────────────────────────────

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

:root {
  --bg-base:    #0d0d1a;
  --bg-surface: #111127;
  --bg-card:    #16162e;
  --bg-input:   #1c1c38;
  --bg-bubble-user: #1e1040;
  --bg-bubble-bot:  #141428;
  --border:     #252545;
  --border-glow:#7c3aed;
  --purple-1:   #7c3aed;
  --purple-2:   #9d5cf6;
  --purple-3:   #c084fc;
  --purple-4:   #e9d5ff;
  --text-1:     #f1f0ff;
  --text-2:     #a89ec9;
  --text-3:     #5a5480;
  --radius:     14px;
  --shadow:     0 4px 24px rgba(124,58,237,0.12);
}

*, *::before, *::after { box-sizing: border-box; }

body, .gradio-container, #root {
  background: var(--bg-base) !important;
  font-family: 'Inter', sans-serif !important;
  color: var(--text-1) !important;
}

.gradio-container {
  max-width: 860px !important;
  margin: 0 auto !important;
  padding: 0 0 40px !important;
}

footer, .footer, .svelte-1gfkn6j { display: none !important; }

/* ── Top bar ── */
#topbar {
  background: linear-gradient(135deg, #13122a 0%, #1a1035 100%);
  border-bottom: 1px solid var(--border);
  padding: 16px 28px;
  display: flex;
  align-items: center;
  gap: 12px;
  position: sticky;
  top: 0;
  z-index: 100;
}
#topbar .logo {
  width: 34px; height: 34px;
  background: linear-gradient(135deg, #7c3aed, #4f46e5);
  border-radius: 9px;
  display: flex; align-items: center; justify-content: center;
  font-size: 16px;
  box-shadow: 0 2px 12px rgba(124,58,237,0.5);
  flex-shrink: 0;
}
#topbar h2 {
  font-size: 1.05rem; font-weight: 700;
  background: linear-gradient(90deg, #c084fc, #818cf8);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  background-clip: text;
  margin: 0;
}
#topbar p { font-size: 0.76rem; color: var(--text-3); margin: 0; }
#topbar .badges { margin-left: auto; display: flex; gap: 6px; }
#topbar .badge {
  background: rgba(124,58,237,0.15);
  border: 1px solid rgba(124,58,237,0.3);
  color: var(--purple-3);
  padding: 3px 10px; border-radius: 20px;
  font-size: 0.72rem; font-weight: 500;
}

/* ── Chatbot ── */
#chatbot {
  background: var(--bg-surface) !important;
  border: none !important;
  border-radius: 0 !important;
  min-height: 480px;
  padding: 0 !important;
}

/* message bubbles */
.message-wrap { padding: 8px 24px !important; }

.message.user .bubble-wrap .md {
  background: var(--bg-bubble-user) !important;
  border: 1px solid rgba(124,58,237,0.25) !important;
  border-radius: 18px 18px 4px 18px !important;
  color: var(--text-1) !important;
  padding: 12px 16px !important;
  font-size: 0.92rem !important;
  max-width: 75% !important;
  margin-left: auto !important;
}

.message.bot .bubble-wrap .md {
  background: var(--bg-bubble-bot) !important;
  border: 1px solid var(--border) !important;
  border-radius: 4px 18px 18px 18px !important;
  color: var(--text-2) !important;
  padding: 16px 20px !important;
  font-size: 0.9rem !important;
  line-height: 1.7 !important;
  max-width: 90% !important;
}

/* bot avatar */
.message.bot .avatar-container {
  background: linear-gradient(135deg,#7c3aed,#4f46e5) !important;
  border-radius: 50% !important;
  width: 30px !important; height: 30px !important;
}

/* markdown inside bubbles */
.message.bot .bubble-wrap h2 {
  font-size: 1.1rem !important; font-weight: 700 !important;
  color: var(--purple-3) !important; margin-bottom: 4px !important;
  border: none !important; padding: 0 !important;
}
.message.bot .bubble-wrap h3 {
  font-size: 0.92rem !important; font-weight: 600 !important;
  color: var(--purple-4) !important;
  margin: 16px 0 8px !important;
  padding-left: 8px !important;
  border-left: 2px solid var(--purple-1) !important;
}
.message.bot .bubble-wrap strong { color: var(--text-1) !important; }
.message.bot .bubble-wrap em { color: var(--text-3) !important; font-size: 0.82rem !important; }
.message.bot .bubble-wrap hr { border-color: var(--border) !important; margin: 12px 0 !important; }
.message.bot .bubble-wrap a { color: var(--purple-3) !important; }
.message.bot .bubble-wrap a:hover { color: var(--purple-4) !important; }
.message.bot .bubble-wrap code {
  background: rgba(124,58,237,0.15) !important;
  color: var(--purple-3) !important;
  border: 1px solid rgba(124,58,237,0.2) !important;
  border-radius: 5px !important;
  padding: 1px 6px !important;
  font-family: 'JetBrains Mono', monospace !important;
  font-size: 0.8rem !important;
}
.message.bot .bubble-wrap blockquote {
  border-left: 3px solid #fbbf24 !important;
  background: rgba(251,191,36,0.07) !important;
  padding: 8px 14px !important; border-radius: 0 8px 8px 0 !important;
  margin: 8px 0 !important;
}
.message.bot .bubble-wrap blockquote p { color: #fbbf24 !important; }

/* tables inside bubbles */
.message.bot .bubble-wrap table {
  width: 100% !important; border-collapse: collapse !important;
  margin: 10px 0 !important; font-size: 0.85rem !important;
}
.message.bot .bubble-wrap thead tr { background: rgba(124,58,237,0.15) !important; }
.message.bot .bubble-wrap th {
  color: var(--purple-3) !important; font-weight: 600 !important;
  padding: 8px 12px !important; text-align: left !important;
  border-bottom: 1px solid var(--border-glow) !important;
  font-size: 0.78rem !important; text-transform: uppercase !important; letter-spacing: 0.4px !important;
}
.message.bot .bubble-wrap td {
  padding: 8px 12px !important; border-bottom: 1px solid var(--border) !important;
  color: var(--text-2) !important;
}
.message.bot .bubble-wrap tbody tr:hover { background: rgba(124,58,237,0.05) !important; }

/* ── Input row ── */
#input-row {
  background: var(--bg-card);
  border-top: 1px solid var(--border);
  padding: 16px 20px;
  display: flex; gap: 10px; align-items: flex-end;
}

#chat-input textarea {
  background: var(--bg-input) !important;
  border: 1px solid var(--border) !important;
  border-radius: 12px !important;
  color: var(--text-1) !important;
  font-family: 'Inter', sans-serif !important;
  font-size: 0.95rem !important;
  padding: 12px 16px !important;
  resize: none !important;
  transition: border-color 0.2s, box-shadow 0.2s !important;
  caret-color: var(--purple-2);
}
#chat-input textarea:focus {
  border-color: var(--border-glow) !important;
  box-shadow: 0 0 0 3px rgba(124,58,237,0.12) !important;
  outline: none !important;
}
#chat-input textarea::placeholder { color: var(--text-3) !important; }

/* send button */
#send-btn {
  background: linear-gradient(135deg, #7c3aed, #5b21b6) !important;
  border: none !important; border-radius: 12px !important;
  color: #fff !important; font-weight: 600 !important;
  font-size: 0.9rem !important; padding: 12px 22px !important;
  cursor: pointer !important;
  box-shadow: 0 3px 12px rgba(124,58,237,0.4) !important;
  transition: all 0.2s !important;
  white-space: nowrap;
}
#send-btn:hover {
  background: linear-gradient(135deg, #9d5cf6, #7c3aed) !important;
  box-shadow: 0 5px 18px rgba(124,58,237,0.55) !important;
  transform: translateY(-1px) !important;
}

/* ── Examples strip ── */
#examples-row {
  background: var(--bg-card);
  border-top: 1px solid var(--border);
  padding: 12px 20px 14px;
  display: flex; flex-wrap: wrap; gap: 8px; align-items: center;
}
#examples-label {
  font-size: 0.72rem; text-transform: uppercase;
  letter-spacing: 1px; color: var(--text-3); font-weight: 600;
  margin-right: 4px; white-space: nowrap;
}
.example-chip button {
  background: var(--bg-input) !important;
  border: 1px solid var(--border) !important;
  border-radius: 20px !important;
  color: var(--purple-3) !important;
  font-family: 'JetBrains Mono', monospace !important;
  font-size: 0.78rem !important; font-weight: 500 !important;
  padding: 5px 14px !important;
  cursor: pointer !important;
  transition: all 0.15s !important;
}
.example-chip button:hover {
  background: rgba(124,58,237,0.15) !important;
  border-color: var(--border-glow) !important;
  color: var(--purple-4) !important;
  transform: translateY(-1px) !important;
}

/* ── Download section ── */
#dl-header {
  padding: 18px 24px 6px;
  font-size: 0.72rem; text-transform: uppercase;
  letter-spacing: 1px; color: var(--text-3); font-weight: 600;
  background: var(--bg-card);
  border-top: 1px solid var(--border);
}
#downloads {
  background: var(--bg-card);
  padding: 6px 20px 20px;
}
#downloads .gr-file-preview, .file-preview {
  background: var(--bg-input) !important;
  border: 1px solid var(--border) !important;
  border-radius: 10px !important;
  color: var(--text-2) !important;
  transition: border-color 0.2s;
}
#downloads .gr-file-preview:hover { border-color: var(--border-glow) !important; }

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 5px; }
::-webkit-scrollbar-track { background: var(--bg-base); }
::-webkit-scrollbar-thumb { background: var(--border-glow); border-radius: 3px; }

/* ── Gradio overrides ── */
.gr-group, .gr-box { background: transparent !important; border: none !important; }
.gap-4 { gap: 0 !important; }
.gr-padded { padding: 0 !important; }
"""

# ─── Build UI ─────────────────────────────────────────────────────────────────

EXAMPLES = [
    "Track Stripe",
    "What's new at Tesla?",
    "Compare Stripe and PayPal",
    "Nike latest features",
    "OpenAI, Anthropic",
]

with gr.Blocks(
    title="Market Scout — Competitive Intelligence",
    theme=gr.themes.Base(),
    css=CSS,
) as demo:

    # ── Top bar ──
    gr.HTML("""
    <div id="topbar">
      <div class="logo">🔍</div>
      <div>
        <h2>Market Scout</h2>
        <p>Competitive Intelligence Assistant</p>
      </div>
      <div class="badges">
        <span class="badge">Google ADK</span>
        <span class="badge">Groq LLaMA 3.3</span>
        <span class="badge">Tavily Search</span>
      </div>
    </div>
    """)

    # ── Chat window ──
    chatbot = gr.Chatbot(
        value=[[None, WELCOME_MSG]],
        elem_id="chatbot",
        bubble_full_width=False,
        show_label=False,
        height=500,
        avatar_images=(None, "https://api.dicebear.com/7.x/bottts-neutral/svg?seed=scout&backgroundColor=7c3aed"),
    )

    # ── Input row ──
    with gr.Row(elem_id="input-row"):
        chat_input = gr.Textbox(
            placeholder="Type a company name… e.g. Stripe or Compare PayPal and Stripe",
            show_label=False,
            lines=1,
            scale=5,
            elem_id="chat-input",
            autofocus=True,
        )
        send_btn = gr.Button("Send ➤", elem_id="send-btn", scale=1, min_width=90)

    # ── Example chips ──
    gr.HTML('<div id="examples-row"><span id="examples-label">Try:</span></div>')
    with gr.Row():
        chip_btns = [
            gr.Button(ex, elem_classes=["example-chip"], size="sm", min_width=0)
            for ex in EXAMPLES
        ]

    # ── Download section ──
    gr.HTML('<div id="dl-header">📎 Download Reports</div>')
    with gr.Row(elem_id="downloads"):
        pdf_out       = gr.File(label="📄 PDF Report",     interactive=False)
        excel_out     = gr.File(label="📊 Excel Workbook", interactive=False)
        briefing_out  = gr.File(label="📝 Text Briefing",  interactive=False)
        dashboard_out = gr.File(label="🌐 HTML Dashboard", interactive=False)

    # ── Wire events ──
    def _unpack(history, files):
        """Split flat file list back into 4 outputs."""
        def _get(i): return files[i] if files and i < len(files) else None
        return history, _get(0), _get(1), _get(2), _get(3)

    outputs = [chatbot, pdf_out, excel_out, briefing_out, dashboard_out]

    def submit_and_clear(msg, history):
        results = None
        for history, files in respond(msg, history):
            results = (history, files)
            yield history, "", *([None]*4)
        if results:
            h, files = results
            def _get(i): return files[i] if files and i < len(files) else None
            yield h, "", _get(0), _get(1), _get(2), _get(3)

    send_btn.click(
        fn=submit_and_clear,
        inputs=[chat_input, chatbot],
        outputs=[chatbot, chat_input, pdf_out, excel_out, briefing_out, dashboard_out],
    )
    chat_input.submit(
        fn=submit_and_clear,
        inputs=[chat_input, chatbot],
        outputs=[chatbot, chat_input, pdf_out, excel_out, briefing_out, dashboard_out],
    )

    for btn, ex in zip(chip_btns, EXAMPLES):
        btn.click(fn=lambda e=ex: e, outputs=chat_input)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7860))
    demo.launch(server_name="0.0.0.0", server_port=port, share=False, show_error=True)