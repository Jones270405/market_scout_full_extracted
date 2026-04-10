# app.py  — Market Scout · Dark Purple UI
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
    text = re.sub(r"\s+(?:latest|recent|new|updates?|features?|releases?|news|info|information)$",
                  "", text, flags=re.IGNORECASE).strip()
    return text

def _check_input(text):
    if len(text) < MIN_QUERY_LEN: return f"⚠️ Query too short (min {MIN_QUERY_LEN} chars)."
    if len(text) > MAX_QUERY_LEN: return f"⚠️ Query too long (max {MAX_QUERY_LEN} chars)."
    lower = text.lower()
    for p in HARMFUL_PATTERNS:
        if re.search(p, lower): return "🚫 Harmful intent detected."
    for p in INJECTION_PATTERNS:
        if re.search(p, lower): return "🚫 Prompt injection detected."
    for p in OUT_OF_SCOPE:
        if re.search(p, lower): return "ℹ️ I only track competitor updates."
    return None

GREETINGS = {"hi","hello","hey","greetings","good morning","good afternoon","good evening","howdy","sup","yo"}

# ─── Main handler ─────────────────────────────────────────────────────────────

def handle_query(user_input):
    text = user_input.strip()
    if not text:
        yield "Please enter a company name.", None, None, None, None
        return
    if text.lower() in GREETINGS:
        yield "👋 Hello! Enter a company name to begin. Try `Stripe` or `Compare PayPal and Stripe`.", None, None, None, None
        return
    block = _check_input(text)
    if block:
        yield block, None, None, None, None
        return
    query = _extract_companies(text)
    if not query:
        yield "Please enter a company name. Example: `Stripe`", None, None, None, None
        return

    yield f"🔎 Analysing **{query}** — please wait 20–40 seconds…", None, None, None, None

    try:
        result = run_pipeline(query)
    except Exception as exc:
        yield (f"❌ **Pipeline error:** `{str(exc)}`\n\nEnsure **TAVILY_API_KEY** and **GROQ_API_KEY** are set in Render → Environment.",
               None, None, None, None)
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
        features_md = "> ⚠️ No features found. Check that **TAVILY_API_KEY** is set in Render → Environment.\n"

    comparison_md = f"\n### ⚖️ Comparison\n\n{comparison_table}\n" if comparison_table else ""

    report = f"""## 📊 {result['company']} — Intelligence Report
*{result['run_date']} &nbsp;·&nbsp; {result['version']}*

---

### 📈 Summary

| Timeframe | Count | Status |
|:----------|------:|:-------|
| **Total Features** | **{summary.get('total',0)}** | — |
| Last 7 Days | {summary.get('week',0)} | 🟢 WEEK |
| Last 30 Days | {summary.get('month',0)} | 🟡 MONTH |
| Last 365 Days | {summary.get('year',0)} | 🔵 YEAR |
| Unverified | {summary.get('unver',0)} | ⚪ |

---

### 🔑 Top Features

{features_md}{comparison_md}---

*Powered by Google ADK &nbsp;·&nbsp; Groq LLaMA 3.3 &nbsp;·&nbsp; Tavily Search*"""

    def _fp(key):
        p = files.get(key, "")
        return p if p and Path(p).exists() else None

    yield report, _fp("pdf"), _fp("excel"), _fp("briefing"), _fp("dashboard")

# ─── CSS ──────────────────────────────────────────────────────────────────────

CSS = """
/* ── Base & fonts ── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

:root {
  --bg-base:    #0d0d1a;
  --bg-surface: #13132b;
  --bg-card:    #1a1a35;
  --bg-input:   #1f1f3d;
  --border:     #2e2e5e;
  --border-glow:#7c3aed;
  --purple-1:   #7c3aed;
  --purple-2:   #9d5cf6;
  --purple-3:   #c084fc;
  --purple-4:   #e9d5ff;
  --accent:     #a855f7;
  --green:      #4ade80;
  --yellow:     #fbbf24;
  --blue:       #60a5fa;
  --red:        #f87171;
  --text-1:     #f1f0ff;
  --text-2:     #a89ec9;
  --text-3:     #6b63a0;
  --radius:     12px;
  --radius-lg:  18px;
  --shadow:     0 4px 24px rgba(124,58,237,0.15);
  --shadow-lg:  0 8px 40px rgba(124,58,237,0.25);
}

/* ── Page background ── */
body, .gradio-container, #root {
  background: var(--bg-base) !important;
  font-family: 'Inter', sans-serif !important;
  color: var(--text-1) !important;
  min-height: 100vh;
}

.gradio-container { max-width: 1100px !important; margin: 0 auto !important; padding: 0 20px 60px !important; }

footer, .footer { display: none !important; }
.svelte-1gfkn6j { display: none !important; }

/* ── Header ── */
#ms-header {
  text-align: center;
  padding: 48px 20px 32px;
  background: linear-gradient(180deg, rgba(124,58,237,0.08) 0%, transparent 100%);
  border-bottom: 1px solid var(--border);
  margin-bottom: 32px;
}
#ms-header h1 {
  font-size: 2.6rem;
  font-weight: 700;
  background: linear-gradient(135deg, #c084fc 0%, #7c3aed 50%, #4f46e5 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  letter-spacing: -0.5px;
  margin-bottom: 10px;
}
#ms-header p {
  color: var(--text-2);
  font-size: 0.95rem;
  letter-spacing: 0.5px;
}
#ms-header .badge {
  display: inline-block;
  background: rgba(124,58,237,0.2);
  border: 1px solid rgba(124,58,237,0.4);
  color: var(--purple-3);
  padding: 3px 12px;
  border-radius: 20px;
  font-size: 0.78rem;
  font-weight: 500;
  margin: 0 4px;
  letter-spacing: 0.3px;
}

/* ── Cards / panels ── */
.ms-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 24px;
  box-shadow: var(--shadow);
  transition: border-color 0.2s;
}
.ms-card:hover { border-color: rgba(124,58,237,0.4); }

/* ── Input box ── */
label.svelte-1b6s6s, .label-wrap { color: var(--text-2) !important; font-size: 0.82rem !important; text-transform: uppercase; letter-spacing: 1px; font-weight: 600; }

textarea, input[type=text], .gr-text-input {
  background: var(--bg-input) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--radius) !important;
  color: var(--text-1) !important;
  font-family: 'Inter', sans-serif !important;
  font-size: 1rem !important;
  padding: 14px 18px !important;
  transition: border-color 0.2s, box-shadow 0.2s !important;
  caret-color: var(--purple-2);
}
textarea:focus, input[type=text]:focus {
  border-color: var(--border-glow) !important;
  box-shadow: 0 0 0 3px rgba(124,58,237,0.15) !important;
  outline: none !important;
}

/* ── Run button ── */
button.primary, #run-btn {
  background: linear-gradient(135deg, #7c3aed 0%, #5b21b6 100%) !important;
  border: none !important;
  border-radius: var(--radius) !important;
  color: #fff !important;
  font-family: 'Inter', sans-serif !important;
  font-size: 1rem !important;
  font-weight: 600 !important;
  letter-spacing: 0.3px !important;
  padding: 14px 28px !important;
  cursor: pointer !important;
  transition: all 0.2s !important;
  box-shadow: 0 4px 15px rgba(124,58,237,0.4) !important;
  width: 100% !important;
}
button.primary:hover {
  background: linear-gradient(135deg, #9d5cf6 0%, #7c3aed 100%) !important;
  box-shadow: 0 6px 20px rgba(124,58,237,0.55) !important;
  transform: translateY(-1px) !important;
}
button.primary:active { transform: translateY(0) !important; }

/* ── Secondary buttons ── */
button.secondary {
  background: var(--bg-input) !important;
  border: 1px solid var(--border) !important;
  border-radius: 8px !important;
  color: var(--text-2) !important;
  font-size: 0.85rem !important;
  padding: 8px 16px !important;
  transition: all 0.2s !important;
}
button.secondary:hover {
  border-color: var(--border-glow) !important;
  color: var(--purple-3) !important;
  background: rgba(124,58,237,0.1) !important;
}

/* ── Report markdown ── */
.report-output {
  background: var(--bg-card) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--radius-lg) !important;
  padding: 28px 32px !important;
  min-height: 120px;
  box-shadow: var(--shadow);
}
.report-output h2 {
  font-size: 1.5rem !important;
  font-weight: 700 !important;
  color: var(--purple-3) !important;
  margin-bottom: 6px !important;
  border: none !important;
  padding: 0 !important;
}
.report-output h3 {
  font-size: 1.05rem !important;
  font-weight: 600 !important;
  color: var(--purple-4) !important;
  margin: 22px 0 10px !important;
  padding-left: 10px !important;
  border-left: 3px solid var(--purple-1) !important;
}
.report-output p, .report-output li {
  color: var(--text-2) !important;
  font-size: 0.93rem !important;
  line-height: 1.7 !important;
}
.report-output strong { color: var(--text-1) !important; font-weight: 600 !important; }
.report-output em { color: var(--text-3) !important; font-size: 0.85rem !important; }
.report-output hr { border-color: var(--border) !important; margin: 18px 0 !important; }
.report-output a { color: var(--purple-3) !important; text-decoration: none !important; }
.report-output a:hover { text-decoration: underline !important; color: var(--purple-4) !important; }
.report-output code {
  background: rgba(124,58,237,0.15) !important;
  color: var(--purple-3) !important;
  border: 1px solid rgba(124,58,237,0.25) !important;
  border-radius: 5px !important;
  padding: 1px 7px !important;
  font-family: 'JetBrains Mono', monospace !important;
  font-size: 0.82rem !important;
}
.report-output blockquote {
  border-left: 3px solid var(--yellow) !important;
  background: rgba(251,191,36,0.07) !important;
  padding: 10px 16px !important;
  border-radius: 0 8px 8px 0 !important;
  margin: 10px 0 !important;
}
.report-output blockquote p { color: var(--yellow) !important; }

/* ── Tables ── */
.report-output table {
  width: 100% !important;
  border-collapse: collapse !important;
  margin: 12px 0 !important;
  font-size: 0.9rem !important;
}
.report-output thead tr {
  background: rgba(124,58,237,0.2) !important;
}
.report-output th {
  color: var(--purple-3) !important;
  font-weight: 600 !important;
  padding: 10px 14px !important;
  text-align: left !important;
  border-bottom: 1px solid var(--border-glow) !important;
  font-size: 0.82rem !important;
  text-transform: uppercase !important;
  letter-spacing: 0.5px !important;
}
.report-output td {
  padding: 9px 14px !important;
  border-bottom: 1px solid var(--border) !important;
  color: var(--text-2) !important;
}
.report-output tbody tr:hover { background: rgba(124,58,237,0.06) !important; }

/* ── File download area ── */
#downloads-section .gr-file-preview, .file-preview {
  background: var(--bg-input) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--radius) !important;
  color: var(--text-2) !important;
}
.file-preview:hover { border-color: var(--border-glow) !important; }

/* ── Examples ── */
.examples-table td {
  background: var(--bg-input) !important;
  color: var(--purple-3) !important;
  border: 1px solid var(--border) !important;
  border-radius: 8px !important;
  font-family: 'JetBrains Mono', monospace !important;
  font-size: 0.85rem !important;
  padding: 8px 16px !important;
  cursor: pointer !important;
  transition: all 0.15s !important;
}
.examples-table td:hover {
  background: rgba(124,58,237,0.15) !important;
  border-color: var(--border-glow) !important;
  color: var(--purple-4) !important;
}
.examples-table th {
  color: var(--text-3) !important;
  font-size: 0.78rem !important;
  text-transform: uppercase !important;
  letter-spacing: 1px !important;
  background: transparent !important;
  border: none !important;
  padding-bottom: 8px !important;
}

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: var(--bg-base); }
::-webkit-scrollbar-thumb { background: var(--border-glow); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: var(--purple-2); }

/* ── Section labels ── */
.section-label {
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 1.2px;
  color: var(--text-3);
  font-weight: 600;
  margin-bottom: 10px;
}

/* ── Stats chips (in header area) ── */
.stat-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: rgba(124,58,237,0.12);
  border: 1px solid rgba(124,58,237,0.25);
  border-radius: 20px;
  padding: 5px 14px;
  font-size: 0.8rem;
  color: var(--text-2);
  margin: 3px;
}

/* ── Accordion / group ── */
.gr-group, .gr-box {
  background: var(--bg-card) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--radius-lg) !important;
}

/* ── Progress / loading ── */
.progress-bar { background: var(--purple-1) !important; }
.generating { border-color: var(--border-glow) !important; }

/* ── Row layout ── */
.gap-4 { gap: 16px !important; }
"""

# ─── Build UI ─────────────────────────────────────────────────────────────────

with gr.Blocks(
    title="Market Scout — Competitive Intelligence",
    theme=gr.themes.Base(),
    css=CSS,
) as demo:

    # Header
    gr.HTML("""
    <div id="ms-header">
      <h1>◈ Market Scout</h1>
      <p>
        <span class="badge">Google ADK</span>
        <span class="badge">Groq LLaMA 3.3</span>
        <span class="badge">Tavily Search</span>
      </p>
      <p style="margin-top:10px;font-size:0.88rem;color:#6b63a0;">
        AI-powered competitive intelligence · track features · generate reports
      </p>
    </div>
    """)

    # Input row
    with gr.Row(equal_height=True):
        with gr.Column(scale=4):
            user_input = gr.Textbox(
                label="COMPANY OR QUERY",
                placeholder="Stripe   ·   Track Tesla   ·   Compare PayPal and Stripe",
                lines=1,
                autofocus=True,
                container=True,
            )
            run_btn = gr.Button("⚡  Run Analysis", variant="primary", elem_id="run-btn")

        with gr.Column(scale=1, min_width=180):
            gr.HTML("""
            <div style="padding:16px 0 0 8px;">
              <div class="section-label">Quick Examples</div>
              <div style="display:flex;flex-direction:column;gap:6px;">
                <span class="stat-chip">Stripe</span>
                <span class="stat-chip">Track Tesla</span>
                <span class="stat-chip">Compare PayPal and Stripe</span>
                <span class="stat-chip">OpenAI, Anthropic</span>
              </div>
            </div>
            """)

    # Report output
    gr.HTML('<div class="section-label" style="margin-top:28px;margin-bottom:8px;">INTELLIGENCE REPORT</div>')
    report_out = gr.Markdown(
        value="""<div style="color:#6b63a0;font-size:0.9rem;padding:20px 0;">
        Enter a company name above and click ⚡ Run Analysis to generate a report.
        </div>""",
        elem_classes=["report-output"],
    )

    # Downloads
    gr.HTML('<div class="section-label" style="margin-top:28px;margin-bottom:8px;" id="downloads-section">DOWNLOAD REPORTS</div>')
    with gr.Row():
        pdf_out       = gr.File(label="📄  PDF Report",     interactive=False)
        excel_out     = gr.File(label="📊  Excel Workbook", interactive=False)
        briefing_out  = gr.File(label="📝  Text Briefing",  interactive=False)
        dashboard_out = gr.File(label="🌐  HTML Dashboard", interactive=False)

    # Example queries (clickable)
    gr.Examples(
        examples=[["Stripe"],["Track Tesla"],["Compare PayPal and Stripe"],["Nike latest features"],["OpenAI, Anthropic"]],
        inputs=user_input,
        label="Click an example to load it",
    )

    # Events
    run_btn.click(fn=handle_query, inputs=user_input,
                  outputs=[report_out, pdf_out, excel_out, briefing_out, dashboard_out])
    user_input.submit(fn=handle_query, inputs=user_input,
                      outputs=[report_out, pdf_out, excel_out, briefing_out, dashboard_out])

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7860))
    demo.launch(server_name="0.0.0.0", server_port=port, share=False, show_error=True)