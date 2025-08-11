# app/backend/routes/client.py
from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.status import HTTP_302_FOUND
from typing import List, Optional
from datetime import datetime

from app.db import prisma  # ✅ shared instance

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/admin/clients")
async def list_clients(request: Request):
    # model is User -> prisma.user
    clients = await prisma.user.find_many(order={"createdAt": "desc"})
    return templates.TemplateResponse("admin/client_list.html", {"request": request, "clients": clients})

@router.get("/admin/client/edit/{id}")
async def edit_client_form(id: str, request: Request):
    client = await prisma.user.find_unique(where={"id": id})
    return templates.TemplateResponse(
        "admin/new_client.html",
        {"request": request, "client": client, "form_action": f"/admin/client/edit/{id}"}
    )

@router.post("/admin/client/edit/{id}")
async def update_client(
    id: str,
    name: str = Form(...),
    surname: str = Form(...),
    phone: str = Form(...),
    email: str = Form(...),
    address: str = Form(""),
    dob: str = Form(""),
    place_of_birth: str = Form(""),
    sex: str = Form(""),
    client_type: str = Form(...),
    tasks: List[str] = Form([]),
    status: str = Form(...),
    description: str = Form("")
):
    dob_dt: Optional[datetime] = None
    if dob.strip():
        # accept YYYY-MM-DD or full ISO
        try:
            dob_dt = datetime.fromisoformat(dob)
        except ValueError:
            dob_dt = datetime.strptime(dob, "%Y-%m-%d")

    await prisma.user.update(
        where={"id": id},
        data={
            "name": name,
            "surname": surname,
            "phone": phone,
            "email": email,
            "address": address or None,
            "dateOfBirth": dob_dt,  # None or datetime
            "placeOfBirth": place_of_birth or None,
            "sex": sex or None,
            "clientType": client_type,
            "tasks": tasks,  # String[]
            "status": status,
            "description": description or None,
        },
    )
    return RedirectResponse(url="/admin/clients", status_code=HTTP_302_FOUND)

@router.get("/admin/client/delete/{id}")
async def delete_client(id: str):
    await prisma.user.delete(where={"id": id})
    return RedirectResponse(url="/admin/clients", status_code=HTTP_302_FOUND)

@router.get("/admin/new_client.html")
async def new_client_form(request: Request):
    return templates.TemplateResponse(
        "admin/new_client.html",
        {"request": request, "client": None, "form_action": "/admin/new_client"}
    )

@router.post("/admin/new_client")
async def create_client(
    name: str = Form(...),
    surname: str = Form(...),
    phone: str = Form(...),
    email: str = Form(...),
    address: str = Form(""),
    dob: str = Form(""),
    place_of_birth: str = Form(""),
    sex: str = Form(""),
    client_type: str = Form(...),
    tasks: List[str] = Form([]),
    status: str = Form(...),
    description: str = Form("")
):
    dob_dt: Optional[datetime] = None
    if dob.strip():
        try:
            dob_dt = datetime.fromisoformat(dob)
        except ValueError:
            dob_dt = datetime.strptime(dob, "%Y-%m-%d")

    await prisma.user.create(
        data={
            "name": name,
            "surname": surname,
            "phone": phone,
            "email": email,
            "address": address or None,
            "dateOfBirth": dob_dt,
            "placeOfBirth": place_of_birth or None,
            "sex": sex or None,
            "clientType": client_type,
            "tasks": tasks,
            "status": status,
            "description": description or None,
        }
    )
    return RedirectResponse(url="/admin/clients", status_code=HTTP_302_FOUND)
