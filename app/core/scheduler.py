import os
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from prisma import Prisma
from app.core.email_utils import send_email
from app.core.pdf_utils2 import render_invoice_html, html_to_pdf

db = Prisma()
scheduler = BackgroundScheduler(timezone="Europe/London")

def _ensure_db():
    if not db.is_connected():
        db.connect()

def roll_date(base: datetime, freq: str) -> datetime:
    return base + (timedelta(days=30) if freq.lower()=="monthly" else timedelta(days=365))

def run_recurring_invoices():
    _ensure_db()
    today = datetime.now()
    recurs = db.recurringinvoice.find_many(where={ "nextRun": { "lte": today } }, include={"invoice": { "include": {"client": True, "services": True} }})
    for r in recurs:
        src = r.invoice
        client = src.client
        services = src.services

        new_issue = today
        new_due = today + timedelta(days=14)
        total = round(sum(s.price for s in services), 2)

        new_inv = db.invoice.create(data={
            "clientId": client.id,
            "invoiceType": src.invoiceType,
            "invoiceDate": new_issue,
            "dueDate": new_due,
            "total": total,
            "accountName": src.accountName,
            "sortCode": src.sortCode,
            "accountNumber": src.accountNumber,
            "iban": src.iban,
            "logoPath": src.logoPath,
            "services": {"create": [{"description": s.description, "price": s.price} for s in services]},
        }, include={"client": True, "services": True})

        context = {
            "invoice": new_inv,
            "client": new_inv.client,
            "services": new_inv.services,
            "total": new_inv.total,
            "issue_date": new_inv.invoiceDate.strftime("%Y-%m-%d"),
            "due_date": new_inv.dueDate.strftime("%Y-%m-%d"),
            "company_name": os.getenv("COMPANY_NAME"),
            "company_email": os.getenv("COMPANY_EMAIL"),
            "company_site": os.getenv("COMPANY_SITE"),
            "company_phone": os.getenv("COMPANY_PHONE"),
            "account_name": new_inv.accountName,
            "sort_code": new_inv.sortCode,
            "account_number": new_inv.accountNumber,
            "iban": new_inv.iban,
            "logo_path": new_inv.logoPath,
            "notes": "",
        }

        html = render_invoice_html(context)
        out_dir = os.getenv("PDF_OUTPUT_DIR", "/app/static/invoices")
        pdf_path = os.path.join(out_dir, f"{new_inv.id}.pdf")
        html_to_pdf(html, pdf_path)

        subject = f"Invoice {new_inv.invoiceDate.strftime('%Y%m%d')}-{new_inv.id[:6]} — £{new_inv.total:.2f}"
        body = f"<p>Hello {client.name}, your recurring invoice is attached. Total: £{new_inv.total:.2f}.</p>"
        send_email(client.email, subject, body, [pdf_path])
        db.invoice.update(where={"id": new_inv.id}, data={"sent": True, "pdfPath": pdf_path})

        db.recurringinvoice.update(where={"id": r.id}, data={"nextRun": roll_date(datetime.now(), r.frequency)})

def run_marketing():
    _ensure_db()
    rules = db.repeatrule.find_many(include={"message": True})
    for rr in rules:
        msg = rr.message
        # simple cadence gate (send once per cadence per day)
        # You can record lastSent in Message if you want stricter control.
        send_email(msg.toEmail, msg.subject, msg.content, [])
        db.message.update(where={"id": msg.id}, data={"sentAt": datetime.now()})

def start():
    scheduler.add_job(run_recurring_invoices, "cron", minute="*/15")  # check every 15 minutes
    scheduler.add_job(run_marketing, "cron", hour="9")                # daily 09:00
    scheduler.start()
