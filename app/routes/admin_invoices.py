# app/routes/admin_invoices.py
import os
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse

from app.db import prisma
from app.core.email_utils import send_email
from app.core.pdf_utils2 import render_invoice_html, html_to_pdf

router = APIRouter(prefix="/admin", tags=["invoices"])


def _templates(request: Request):
    # works whether you stored templates in app.templates or app.state.templates
    return getattr(request.app, "templates", request.app.state.templates)


def _money(v: str | float) -> float:
    return round(float(v), 2)


# ---------- List (optional page)
@router.get("/invoices", response_class=HTMLResponse)
async def invoice_index(request: Request):
    invs = await prisma.invoice.find_many(
        include={"client": True},
        order={"createdAt": "desc"},
    )
    return _templates(request).TemplateResponse(
        "admin/invoice_list.html",
        {"request": request, "invoices": invs},
    )


# ---------- Create forms
@router.get("/invoice/create", response_class=HTMLResponse)
async def invoice_form_blank(request: Request):
    clients = await prisma.user.find_many()
    return _templates(request).TemplateResponse(
        "admin/invoice_form.html",
        {"request": request, "clients": clients, "preselect_client_id": None},
    )


@router.get("/invoice/create/{client_id}", response_class=HTMLResponse)
async def invoice_form_for_client(request: Request, client_id: str):
    clients = await prisma.user.find_many()
    return _templates(request).TemplateResponse(
        "admin/invoice_form.html",
        {"request": request, "clients": clients, "preselect_client_id": client_id},
    )


# ---------- Preview (from form)
@router.post("/invoice/preview", response_class=HTMLResponse)
async def invoice_preview(
    request: Request,
    client_id: str = Form(...),
    issue_date: str = Form(...),
    due_date: str = Form(...),
    notes: Optional[str] = Form(None),
    # multiple fields with the same name build a list:
    service_description: list[str] = Form(default=[]),
    service_price: list[str] = Form(default=[]),
):
    client = await prisma.user.find_unique(where={"id": client_id})
    if not client:
        clients = await prisma.user.find_many()
        return _templates(request).TemplateResponse(
            "admin/invoice_form.html",
            {"request": request, "clients": clients, "error": "Client not found"},
        )

    services = [
        {"description": d.strip(), "price": _money(p)}
        for d, p in zip(service_description, service_price)
        if d and d.strip()
    ]
    total = round(sum(s["price"] for s in services), 2)

    # Correct static URL for the logo
    logo_url = request.app.url_path_for("static", path="/logos/dynastra_dark.png")

    ctx = {
        "request": request,
        "invoice": None,  # template will use client/services/total instead
        "client": client,
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
        "logo_url": logo_url,
    }
    return _templates(request).TemplateResponse("admin/invoice_preview.html", ctx)


# ---------- Save (from preview)
@router.post("/invoice/save")
async def invoice_save(
    request: Request,
    client_id: str = Form(...),
    issue_date: str = Form(...),
    due_date: str = Form(...),
    notes: Optional[str] = Form(None),
    service_description: list[str] = Form(default=[]),
    service_price: list[str] = Form(default=[]),
    invoice_type: str = Form("ONE_TIME"),
):
    client = await prisma.user.find_unique(where={"id": client_id})
    if not client:
        raise HTTPException(404, "Client not found")

    services = [
        {"description": d.strip(), "price": _money(p)}
        for d, p in zip(service_description, service_price)
        if d and d.strip()
    ]
    total = round(sum(s["price"] for s in services), 2)

    inv = await prisma.invoice.create(
        data={
            "clientId": client_id,
            "invoiceType": invoice_type,
            "invoiceDate": datetime.fromisoformat(issue_date),
            "dueDate": datetime.fromisoformat(due_date),
            "total": total,
            "accountName": os.getenv("ACCOUNT_NAME"),
            "sortCode": os.getenv("SORT_CODE"),
            "accountNumber": os.getenv("ACCOUNT_NUMBER"),
            "iban": os.getenv("IBAN"),
            # stored value isn't used at render; we compute logo_url dynamically
            "logoPath": os.getenv("LOGO_PATH", "/static/logos/dynastra_dark.png"),
            "services": {"create": services},
        },
        include={"client": True, "services": True},
    )
    return RedirectResponse(f"/admin/invoice/{inv.id}/preview", status_code=303)


# ---------- Preview (saved invoice)
@router.get("/invoice/{invoice_id}/preview", response_class=HTMLResponse)
async def invoice_preview_saved(request: Request, invoice_id: str):
    invoice = await prisma.invoice.find_unique(
        where={"id": invoice_id},
        include={"client": True, "services": True},
    )
    if not invoice:
        raise HTTPException(404, "Invoice not found")

    logo_url = request.app.url_path_for("static", path="/logos/dynastra_dark.png")

    ctx = {
        "request": request,
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
        "logo_url": logo_url,
    }
    return _templates(request).TemplateResponse("admin/invoice_preview.html", ctx)


# ---------- Helpers for sending
def _default_subject(invoice) -> str:
    return (
        f"Invoice INV-{invoice.invoiceDate.strftime('%Y%m%d')}"
        f"-{invoice.id[:6].upper()} — £{invoice.total:.2f} "
        f"due {invoice.dueDate.strftime('%d %b %Y')} – {os.getenv('COMPANY_NAME')}"
    )


def _default_body(invoice) -> str:
    return f"""
<div style="font-family:Arial,sans-serif;line-height:1.6;color:#111">
  <p>Hi {invoice.client.name},</p>
  <p>Thanks for your business. Please find your invoice details below. The total due is
    <strong>£{invoice.total:.2f}</strong> by <strong>{invoice.dueDate.strftime('%d %b %Y')}</strong>.
  </p>
  <table cellpadding="0" cellspacing="0" style="border-collapse:collapse;margin:12px 0;width:100%;max-width:560px">
    <tr><td style="border:1px solid #ddd;padding:8px;background:#f8fafc"><strong>Invoice #</strong></td>
        <td style="border:1px solid #ddd;padding:8px">INV-{invoice.invoiceDate.strftime('%Y%m%d')}-{invoice.id[:6].upper()}</td></tr>
    <tr><td style="border:1px solid #ddd;padding:8px;background:#f8fafc"><strong>Issue date</strong></td>
        <td style="border:1px solid #ddd;padding:8px">{invoice.invoiceDate.strftime('%d %b %Y')}</td></tr>
    <tr><td style="border:1px solid #ddd;padding:8px;background:#f8fafc"><strong>Due date</strong></td>
        <td style="border:1px solid #ddd;padding:8px">{invoice.dueDate.strftime('%d %b %Y')}</td></tr>
    <tr><td style="border:1px solid #ddd;padding:8px;background:#f8fafc"><strong>Total</strong></td>
        <td style="border:1px solid #ddd;padding:8px"><strong>£{invoice.total:.2f}</strong></td></tr>
  </table>
  <p style="margin:16px 0 6px 0"><strong>Bank details</strong><br>
     Account name: {invoice.accountName}<br>
     Sort code: {invoice.sortCode} • Account no: {invoice.accountNumber}<br>
     IBAN: {invoice.iban or '-'}
  </p>
  <p>If you have any questions, just reply to this email.</p>
  <p>Best regards,<br>{os.getenv('COMPANY_NAME')}<br>{os.getenv('COMPANY_EMAIL')} · {os.getenv('COMPANY_PHONE')}</p>
</div>
""".strip()


def _generate_invoice_pdf(request: Request, invoice, ctx: dict) -> str | None:
    """
    Try WeasyPrint; if it fails (e.g., missing GTK on Windows), try ReportLab fallback.
    Returns the file path or None.
    """
    out_dir = os.getenv("PDF_OUTPUT_DIR", "app/static/invoices")
    os.makedirs(out_dir, exist_ok=True)
    pdf_path = os.path.join(out_dir, f"{invoice.id}.pdf")

    # Try WeasyPrint (html_to_pdf)
    try:
        html = render_invoice_html({**ctx, "request": request})
        html_to_pdf(html, pdf_path)
        return pdf_path
    except Exception as e:
        print("WeasyPrint failed:", e)

    # Fallback to ReportLab if available
    try:
        from app.core.pdf_utils2 import simple_invoice_pdf  # optional helper you can add
        simple_invoice_pdf(invoice, invoice.services, invoice.client, ctx, pdf_path)
        print("ReportLab fallback PDF created:", pdf_path)
        return pdf_path
    except Exception as e2:
        print("ReportLab fallback failed:", e2)
        return None


# ---------- Send
@router.post("/invoice/send/{invoice_id}")
async def invoice_send(
    request: Request,
    invoice_id: str,
    subject: Optional[str] = Form(None),
    body: Optional[str] = Form(None),
):
    invoice = await prisma.invoice.find_unique(
        where={"id": invoice_id},
        include={"client": True, "services": True},
    )
    if not invoice:
        raise HTTPException(404, "Invoice not found")

    # Build defaults if not provided
    subject = (subject or "").strip() or _default_subject(invoice)
    body = (body or "").strip() or _default_body(invoice)

    # Prepare context for PDF rendering
    logo_url = request.app.url_path_for("static", path="/logos/dynastra_dark.png")
    ctx = {
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
        "logo_url": logo_url,
        "notes": "",
    }

    pdf_path = _generate_invoice_pdf(request, invoice, ctx)
    attachments = [pdf_path] if (pdf_path and os.path.exists(pdf_path)) else []

    try:
        send_email(invoice.client.email, subject, body, attachments=attachments)
    except Exception as e:
        print("Email send failed:", e)
        # Don’t 500 the page—redirect with a flag you can show in the UI
        return RedirectResponse(f"/admin/invoice/{invoice.id}/preview?sent=0", status_code=303)

    await prisma.invoice.update(
        where={"id": invoice.id},
        data={"sent": True, "pdfPath": (pdf_path or None)},
    )
    return RedirectResponse(f"/admin/invoice/{invoice.id}/preview?sent=1", status_code=303)
