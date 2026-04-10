# app.py
"""
Market Scout — Gradio UI
Replaces Chainlit. Works reliably on Render free tier.
Run locally : python app.py
Deploy      : Render (see render.yaml)
"""

import os
import sys
import re
import asyncio
import threading
from pathlib import Path
from datetime import datetime

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

OUTPUT_DIR = os.environ.get(
    "MARKET_SCOUT_OUTPUT_DIR",
    os.path.join(_HERE, "outputs"),
)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ─── Company name extraction ──────────────────────────────────────────────────

_ACTION_PREFIXES = re.compile(
    r"^(track|monitor|research|analyse|analyze|check|find|get|show|give me|"
    r"look up|search for|tell me about|what about|latest features? (?:of|for)?|"
    r"(?:latest |recent )?(?:updates?|news|features?|releases?) (?:for|of|on|about)?)\s+",
    re.IGNORECASE,
)
_COMPARE_PATTERN = re.compile(r"^(?:compare|vs\.?|versus)\s+", re.IGNORECASE)
_AND_PATTERN     = re.compile(r"\s+(?:and|vs\.?|versus)\s+", re.IGNORECASE)

def _extract_companies(text: str) -> str:
    text = text.strip()
    for _ in range(3):
        new = _ACTION_PREFIXES.sub("", text).strip()
        new = _COMPARE_PATTERN.sub("", new).strip()
        if new == text:
            break
        text = new
    text = _AND_PATTERN.sub(", ", text)
    text = re.sub(
        r"\s+(?:latest|recent|new|updates?|features?|releases?|news|info|information)$",
        "", text, flags=re.IGNORECASE,
    ).strip()
    return text

# ─── Guardrail ────────────────────────────────────────────────────────────────

def _check_input(text: str) -> str | None:
    if len(text) < MIN_QUERY_LEN:
        return f"⚠️ Query too short (minimum {MIN_QUERY_LEN} characters)."
    if len(text) > MAX_QUERY_LEN:
        return f"⚠️ Query too long (maximum {MAX_QUERY_LEN} characters)."
    lower = text.lower()
    for p in HARMFUL_PATTERNS:
        if re.search(p, lower):
            return "🚫 Harmful intent detected. I can only help with competitor intelligence."
    for p in INJECTION_PATTERNS:
        if re.search(p, lower):
            return "🚫 Prompt injection attempt detected."
    for p in OUT_OF_SCOPE:
        if re.search(p, lower):
            return "ℹ️ I only track competitor updates. Try: 'Track Stripe'."
    return None

# ─── Main handler ─────────────────────────────────────────────────────────────

def handle_query(user_input: str):
    """
    Yields incremental status updates, then returns:
      (markdown_report, pdf_path, excel_path, briefing_path, dashboard_path)
    """
    text = user_input.strip()

    GREETING_TRIGGERS = {"hi","hello","hey","greetings","good morning",
                         "good afternoon","good evening","howdy","sup","yo"}
    if text.lower() in GREETING_TRIGGERS:
        yield (
            "👋 Hello! Type a company name to get started.\n\n"
            "Examples: `Stripe` · `Track Tesla` · `Compare PayPal and Stripe`",
            None, None, None, None
        )
        return

    block = _check_input(text)
    if block:
        yield (block, None, None, None, None)
        return

    query = _extract_companies(text)
    if not query:
        yield ("Please enter a company name. Example: `Stripe`", None, None, None, None)
        return

    yield (f"🔎 Searching for **{query}** — this may take 20–40 seconds…", None, None, None, None)

    try:
        result = run_pipeline(query)
    except Exception as exc:
        yield (
            f"❌ **Pipeline error:** `{str(exc)}`\n\n"
            "Check that **TAVILY_API_KEY** and **GROQ_API_KEY** are set in "
            "Render → Environment.",
            None, None, None, None
        )
        return

    summary          = result.get("summary", {})
    top_features     = result.get("top_features", [])
    files            = result.get("files", {})
    comparison_table = result.get("comparison_table", "")

    # ── Features section ──
    if top_features:
        features_md = ""
        for i, f in enumerate(top_features, 1):
            url_md = f"\n  - 🔗 [Source]({f['url']})" if f.get("url") else ""
            features_md += (
                f"**{i}. {f['feature']}**  \n"
                f"  `{f['category']}` · {f['date']} · **{f['status']}**"
                f"{url_md}\n\n"
            )
    else:
        features_md = (
            "> ⚠️ No features found. This usually means **TAVILY_API_KEY** "
            "is not set in Render → Environment → add it and redeploy.\n"
        )

    comparison_md = ""
    if comparison_table:
        comparison_md = f"\n### ⚖️ Company Comparison\n\n{comparison_table}\n"

    report = f"""## 📊 Market Scout Report
**Company:** {result['company']} &nbsp;|&nbsp; **Run Date:** {result['run_date']} &nbsp;|&nbsp; **Version:** {result['version']}

---

### 📈 Findings Summary

| Timeframe | Count | Status |
|:----------|------:|:-------|
| Total Features | {summary.get('total', 0)} | — |
| Last 7 Days | {summary.get('week', 0)} | 🟢 WEEK |
| Last 30 Days | {summary.get('month', 0)} | 🟡 MONTH |
| Last 365 Days | {summary.get('year', 0)} | 🔵 YEAR |
| Unverified | {summary.get('unver', 0)} | ⚪ Unknown |

---

### 🔑 Top Features

{features_md}{comparison_md}
---

*Powered by Google ADK · Groq LLaMA 3.3 · Tavily Search*
"""

    # Resolve file paths — return None if file doesn't exist (Gradio skips None)
    def _path(key):
        p = files.get(key, "")
        return p if p and Path(p).exists() else None

    yield (report, _path("pdf"), _path("excel"), _path("briefing"), _path("dashboard"))


# ─── Gradio UI ────────────────────────────────────────────────────────────────

EXAMPLES = [
    ["Stripe"],
    ["Track Tesla"],
    ["Compare PayPal and Stripe"],
    ["Nike latest features"],
    ["OpenAI"],
]

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

:root {
  --bg-base:        #09090f;
  --bg-surface:     #0f0d1f;
  --bg-card:        #12102a;
  --bg-input:       #12102a;
  --bg-bubble-user: #1a1040;
  --bg-bubble-bot:  #0f0d1f;
  --border:         #1e1b3a;
  --border-accent:  #2e2860;
  --border-glow:    #5b21b6;
  --purple-1:       #5b21b6;
  --purple-2:       #7c3aed;
  --purple-3:       #a78bfa;
  --purple-4:       #ddd6fe;
  --text-1:         #e2dcf8;
  --text-2:         #9d96c0;
  --text-3:         #4b4870;
  --radius:         12px;
}

*, *::before, *::after { box-sizing: border-box; }

body, .gradio-container, #root {
  background: var(--bg-base) !important;
  font-family: 'Inter', system-ui, sans-serif !important;
  color: var(--text-1) !important;
}

.gradio-container {
  max-width: 880px !important;
  margin: 0 auto !important;
  padding: 0 0 48px !important;
}

footer, .footer, .svelte-1gfkn6j { display: none !important; }

/* ── Topbar ── */
#topbar {
  background: var(--bg-surface);
  border-bottom: 1px solid var(--border);
  padding: 14px 24px;
  display: flex;
  align-items: center;
  gap: 14px;
  position: sticky;
  top: 0;
  z-index: 100;
}
#topbar .logo {
  width: 36px; height: 36px;
  background: var(--purple-1);
  border-radius: 10px;
  display: flex; align-items: center; justify-content: center;
  font-size: 15px;
  flex-shrink: 0;
}
#topbar h2 {
  font-size: 15px; font-weight: 700;
  color: var(--purple-4);
  letter-spacing: -0.3px;
  margin: 0;
}
#topbar p { font-size: 11px; color: var(--text-3); margin: 2px 0 0; letter-spacing: 0.2px; }
#topbar .badges { margin-left: auto; display: flex; gap: 6px; }
#topbar .badge {
  background: var(--bg-card);
  border: 1px solid var(--border-accent);
  color: var(--purple-3);
  padding: 3px 10px; border-radius: 20px;
  font-size: 10.5px; font-weight: 500; letter-spacing: 0.2px;
}

/* ── Chatbot ── */
#chatbot {
  background: var(--bg-base) !important;
  border: none !important;
  border-radius: 0 !important;
  min-height: 480px;
  padding: 8px 0 !important;
}

.message-wrap { padding: 8px 24px !important; }

.message.user .bubble-wrap .md {
  background: var(--bg-bubble-user) !important;
  border: 1px solid var(--border-accent) !important;
  border-radius: 16px 4px 16px 16px !important;
  color: var(--purple-4) !important;
  padding: 11px 15px !important;
  font-size: 13.5px !important;
  max-width: 70% !important;
  margin-left: auto !important;
}

.message.bot .bubble-wrap .md {
  background: var(--bg-bubble-bot) !important;
  border: 1px solid var(--border) !important;
  border-radius: 4px 16px 16px 16px !important;
  color: var(--text-2) !important;
  padding: 15px 19px !important;
  font-size: 13px !important;
  line-height: 1.7 !important;
  max-width: 88% !important;
}

.message.bot .avatar-container {
  background: var(--purple-1) !important;
  border-radius: 50% !important;
  width: 30px !important; height: 30px !important;
}

/* Markdown inside bot bubble */
.message.bot .bubble-wrap h2 {
  font-size: 14px !important; font-weight: 700 !important;
  color: var(--purple-4) !important;
  margin-bottom: 6px !important;
  border: none !important; padding: 0 !important;
  letter-spacing: -0.2px !important;
}
.message.bot .bubble-wrap h3 {
  font-size: 11px !important; font-weight: 600 !important;
  color: var(--purple-3) !important;
  margin: 14px 0 7px !important;
  padding-left: 8px !important;
  border-left: 2px solid var(--purple-1) !important;
  text-transform: uppercase !important;
  letter-spacing: 0.5px !important;
}
.message.bot .bubble-wrap strong { color: var(--text-1) !important; }
.message.bot .bubble-wrap em { color: var(--text-3) !important; font-size: 11px !important; }
.message.bot .bubble-wrap hr { border-color: var(--border) !important; margin: 12px 0 !important; }
.message.bot .bubble-wrap a { color: var(--purple-3) !important; }
.message.bot .bubble-wrap a:hover { color: var(--purple-4) !important; }
.message.bot .bubble-wrap code {
  background: rgba(91,33,182,0.18) !important;
  color: var(--purple-3) !important;
  border: 1px solid rgba(91,33,182,0.25) !important;
  border-radius: 5px !important;
  padding: 1px 6px !important;
  font-family: 'JetBrains Mono', monospace !important;
  font-size: 11px !important;
}
.message.bot .bubble-wrap blockquote {
  border-left: 2px solid #f59e0b !important;
  background: rgba(245,158,11,0.08) !important;
  padding: 8px 14px !important;
  border-radius: 0 8px 8px 0 !important;
  margin: 8px 0 !important;
}
.message.bot .bubble-wrap blockquote p { color: #fbbf24 !important; font-size: 12.5px !important; }

/* Tables in bot bubble */
.message.bot .bubble-wrap table {
  width: 100% !important; border-collapse: collapse !important;
  margin: 10px 0 !important; font-size: 12px !important;
}
.message.bot .bubble-wrap thead tr { background: rgba(91,33,182,0.14) !important; }
.message.bot .bubble-wrap th {
  color: var(--purple-3) !important; font-weight: 600 !important;
  padding: 7px 11px !important; text-align: left !important;
  border-bottom: 1px solid var(--border-accent) !important;
  font-size: 10px !important; text-transform: uppercase !important; letter-spacing: 0.5px !important;
}
.message.bot .bubble-wrap td {
  padding: 7px 11px !important; border-bottom: 1px solid var(--border) !important;
  color: var(--text-2) !important;
}
.message.bot .bubble-wrap tbody tr:last-child td { border-bottom: none !important; }
.message.bot .bubble-wrap tbody tr:hover { background: rgba(91,33,182,0.04) !important; }

/* ── Input area ── */
#input-row {
  background: var(--bg-surface);
  border-top: 1px solid var(--border);
  padding: 14px 20px;
  display: flex;
  gap: 10px;
  align-items: flex-end;
}

#chat-input textarea {
  background: var(--bg-input) !important;
  border: 1px solid var(--border) !important;
  border-radius: 11px !important;
  color: var(--text-1) !important;
  font-family: 'Inter', sans-serif !important;
  font-size: 13.5px !important;
  padding: 11px 15px !important;
  resize: none !important;
  transition: border-color 0.2s, box-shadow 0.2s !important;
  caret-color: var(--purple-3);
}
#chat-input textarea:focus {
  border-color: var(--border-glow) !important;
  box-shadow: 0 0 0 3px rgba(91,33,182,0.14) !important;
  outline: none !important;
}
#chat-input textarea::placeholder { color: var(--text-3) !important; }

#send-btn {
  background: var(--purple-1) !important;
  border: none !important; border-radius: 11px !important;
  color: #fff !important; font-weight: 600 !important;
  font-size: 13px !important; padding: 11px 20px !important;
  cursor: pointer !important;
  transition: background 0.2s, transform 0.15s !important;
  white-space: nowrap;
  letter-spacing: 0.2px;
}
#send-btn:hover {
  background: var(--purple-2) !important;
  transform: translateY(-1px) !important;
}
#send-btn:active { transform: scale(0.98) !important; }

/* ── Example chips ── */
#examples-row {
  background: var(--bg-surface);
  border-top: 1px solid var(--border);
  padding: 11px 20px 13px;
  display: flex; flex-wrap: wrap; gap: 7px; align-items: center;
}
#examples-label {
  font-size: 10px; text-transform: uppercase;
  letter-spacing: 1px; color: var(--text-3); font-weight: 600;
  margin-right: 4px; white-space: nowrap;
}
.example-chip button {
  background: var(--bg-input) !important;
  border: 1px solid var(--border) !important;
  border-radius: 20px !important;
  color: var(--purple-3) !important;
  font-family: 'JetBrains Mono', monospace !important;
  font-size: 11px !important; font-weight: 500 !important;
  padding: 4px 13px !important;
  cursor: pointer !important;
  transition: all 0.15s !important;
  letter-spacing: 0.1px !important;
}
.example-chip button:hover {
  background: rgba(91,33,182,0.15) !important;
  border-color: var(--border-glow) !important;
  color: var(--purple-4) !important;
  transform: translateY(-1px) !important;
}

/* ── Downloads ── */
#dl-header {
  padding: 14px 24px 6px;
  font-size: 10px; text-transform: uppercase;
  letter-spacing: 1px; color: var(--text-3); font-weight: 600;
  background: #0c0b1a;
  border-top: 1px solid var(--border);
}
#downloads {
  background: #0c0b1a;
  padding: 8px 20px 20px;
  display: grid !important;
  grid-template-columns: repeat(4, 1fr) !important;
  gap: 9px !important;
}
#downloads .gr-file-preview, .file-preview {
  background: var(--bg-card) !important;
  border: 1px solid var(--border) !important;
  border-radius: 10px !important;
  color: var(--text-2) !important;
  transition: border-color 0.2s, background 0.2s;
}
#downloads .gr-file-preview:hover {
  border-color: var(--border-glow) !important;
  background: rgba(91,33,182,0.08) !important;
}

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--border-glow); border-radius: 4px; }

/* ── Gradio overrides ── */
.gr-group, .gr-box { background: transparent !important; border: none !important; }
.gap-4 { gap: 0 !important; }
.gr-padded { padding: 0 !important; }
"""

with gr.Blocks(
    title="Market Scout — Competitive Intelligence",
    theme=gr.themes.Soft(primary_hue="blue", neutral_hue="slate"),
    css=CSS,
) as demo:

    gr.HTML("""
    <div id="header">
      <h1>🔍 Market Scout</h1>
      <p>AI-powered Competitive Intelligence &nbsp;·&nbsp;
         Google ADK &nbsp;·&nbsp; Groq LLaMA 3.3 &nbsp;·&nbsp; Tavily Search</p>
    </div>
    """)

    with gr.Row():
        with gr.Column(scale=3):
            user_input = gr.Textbox(
                label="Company or query",
                placeholder="e.g.  Stripe   |   Track Tesla   |   Compare PayPal and Stripe",
                lines=1,
                autofocus=True,
            )
            run_btn = gr.Button("🚀 Run Analysis", variant="primary", size="lg")

        with gr.Column(scale=1):
            gr.Markdown("""
**Quick examples:**
- `Stripe`
- `Track Tesla`
- `Compare PayPal and Stripe`
- `Nike latest features`
- `OpenAI, Anthropic`
            """)

    report_out = gr.Markdown(
        value="*Enter a company name above and click Run Analysis.*",
        label="Report",
        elem_classes=["report-box"],
    )

    gr.Markdown("### 📎 Download Reports")
    with gr.Row():
        pdf_out      = gr.File(label="📄 PDF Report",      visible=True, interactive=False)
        excel_out    = gr.File(label="📊 Excel Workbook",  visible=True, interactive=False)
        briefing_out = gr.File(label="📝 Text Briefing",   visible=True, interactive=False)
        dashboard_out= gr.File(label="🌐 HTML Dashboard",  visible=True, interactive=False)

    gr.Examples(
        examples=EXAMPLES,
        inputs=user_input,
        label="Example queries",
    )

    # Wire up button and Enter key
    run_btn.click(
        fn=handle_query,
        inputs=user_input,
        outputs=[report_out, pdf_out, excel_out, briefing_out, dashboard_out],
    )
    user_input.submit(
        fn=handle_query,
        inputs=user_input,
        outputs=[report_out, pdf_out, excel_out, briefing_out, dashboard_out],
    )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7860))
    demo.launch(
        server_name="0.0.0.0",
        server_port=port,
        share=False,
        show_error=True,
    )
