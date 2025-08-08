# app/backend/crud_invoice.py

from fastapi import APIRouter, Request, Form, UploadFile, File
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import List
from app.backend.auth_utilis import require_admin
from prisma import Prisma
import uuid

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")
db = Prisma()


@router.get("/admin/invoice/create")
async def show_invoice_form(request: Request):
    require_admin(request)
    await db.connect()
    clients = await db.client.find_many()
    await db.disconnect()
    return templates.TemplateResponse("admin/invoice_creator.html", {
        "request": request,
        "clients": clients
    })


@router.post("/admin/invoice/create")
async def create_invoice(
    request: Request,
    client: str = Form(...),
    invoiceType: str = Form(...),
    invoiceDate: str = Form(...),
    dueDate: str = Form(...),
    service_description: List[str] = Form(...),
    service_price: List[float] = Form(...),
    total: float = Form(...),
    accountName: str = Form(...),
    sortCode: str = Form(...),
    accountNumber: str = Form(...),
    iban: str = Form(...),
    companyLogo: UploadFile = File(None),
):
    require_admin(request)

    invoice_id = str(uuid.uuid4())

    await db.connect()

    # Store invoice in DB (basic table needed for invoices)
    await db.invoice.create({
        "id": invoice_id,
        "clientId": client,
        "type": invoiceType,
        "invoiceDate": invoiceDate,
        "dueDate": dueDate,
        "total": total,
        "bankAccountName": accountName,
        "sortCode": sortCode,
        "accountNumber": accountNumber,
        "iban": iban,
        "services": ", ".join([
            f"{desc} - £{price:.2f}" for desc, price in zip(service_description, service_price)
        ]),
        "logoFilename": companyLogo.filename if companyLogo else None,
    })

    # Optionally: save logo
    if companyLogo:
        with open(f"app/static/invoices/logos/{invoice_id}_{companyLogo.filename}", "wb") as f:
            f.write(await companyLogo.read())

    await db.disconnect()

    return RedirectResponse(url="/admin/client_list", status_code=303)

@router.get("/admin/client/{client_id}/invoices")
async def list_invoices_for_client(request: Request, client_id: str):
    require_admin(request)

    await db.connect()
    invoices = await db.invoice.find_many(where={"clientId": client_id})
    client = await db.client.find_unique(where={"id": client_id})
    await db.disconnect()

    return templates.TemplateResponse("admin/invoice_list.html", {
        "request": request,
        "invoices": invoices,
        "client": client
    })
from fastapi import APIRouter, Form, Request, UploadFile
from fastapi.responses import RedirectResponse
from app.generated.prisma import Prisma
from app.backend.auth_utils import require_admin
from uuid import uuid4
from typing import List
import shutil
import os

router = APIRouter()
db = Prisma()

@router.post("/admin/invoice/create")
async def create_invoice(
    request: Request,
    client: str = Form(...),
    invoiceType: str = Form(...),
    invoiceDate: str = Form(...),
    dueDate: str = Form(...),
    service_description: List[str] = Form(...),
    service_price: List[float] = Form(...),
    accountName: str = Form(...),
    sortCode: str = Form(...),
    accountNumber: str = Form(...),
    iban: str = Form(""),
    companyLogo: UploadFile = None,
):
    require_admin(request)

    logo_path = None
    if companyLogo:
        file_ext = os.path.splitext(companyLogo.filename)[1]
        file_name = f"{uuid4()}{file_ext}"
        save_path = f"app/static/uploads/{file_name}"
        with open(save_path, "wb") as buffer:
            shutil.copyfileobj(companyLogo.file, buffer)
        logo_path = save_path

    total = sum(service_price)
    
    invoice = await db.invoice.create(
        data={
            "clientId": client,
            "invoiceType": invoiceType,
            "invoiceDate": invoiceDate,
            "dueDate": dueDate,
            "total": total,
            "accountName": accountName,
            "sortCode": sortCode,
            "accountNumber": accountNumber,
            "iban": iban,
            "logoPath": logo_path,
        }
    )

    for desc, price in zip(service_description, service_price):
        await db.service.create(
            data={
                "invoiceId": invoice.id,
                "description": desc,
                "price": price,
            }
        )

    return RedirectResponse("/admin/invoice/list", status_code=303)
from fastapi.templating import Jinja2Templates
from fastapi import Depends
from datetime import datetime

templates = Jinja2Templates(directory="app/templates")

@router.get("/admin/invoice/list")
async def invoice_list(request: Request):
    require_admin(request)

    invoices = await db.invoice.find_many(
        include={
            "client": True,
            "services": True,
            "recurring": True,
        },
        order={"createdAt": "desc"}
    )

    return templates.TemplateResponse("admin/invoice_list.html", {
        "request": request,
        "invoices": invoices,
    })

@router.get("/admin/invoice/view/{invoice_id}")
async def view_invoice(invoice_id: str, request: Request):
    require_admin(request)

    invoice = await db.invoice.find_unique(
        where={"id": invoice_id},
        include={
            "client": True,
            "services": True,
            "recurring": True,
        }
    )

    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    return templates.TemplateResponse("admin/invoice_view.html", {
        "request": request,
        "invoice": invoice
    })

from app.utils.pdf_utils import generate_invoice_pdf
from app.utils.email_utils import send_invoice_email

@router.get("/admin/invoice/send/{invoice_id}")
async def send_invoice(invoice_id: str, request: Request):
    require_admin(request)

    invoice = await db.invoice.find_unique(
        where={"id": invoice_id},
        include={"client": True, "services": True}
    )

    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    # Generate PDF
    pdf_filename = generate_invoice_pdf(invoice)

    # Email it
    send_invoice_email(
        to_email=invoice["client"]["email"],
        subject="Your Invoice from Dynastra",
        body="Please find your invoice attached.",
        pdf_filename=pdf_filename
    )

    # Mark invoice as sent
    await db.invoice.update(
        where={"id": invoice_id},
        data={"sent": True, "pdfPath": pdf_filename}
    )

    return RedirectResponse(url="/admin/invoice/view/" + invoice_id, status_code=303)
