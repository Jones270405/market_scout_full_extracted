import gradio as gr
import os

WELCOME_MSG = "## 👋 Welcome to Market Scout\nEnter a company name to generate a competitive intelligence report."

CSS = """
body {
    background-color: #0f172a;
    color: white;
}
"""

def generate_report(company_name):
    if not company_name:
        return "❌ Please enter a company name.", None

    # Dummy response (replace with your actual logic)
    report = f"""
## 📊 Competitive Report for {company_name}

- Market Position: Strong
- Competitors: A, B, C
- SWOT:
  - Strength: Brand
  - Weakness: Pricing
  - Opportunity: Expansion
  - Threat: Competition
    """

    # Optional file output (dummy)
    file_path = None

    return report, file_path


with gr.Blocks(title="Market Scout — Competitive Intelligence") as demo:

    gr.Markdown("# 🚀 Market Scout")
    gr.Markdown("Generate competitive intelligence reports instantly.")

    with gr.Row():
        company_input = gr.Textbox(
            placeholder="Enter company name...",
            label="Company",
        )
        submit_btn = gr.Button("Generate Report")

    report_out = gr.Markdown(WELCOME_MSG)
    file_out = gr.File(label="Download Report")

    submit_btn.click(
        fn=generate_report,
        inputs=company_input,
        outputs=[report_out, file_out],
    )

    company_input.submit(
        fn=generate_report,
        inputs=company_input,
        outputs=[report_out, file_out],
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7860))

    demo.launch(
        server_name="0.0.0.0",
        server_port=port,
        show_error=True,
        theme=gr.themes.Base(),
        css=CSS,
    )