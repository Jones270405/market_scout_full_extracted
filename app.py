import gradio as gr
import os

# Paste your FULL CSS here
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

WELCOME_MSG = """
## 👋 Welcome to Market Scout

I help you track and analyse competitor product updates in real time.

### Try asking:
- `Track Stripe`
- `What's new at Tesla?`
- `Compare Stripe and PayPal`
- `Nike latest features`
"""

# --- Bot logic ---
def respond(message, history):
    history = history or []

    # Append user message
    history.append({"role": "user", "content": message})

    # Dummy response (replace with your backend)
    bot_reply = f"""
## 📊 Analysis for: {message}

### Key Insights
- Strong market activity
- New feature releases detected
- Competitive positioning evolving

### Summary
This is a simulated intelligence report.
"""

    history.append({"role": "assistant", "content": bot_reply})

    return history, ""

# Example chip click
def fill_input(text):
    return text

# --- UI ---
with gr.Blocks(css=CSS, theme=gr.themes.Base()) as demo:

    # 🔝 Topbar
    gr.HTML("""
    <div id="topbar">
        <div class="logo"></div>
        <div>
            <h2>Market Scout</h2>
            <p>Competitive Intelligence Assistant</p>
        </div>
        <div class="badges">
            <div class="badge">LIVE</div>
            <div class="badge">AI</div>
        </div>
    </div>
    """)

    # 💬 Chatbot
    chatbot = gr.Chatbot(
        value=[{"role": "assistant", "content": WELCOME_MSG}],
        elem_id="chatbot",
        show_label=False,
        height=500,
    )

    # ⌨️ Input row
    with gr.Row(elem_id="input-row"):
        user_input = gr.Textbox(
            placeholder="Ask something...",
            show_label=False,
            elem_id="chat-input",
        )
        send_btn = gr.Button("Send", elem_id="send-btn")

    # ⚡ Example chips
    with gr.Row(elem_id="examples-row"):
        gr.Markdown('<span id="examples-label">Examples:</span>')
        
        ex1 = gr.Button("Track Stripe", elem_classes="example-chip")
        ex2 = gr.Button("What's new at Tesla?", elem_classes="example-chip")
        ex3 = gr.Button("Compare Stripe and PayPal", elem_classes="example-chip")
        ex4 = gr.Button("Nike latest features", elem_classes="example-chip")

    # 🔗 Events
    send_btn.click(respond, [user_input, chatbot], [chatbot, user_input])
    user_input.submit(respond, [user_input, chatbot], [chatbot, user_input])

    ex1.click(lambda: "Track Stripe", outputs=user_input)
    ex2.click(lambda: "What's new at Tesla?", outputs=user_input)
    ex3.click(lambda: "Compare Stripe and PayPal", outputs=user_input)
    ex4.click(lambda: "Nike latest features", outputs=user_input)


# 🚀 Launch (Render-ready)
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7860))

    demo.launch(
        server_name="0.0.0.0",
        server_port=port,
        show_error=True,
    )