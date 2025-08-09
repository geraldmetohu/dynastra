from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.templating import Jinja2Templates
from app.utils.email_sender import send_invoice_email
import os
from app.generated.prisma import Prisma

prisma = Prisma()

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/admin/invoice/send/{invoice_id}")
async def send_invoice_to_client(request: Request, invoice_id: str):
    invoice = await prisma.invoice.find_unique(
        where={"id": invoice_id},
        include={"client": True}
    )
    if not invoice:
        return RedirectResponse("/admin/dashboard", status_code=303)

    pdf_path = invoice.get("pdfPath")
    if not pdf_path or not os.path.exists(pdf_path):
        return HTMLResponse("⚠️ PDF not found. Please save the invoice first.", status_code=400)

    send_invoice_email(
        to_email=invoice["client"]["email"],
        client_name=invoice["client"]["name"],
        invoice_path=pdf_path
    )

    return templates.TemplateResponse("admin/invoice_done.html", {
        "request": request,
        "invoice_id": invoice_id
    })

@router.get("/invoices/pdf/{invoice_id}")
async def download_invoice(invoice_id: str):
    invoice = await prisma.invoice.find_unique(where={"id": invoice_id})
    pdf_path = invoice.get("pdfPath") if invoice else None

    if not pdf_path or not os.path.exists(pdf_path):
        return HTMLResponse("PDF not found", status_code=404)

    return FileResponse(pdf_path, media_type="application/pdf", filename=os.path.basename(pdf_path))
