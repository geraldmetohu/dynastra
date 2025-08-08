from weasyprint import HTML
from jinja2 import Environment, FileSystemLoader
import os
import uuid

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "..", "templates")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "static", "invoices")

env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))

def generate_invoice_pdf(invoice_data: dict) -> str:
    template = env.get_template("admin/invoice_pdf_template.html")

    html_out = template.render(invoice=invoice_data)
    filename = f"invoice_{uuid.uuid4().hex}.pdf"
    output_path = os.path.join(OUTPUT_DIR, filename)

    HTML(string=html_out).write_pdf(output_path)
    return filename
