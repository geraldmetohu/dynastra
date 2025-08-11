# app/routes/admin_invoices.py
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from app.backend.utils.auth import require_admin
from app.generated.prisma import Prisma
from app.db import prisma as shared_prisma

router = APIRouter(prefix="/admin", tags=["Admin Invoices"], dependencies=[Depends(require_admin)])

def get_prisma() -> Prisma:
    return shared_prisma

@router.get("/invoices", response_class=HTMLResponse)
async def invoices_index(request: Request, prisma: Prisma = Depends(get_prisma)):
    # show the form directly (you can later add a list+form if you want)
    clients = await prisma.user.find_many(where={"role": "CLIENT"}, order={"createdAt": "desc"})
    return request.app.templates.TemplateResponse(
        "admin/invoice_form.html",
        {"request": request, "clients": clients},
    )

# Handle the form submit (preview step)
@router.post("/invoice/preview", response_class=HTMLResponse)
async def invoice_preview(request: Request):
    form = await request.form()

    client_id = form.get("client_id")
    issue_date = form.get("issue_date")
    due_date = form.get("due_date")
    notes = form.get("notes") or ""

    # Services come as arrays
    descriptions = form.getlist("service_description[]")
    prices = form.getlist("service_price[]")

    services = []
    total = 0.0
    for d, p in zip(descriptions, prices):
        if not d:
            continue
        try:
            amt = float(p)
        except:
            amt = 0.0
        total += amt
        services.append({"description": d, "price": amt})

    # You can render a preview template or reuse the same with a summary block.
    return request.app.templates.TemplateResponse(
        "admin/invoice_preview.html",  # create this if you want a nice preview
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
