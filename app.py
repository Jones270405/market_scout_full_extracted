import gradio as gr
import os

CSS = """
body {
    background-color: #0f172a;
    color: #e5e7eb;
    font-family: 'Inter', sans-serif;
}

.container {
    max-width: 900px;
    margin: auto;
}

.header {
    font-size: 26px;
    font-weight: 700;
    margin-bottom: 10px;
}

.subtext {
    color: #9ca3af;
    margin-bottom: 20px;
}

.table {
    width: 100%;
    border-collapse: collapse;
    margin-top: 20px;
    background: #1f2937;
    border-radius: 10px;
    overflow: hidden;
}

.table th, .table td {
    padding: 14px;
    text-align: left;
}

.table th {
    background-color: #374151;
    color: #d1d5db;
}

.table tr {
    border-bottom: 1px solid #374151;
}

.badge {
    background: #374151;
    padding: 6px 10px;
    border-radius: 6px;
    font-family: monospace;
    color: #e5e7eb;
}

.gr-button {
    background-color: #7c3aed !important;
    color: white !important;
    border-radius: 8px !important;
}

textarea, input {
    background-color: #1f2937 !important;
    color: white !important;
    border: 1px solid #374151 !important;
}
"""

WELCOME_HTML = """
<div class="container">
    <div class="header">🌸 👋 Welcome to Market Scout — Competitive Intelligence Assistant!</div>
    <div class="subtext">
        I help you track and analyse competitor product updates in real time.
    </div>

    <h3>Here's what you can ask me:</h3>

    <table class="table">
        <tr>
            <th>Example Query</th>
            <th>What happens</th>
        </tr>
        <tr>
            <td><span class="badge">Track Stripe</span></td>
            <td>Full intelligence run for Stripe</td>
        </tr>
        <tr>
            <td><span class="badge">What's new at Tesla?</span></td>
            <td>Latest feature updates for Tesla</td>
        </tr>
        <tr>
            <td><span class="badge">Compare Stripe and PayPal</span></td>
            <td>Side-by-side analysis of both</td>
        </tr>
        <tr>
            <td><span class="badge">Nike latest features</span></td>
            <td>Recent product moves by Nike</td>
        </tr>
    </table>
</div>
"""

def generate_report(company):
    if not company:
        return "❌ Please enter a query."

    return f"""
## 📊 Results for: {company}

- Insight 1: Example finding  
- Insight 2: Competitive positioning  
- Insight 3: Recent updates  
"""

with gr.Blocks(title="Market Scout") as demo:

    gr.HTML(WELCOME_HTML)

    with gr.Row():
        user_input = gr.Textbox(
            placeholder="Ask something like: Compare Stripe and PayPal...",
            show_label=False,
        )
        submit_btn = gr.Button("Run")

    output = gr.Markdown()

    submit_btn.click(
        fn=generate_report,
        inputs=user_input,
        outputs=output,
    )

    user_input.submit(
        fn=generate_report,
        inputs=user_input,
        outputs=output,
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7860))
    demo.launch(
        server_name="0.0.0.0",
        server_port=port,
        css=CSS,
        theme=gr.themes.Base(),
    )