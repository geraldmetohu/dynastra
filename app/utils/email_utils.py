import smtplib
from email.message import EmailMessage
from pathlib import Path

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_FROM = "your-email@gmail.com"
EMAIL_PASSWORD = "your-app-password"

def send_invoice_email(to_email: str, subject: str, body: str, pdf_filename: str):
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = EMAIL_FROM
    msg["To"] = to_email
    msg.set_content(body)

    # Attach PDF
    pdf_path = Path("app/static/invoices") / pdf_filename
    with open(pdf_path, "rb") as f:
        msg.add_attachment(f.read(), maintype="application", subtype="pdf", filename=pdf_filename)

    # Send
    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(EMAIL_FROM, EMAIL_PASSWORD)
        server.send_message(msg)
