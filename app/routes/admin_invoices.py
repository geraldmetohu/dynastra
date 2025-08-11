# app/routes/admin_invoices.py

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse

# If your auth lives under app.backend.utils.auth keep this import;
# otherwise switch to app.utils.auth (uncomment the fallback).
from app.backend.utils.auth import require_admin
# from app.utils.auth import require_admin

from app.db import prisma

router = APIRouter(
    prefix="/admin",
    tags=["Admin Invoices"],
    dependencies=[Depends(require_admin)],
)

@router.get("/invoices", response_class=HTMLResponse)
async def invoices_index(request: Request):
    # Use the shared prisma instance directly
    clients = await prisma.user.find_many(
        where={"role": "CLIENT"},
        order={"createdAt": "desc"},
    )
    return request.app.templates.TemplateResponse(
        "admin/invoice_form.html",
        {"request": request, "clients": clients},
    )

@router.post("/invoice/preview", response_class=HTMLResponse)
async def invoice_preview(request: Request):
    form = await request.form()

    client_id = form.get("client_id")
    issue_date = form.get("issue_date")
    due_date = form.get("due_date")
    notes = form.get("notes") or ""

    descriptions = form.getlist("service_description[]")
    prices = form.getlist("service_price[]")

    services = []
    total = 0.0
    for d, p in zip(descriptions, prices):
        if not d:
            continue
        try:
            amt = float(p)
        except Exception:
            amt = 0.0
        total += amt
        services.append({"description": d, "price": amt})

    return request.app.templates.TemplateResponse(
        "admin/invoice_preview.html",
        {
            "request": request,
            "client_id": client_id,
            "issue_date": issue_date,
            "due_date": due_date,
            "notes": notes,
            "services": services,
            "total": total,
        },
    )
