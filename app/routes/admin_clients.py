# app/routes/admin_clients.py
import json
from datetime import datetime
from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse
from app.db import prisma

router = APIRouter(prefix="/admin", tags=["clients"])

def _templates(request: Request):
    return getattr(request.app, "templates", request.app.state.templates)

def _require_admin(request: Request):
    return request.session.get("is_admin", False)

# ---------- List Clients (your existing page uses this)
@router.get("/clients", response_class=HTMLResponse)
async def client_list(request: Request):
    if not _require_admin(request):
        return RedirectResponse("/admin/login", status_code=303)
    clients = await prisma.user.find_many(order={"createdAt": "desc"})
    return _templates(request).TemplateResponse(
        "admin/client_list.html",
        {"request": request, "clients": clients},
    )

# ---------- Create: show form
@router.get("/client/new", response_class=HTMLResponse)
async def client_new(request: Request):
    if not _require_admin(request):
        return RedirectResponse("/admin/login", status_code=303)
    return _templates(request).TemplateResponse(
        "admin/new_client.html",
        {
            "request": request,
            "client": None,
            "error": None,
            "form_action": "/admin/client/save",
        },
    )

# ---------- Create: save
@router.post("/client/save")
async def client_save(
    request: Request,
    name: str = Form(...),
    surname: str = Form(...),
    phone: str = Form(...),
    email: str = Form(...),
    address: str | None = Form(None),
    dob: str | None = Form(None),
    place_of_birth: str | None = Form(None),
    sex: str | None = Form(None),
    client_type: str | None = Form(None),
    tasks: list[str] = Form(default=[]),
    status: str | None = Form(None),
    description: str | None = Form(None),
):
    if not _require_admin(request):
        return RedirectResponse("/admin/login", status_code=303)

    dob_dt = None
    if dob:
        try:
            dob_dt = datetime.fromisoformat(dob)
        except Exception:
            dob_dt = None

    await prisma.user.create(
        data={
            "name": name.strip(),
            "surname": surname.strip(),
            "phone": phone.strip(),
            "email": email.strip().lower(),
            "address": address or None,
            "dateOfBirth": dob_dt,
            "placeOfBirth": place_of_birth or None,
            "sex": sex or None,
            "clientType": client_type or None,
            "tasks": tasks or [],
            "status": status or None,
            "description": description or None,
        }
    )
    return RedirectResponse("/admin/clients", status_code=303)

# ---------- Edit: show form (reuses your new_client.html)
@router.get("/client/edit/{client_id}", response_class=HTMLResponse)
async def client_edit(request: Request, client_id: str):
    if not _require_admin(request):
        return RedirectResponse("/admin/login", status_code=303)
    client = await prisma.user.find_unique(where={"id": client_id})
    if not client:
        raise HTTPException(404, "Client not found")
    return _templates(request).TemplateResponse(
        "admin/new_client.html",
        {
            "request": request,
            "client": client,
            "error": None,
            "form_action": "/admin/client/update",
        },
    )

# ---------- Edit: save changes
@router.post("/client/update")
async def client_update(
    request: Request,
    client_id: str = Form(...),
    name: str = Form(...),
    surname: str = Form(...),
    phone: str = Form(...),
    email: str = Form(...),
    address: str | None = Form(None),
    dob: str | None = Form(None),
    place_of_birth: str | None = Form(None),
    sex: str | None = Form(None),
    client_type: str | None = Form(None),
    tasks: list[str] = Form(default=[]),
    status: str | None = Form(None),
    description: str | None = Form(None),
):
    if not _require_admin(request):
        return RedirectResponse("/admin/login", status_code=303)

    dob_dt = None
    if dob:
        try:
            dob_dt = datetime.fromisoformat(dob)
        except Exception:
            dob_dt = None

    await prisma.user.update(
        where={"id": client_id},
        data={
            "name": name.strip(),
            "surname": surname.strip(),
            "phone": phone.strip(),
            "email": email.strip().lower(),
            "address": address or None,
            "dateOfBirth": dob_dt,
            "placeOfBirth": place_of_birth or None,
            "sex": sex or None,
            "clientType": client_type or None,
            "tasks": tasks or [],
            "status": status or None,
            "description": description or None,
        },
    )
    return RedirectResponse("/admin/clients", status_code=303)

# ---------- Delete (simple)
# --- keep your other imports & routes above ---

# OLD (GET) delete route — make it a no-op/redirect to be safe (optional)
@router.get("/client/delete/{client_id}")
async def client_delete_get(request: Request, client_id: str):
    # Optional: redirect instead of deleting via GET
    return RedirectResponse("/admin/clients", status_code=303)

# NEW: real delete happens via POST + confirm()
@router.post("/client/delete/{client_id}")
async def client_delete_post(request: Request, client_id: str):
    if not request.session.get("is_admin"):
        return RedirectResponse("/admin/login", status_code=303)

    # delete invoices + children first to avoid FK issues
    invoices = await prisma.invoice.find_many(where={"clientId": client_id})
    for inv in invoices:
        await prisma.service.delete_many(where={"invoiceId": inv.id})
        await prisma.recurringinvoice.delete_many(where={"invoiceId": inv.id})
        await prisma.invoice.delete(where={"id": inv.id})

    # finally delete client (or soft-delete fallback)
    try:
        await prisma.user.delete(where={"id": client_id})
    except Exception:
        await prisma.user.update(where={"id": client_id}, data={"status": "Deleted"})
    return RedirectResponse("/admin/clients", status_code=303)

# ---------- View Invoices for a client
@router.get("/client/{client_id}/invoices", response_class=HTMLResponse)
async def client_invoices(request: Request, client_id: str):
    if not _require_admin(request):
        return RedirectResponse("/admin/login", status_code=303)

    client = await prisma.user.find_unique(where={"id": client_id})
    if not client:
        raise HTTPException(404, "Client not found")

    invs = await prisma.invoice.find_many(
        where={"clientId": client_id},
        include={"services": True},
        order={"createdAt": "desc"},
    )

    return _templates(request).TemplateResponse(
        "admin/client_invoices.html",
        {"request": request, "client": client, "invoices": invs},
    )
