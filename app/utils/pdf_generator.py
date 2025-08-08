from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
import os

def generate_invoice_pdf(invoice, client, services, output_path: str):
    doc = SimpleDocTemplate(output_path, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph(f"Invoice for {client['name']} {client['surname']}", styles['Title']))
    elements.append(Spacer(1, 12))

    elements.append(Paragraph(f"Email: {client['email']} | Phone: {client['phone']}", styles['Normal']))
    elements.append(Spacer(1, 12))

    elements.append(Paragraph(f"Invoice Date: {invoice['invoiceDate']}", styles['Normal']))
    elements.append(Paragraph(f"Due Date: {invoice['dueDate']}", styles['Normal']))
    elements.append(Spacer(1, 12))

    data = [["Service", "Price (£)"]]
    for s in services:
        data.append([s['description'], f"£{s['price']:.2f}"])
    data.append(["Total", f"£{invoice['total']:.2f}"])

    table = Table(data, hAlign="LEFT")
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
    ]))
    elements.append(table)

    doc.build(elements)
