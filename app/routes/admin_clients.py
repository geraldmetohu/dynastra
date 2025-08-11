from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.backend.utils.auth import require_admin
from app.generated.prisma import Prisma
from app.db import prisma  # ✅ import the shared instance

# Dependency to reuse prisma
def get_prisma() -> Prisma:
    return prisma  # ✅ now directly returns the shared prisma

router = APIRouter(
    prefix="/admin",
    tags=["Admin Clients"],
    dependencies=[Depends(require_admin)],
)

@router.get("/clients", response_class=HTMLResponse)
async def client_list(request: Request, prisma: Prisma = Depends(get_prisma)):
    clients = await prisma.user.find_many(
        where={"role": "CLIENT"},
        order={"createdAt": "desc"},
    )
    return request.app.templates.TemplateResponse(
        "admin/client_list.html",
        {"request": request, "clients": clients},
    )

@router.get("/client/new", response_class=HTMLResponse)
async def new_client_form(request: Request):
    return request.app.templates.TemplateResponse(
        "admin/new_client.html",
        {"request": request, "client": None, "form_action": "/admin/client/save", "error": None},
    )

@router.get("/client/edit/{client_id}", response_class=HTMLResponse)
async def edit_client_form(request: Request, client_id: str, prisma: Prisma = Depends(get_prisma)):
    client = await prisma.user.find_unique(where={"id": client_id})
    if client is None:
        return RedirectResponse("/admin/clients", status_code=303)

    return request.app.templates.TemplateResponse(
        "admin/new_client.html",
        {"request": request, "client": client, "form_action": "/admin/client/save", "error": None},
    )

@router.post("/client/save")
async def save_client(
    request: Request,
    prisma: Prisma = Depends(get_prisma),
    name: str = Form(...),
    surname: str = Form(...),
    phone: str = Form(...),
    email: str = Form(...),
    address: Optional[str] = Form(None),
    dob: Optional[str] = Form(None),
    place_of_birth: Optional[str] = Form(None),
    sex: Optional[str] = Form(None),
    client_type: Optional[str] = Form(None),
    status: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    tasks: Optional[List[str]] = Form(None),
    client_id: Optional[str] = Form(None),
):
    date_of_birth = None
    if dob:
        try:
            date_of_birth = datetime.strptime(dob, "%Y-%m-%d")
        except ValueError:
            return request.app.templates.TemplateResponse(
                "admin/new_client.html",
                {"request": request, "client": None, "form_action": "/admin/client/save",
                 "error": "Invalid date format. Use YYYY-MM-DD."},
                status_code=400,
            )

    data = {
        "name": name,
        "surname": surname,
        "phone": phone,
        "email": email,
        "address": address,
        "dateOfBirth": date_of_birth,
        "placeOfBirth": place_of_birth,
        "sex": sex,
        "clientType": client_type,
        "status": status,
        "description": description,
        "tasks": tasks or [],
        "role": "CLIENT",
    }

    try:
        if client_id:
            await prisma.user.update(where={"id": client_id}, data=data)
        else:
            await prisma.user.create(data=data)
    except Exception:
        return request.app.templates.TemplateResponse(
            "admin/new_client.html",
            {"request": request, "client": None, "form_action": "/admin/client/save",
             "error": "Could not save client. Ensure the email is unique and try again."},
            status_code=400,
        )

    return RedirectResponse("/admin/clients", status_code=303)

@router.get("/client/delete/{client_id}")
async def delete_client(client_id: str, prisma: Prisma = Depends(get_prisma)):
    try:
        await prisma.user.delete(where={"id": client_id})
    except Exception:
        pass
    return RedirectResponse("/admin/clients", status_code=303)
