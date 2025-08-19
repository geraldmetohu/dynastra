from fastapi import APIRouter, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from prisma import Prisma
from datetime import datetime, timedelta, date
import os, math, uuid

from app.core.email_utils import send_email
from app.core.pdf_utils2 import render_invoice_html, html_to_pdf

router = APIRouter(prefix="/admin", tags=["admin"])

def db_dep():
    db = Prisma()
    if not db.is_connected():
        db.connect()
    try:
        yield db
    finally:
        # keep connection for performance if you prefer; explicit close on shutdown
        ...

def money(v: str | float) -> float:
    return round(float(v), 2)

# ---------- Clients ----------
@router.get("/clients", response_class=HTMLResponse)
async def client_list(request: Request, db: Prisma = Depends(db_dep)):
    clients = await db.user.find_many(order={"createdAt": "desc"})
    return request.app.state.templates.TemplateResponse("admin/client_list.html", {"request": request, "clients": clients})

@router.get("/client/new", response_class=HTMLResponse)
async def client_new(request: Request):
    return request.app.state.templates.TemplateResponse("admin/new_client.html", {
        "request": request, "client": None, "form_action": "/admin/client/new"
    })

@router.post("/client/new")
async def client_create(
    request: Request,
    name: str = Form(...), surname: str = Form(...),
    phone: str = Form(...), email: str = Form(...),
    address: str | None = Form(None),
    dob: str | None = Form(None),
    place_of_birth: str | None = Form(None),
    sex: str | None = Form(None),
    client_type: str | None = Form(None),
    tasks: list[str] | None = Form(None),
    status: str | None = Form(None),
    description: str | None = Form(None),
    db: Prisma = Depends(db_dep)
):
    dto = {
        "role": "CLIENT", "name": name, "surname": surname, "phone": phone, "email": email,
        "address": address or None,
        "dateOfBirth": datetime.fromisoformat(dob).isoformat() if dob else None,
        "placeOfBirth": place_of_birth or None,
        "sex": sex or None,
        "clientType": client_type or None,
        "tasks": tasks or [],
        "status": status or None,
        "description": description or None,
    }
    try:
        await db.user.create(data=dto)
    except Exception as e:
        # Minimal error pass-through to template
        return request.app.state.templates.TemplateResponse("admin/new_client.html", {
            "request": request, "client": None, "form_action": "/admin/client/new",
            "error": f"{e}"
        })
    return RedirectResponse("/admin/clients", status_code=303)

# ---------- Invoices ----------
@router.get("/invoice/create/{client_id}", response_class=HTMLResponse)
async def invoice_form(request: Request, client_id: str, db: Prisma = Depends(db_dep)):
    clients = await db.user.find_many()
    return request.app.state.templates.TemplateResponse("admin/invoice_form.html", {
        "request": request, "clients": clients, "preselect_client_id": client_id
    })

@router.get("/invoice/create", response_class=HTMLResponse)
async def invoice_form_blank(request: Request, db: Prisma = Depends(db_dep)):
    clients = await db.user.find_many()
    return request.app.state.templates.TemplateResponse("admin/invoice_form.html", {
        "request": request, "clients": clients, "preselect_client_id": None
    })

@router.post("/invoice/preview", response_class=HTMLResponse)
async def invoice_preview(
    request: Request,
    client_id: str = Form(...),
    issue_date: str = Form(...),
    due_date: str = Form(...),
    notes: str | None = Form(None),
    service_description: list[str] = Form(default=[]),
    service_price: list[str] = Form(default=[]),
    db: Prisma = Depends(db_dep)
):
    client = await db.user.find_unique(where={"id": client_id})
    if not client:
        raise HTTPException(404, "Client not found")

    services = []
    for d, p in zip(service_description, service_price):
        services.append({"description": d.strip(), "price": money(p)})

    total = round(sum(s["price"] for s in services), 2)

    env = request.app.state.env  # pull shared env/company settings if you stored them
    context = {
        "client": client,
        "invoice": None,
        "services": services,
        "total": total,
        "issue_date": issue_date,
        "due_date": due_date,
        "notes": notes or "",
        "company_name": os.getenv("COMPANY_NAME"),
        "company_email": os.getenv("COMPANY_EMAIL"),
        "company_site": os.getenv("COMPANY_SITE"),
        "company_phone": os.getenv("COMPANY_PHONE"),
        "account_name": os.getenv("ACCOUNT_NAME"),
        "sort_code": os.getenv("SORT_CODE"),
        "account_number": os.getenv("ACCOUNT_NUMBER"),
        "iban": os.getenv("IBAN"),
        "logo_path": os.getenv("LOGO_PATH"),
    }
    return request.app.state.templates.TemplateResponse("admin/invoice_preview.html", {"request": request, **context})

@router.post("/invoice/save")
async def invoice_save(
    request: Request,
    client_id: str = Form(...),
    issue_date: str = Form(...),
    due_date: str = Form(...),
    notes: str | None = Form(None),
    service_description: list[str] = Form(default=[]),
    service_price: list[str] = Form(default=[]),
    invoice_type: str = Form("ONE_TIME"),        # ONE_TIME | MONTHLY | ANNUAL
    recurring: bool = Form(False),
    db: Prisma = Depends(db_dep)
):
    client = await db.user.find_unique(where={"id": client_id})
    if not client: raise HTTPException(404, "Client not found")

    services = [{"description": d.strip(), "price": money(p)} for d,p in zip(service_description, service_price)]
    total = round(sum(s["price"] for s in services), 2)

    inv = await db.invoice.create(
        data={
            "clientId": client_id,
            "invoiceType": invoice_type,                      # schema uses String, but your enum exists too
            "invoiceDate": datetime.fromisoformat(issue_date),
            "dueDate": datetime.fromisoformat(due_date),
            "total": total,
            "accountName": os.getenv("ACCOUNT_NAME"),
            "sortCode": os.getenv("SORT_CODE"),
            "accountNumber": os.getenv("ACCOUNT_NUMBER"),
            "iban": os.getenv("IBAN"),
            "logoPath": os.getenv("LOGO_PATH"),
            "services": { "create": services },
        },
        include={ "services": True, "client": True }
    )

    if recurring and invoice_type in ("MONTHLY", "ANNUAL"):
        next_run = (datetime.fromisoformat(issue_date) + (timedelta(days=30) if invoice_type=="MONTHLY" else timedelta(days=365)))
        await db.recurringinvoice.create(
            data={"invoiceId": inv.id, "frequency": "monthly" if invoice_type=="MONTHLY" else "annual", "nextRun": next_run}
        )

    return RedirectResponse(f"/admin/invoice/{inv.id}/preview", status_code=303)

@router.get("/invoice/{invoice_id}/preview", response_class=HTMLResponse)
async def invoice_preview_saved(request: Request, invoice_id: str, db: Prisma = Depends(db_dep)):
    invoice = await db.invoice.find_unique(
        where={"id": invoice_id},
        include={"client": True, "services": True}
    )
    if not invoice: raise HTTPException(404, "Invoice not found")

    context = {
        "invoice": invoice,
        "client": invoice.client,
        "services": invoice.services,
        "total": invoice.total,
        "issue_date": invoice.invoiceDate.strftime("%Y-%m-%d"),
        "due_date": invoice.dueDate.strftime("%Y-%m-%d"),
        "notes": "",
        "company_name": os.getenv("COMPANY_NAME"),
        "company_email": os.getenv("COMPANY_EMAIL"),
        "company_site": os.getenv("COMPANY_SITE"),
        "company_phone": os.getenv("COMPANY_PHONE"),
        "account_name": invoice.accountName,
        "sort_code": invoice.sortCode,
        "account_number": invoice.accountNumber,
        "iban": invoice.iban,
        "logo_path": invoice.logoPath,
    }
    return request.app.state.templates.TemplateResponse("admin/invoice_preview.html", {"request": request, **context})

@router.post("/invoice/send/{invoice_id}")
async def invoice_send(invoice_id: str, request: Request, db: Prisma = Depends(db_dep)):
    invoice = await db.invoice.find_unique(
        where={"id": invoice_id},
        include={"client": True, "services": True}
    )
    if not invoice: raise HTTPException(404, "Invoice not found")

    context = {
        "invoice": invoice,
        "client": invoice.client,
        "services": invoice.services,
        "total": invoice.total,
        "issue_date": invoice.invoiceDate.strftime("%Y-%m-%d"),
        "due_date": invoice.dueDate.strftime("%Y-%m-%d"),
        "company_name": os.getenv("COMPANY_NAME"),
        "company_email": os.getenv("COMPANY_EMAIL"),
        "company_site": os.getenv("COMPANY_SITE"),
        "company_phone": os.getenv("COMPANY_PHONE"),
        "account_name": invoice.accountName,
        "sort_code": invoice.sortCode,
        "account_number": invoice.accountNumber,
        "iban": invoice.iban,
        "logo_path": invoice.logoPath,
        "notes": "",
    }

    # 1) HTML → PDF
    html = render_invoice_html(context)
    out_dir = os.getenv("PDF_OUTPUT_DIR", "/app/static/invoices")
    pdf_path = os.path.join(out_dir, f"{invoice.id}.pdf")
    html_to_pdf(html, pdf_path)

    # 2) Send email
    subject = f"Invoice {invoice.invoiceDate.strftime('%Y%m%d')}-{invoice.id[:6]} — £{invoice.total:.2f}"
    body = f"""
    <div style="font-family:Arial,sans-serif">
      <p>Hello {invoice.client.name},</p>
      <p>Please find attached your invoice. Total due: <strong>£{invoice.total:.2f}</strong> by {invoice.dueDate.strftime('%d %b %Y')}.</p>
      <p>Account: <strong>{invoice.accountName}</strong><br/>
         Sort code: <strong>{invoice.sortCode}</strong> • Account no: <strong>{invoice.accountNumber}</strong><br/>
         IBAN: <strong>{invoice.iban or '-'}</strong>
      </p>
      <p>Thanks,<br/>{os.getenv("COMPANY_NAME")}</p>
    </div>
    """
    send_email(invoice.client.email, subject, body, attachments=[pdf_path])

    await db.invoice.update(where={"id": invoice.id}, data={"sent": True, "pdfPath": pdf_path})
    return RedirectResponse(f"/admin/invoice/{invoice.id}/preview", status_code=303)

# ---------- Marketing ----------
@router.get("/marketing/send/{client_id}", response_class=HTMLResponse)
async def marketing_form(request: Request, client_id: str, db: Prisma = Depends(db_dep)):
    client = await db.user.find_unique(where={"id": client_id})
    if not client: raise HTTPException(404, "Client not found")
    return request.app.state.templates.TemplateResponse("admin/marketing_form.html", {"request": request, "client": client})

@router.post("/marketing/send")
async def marketing_send(
    client_id: str = Form(...),
    subject: str = Form(...),
    content: str = Form(...),
    attachments: list[str] | None = Form(None),   # paths to files you choose via UI (optional)
    repeat: str | None = Form(None),              # DAILY | WEEKLY | MONTHLY | (or empty for one-time)
    db: Prisma = Depends(db_dep)
):
    client = await db.user.find_unique(where={"id": client_id})
    if not client: raise HTTPException(404, "Client not found")

    # send immediately
    send_email(client.email, subject, content, attachments=attachments or [])
    msg = await db.message.create(data={
        "subject": subject, "content": content, "fromEmail": os.getenv("FROM_EMAIL"),
        "toEmail": client.email
    })
    if repeat:
        await db.repeatrule.create(data={"messageId": msg.id, "frequency": repeat})
    return RedirectResponse(f"/admin/clients", status_code=303)
