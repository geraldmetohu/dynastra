# app/routes/admin_marketing.py
from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from app.db import prisma
from app.core.email_utils import send_email

router = APIRouter(prefix="/admin", tags=["marketing"])

def _templates(request: Request):
    return getattr(request.app, "templates", request.app.state.templates)

def _require_admin(request: Request):
    return request.session.get("is_admin", False)

# Optional index page (not required by your buttons)
@router.get("/marketing", response_class=HTMLResponse)
async def marketing_index(request: Request):
    if not _require_admin(request):
        return RedirectResponse("/admin/login", status_code=303)
    clients = await prisma.user.find_many()
    return _templates(request).TemplateResponse(
        "admin/marketing_index.html",
        {"request": request, "clients": clients},
    )

# Send form for a single client
@router.get("/marketing/send/{client_id}", response_class=HTMLResponse)
async def marketing_form(request: Request, client_id: str):
    if not _require_admin(request):
        return RedirectResponse("/admin/login", status_code=303)
    client = await prisma.user.find_unique(where={"id": client_id})
    if not client:
        return RedirectResponse("/admin/clients", status_code=303)
    templates = [
        {"id": "invoice_reminder", "name": "Invoice Reminder", "subject": "Reminder: Invoice due", "content": "Hi {name},\nJust a friendly reminder your invoice is due.\nThanks,\n{company}"},
        {"id": "promo", "name": "New Services", "subject": "What’s new at {company}", "content": "Hi {name},\nWe’ve launched new services that might help you.\nCheers,\n{company}"},
    ]
    return _templates(request).TemplateResponse(
        "admin/marketing_form.html",
        {"request": request, "client": client, "templates": templates, "sent": False, "error": None},
    )

# Handle send
@router.post("/marketing/send", response_class=HTMLResponse)
async def marketing_send(
    request: Request,
    client_id: str = Form(...),
    subject: str = Form(...),
    message: str = Form(...),
):
    if not _require_admin(request):
        return RedirectResponse("/admin/login", status_code=303)

    client = await prisma.user.find_unique(where={"id": client_id})
    if not client:
        return RedirectResponse("/admin/clients", status_code=303)

    # simple placeholder substitutions
    company = request.app.templates.env.globals.get("company_name") or "Dynastra Tech"
    body = (
        message.replace("{name}", client.name)
               .replace("{company}", company)
    )

    ok = True
    try:
        send_email(client.email, subject, f"<pre style='font-family:inherit;white-space:pre-wrap'>{body}</pre>")
    except Exception as e:
        print("Marketing email failed:", e)
        ok = False

    templates = [
        {"id": "invoice_reminder", "name": "Invoice Reminder", "subject": "Reminder: Invoice due", "content": "Hi {name},\nJust a friendly reminder your invoice is due.\nThanks,\n{company}"},
        {"id": "promo", "name": "New Services", "subject": "What’s new at {company}", "content": "Hi {name},\nWe’ve launched new services that might help you.\nCheers,\n{company}"},
    ]
    return _templates(request).TemplateResponse(
        "admin/marketing_form.html",
        {"request": request, "client": client, "templates": templates, "sent": ok, "error": None if ok else "Send failed"},
    )
