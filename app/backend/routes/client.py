from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from app.generated.prisma import prisma
from starlette.status import HTTP_302_FOUND
from typing import List

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/admin/clients")
async def list_clients(request: Request):
    clients = await prisma.client.find_many(order={"createdAt": "desc"})
    return templates.TemplateResponse("admin/client_list.html", {"request": request, "clients": clients})

@router.get("/admin/client/edit/{id}")
async def edit_client_form(id: str, request: Request):
    client = await prisma.client.find_unique(where={"id": id})
    return templates.TemplateResponse("admin/new_client.html", {"request": request, "client": client, "form_action": f"/admin/client/edit/{id}"})

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
    await prisma.client.update(
        where={"id": id},
        data={
            "name": name,
            "surname": surname,
            "phone": phone,
            "email": email,
            "address": address,
            "dateOfBirth": dob or None,
            "placeOfBirth": place_of_birth,
            "sex": sex,
            "clientType": client_type,
            "tasks": tasks,
            "status": status,
            "description": description
        }
    )
    return RedirectResponse(url="/admin/clients", status_code=HTTP_302_FOUND)

@router.get("/admin/client/delete/{id}")
async def delete_client(id: str):
    await prisma.client.delete(where={"id": id})
    return RedirectResponse(url="/admin/clients", status_code=HTTP_302_FOUND)

@router.get("/admin/new_client.html")
async def new_client_form(request: Request):
    return templates.TemplateResponse("admin/new_client.html", {"request": request, "client": None, "form_action": "/admin/new_client"})

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
    await prisma.client.create(
        data={
            "name": name,
            "surname": surname,
            "phone": phone,
            "email": email,
            "address": address,
            "dateOfBirth": dob or None,
            "placeOfBirth": place_of_birth,
            "sex": sex,
            "clientType": client_type,
            "tasks": tasks,
            "status": status,
            "description": description
        }
    )
    return RedirectResponse(url="/admin/clients", status_code=HTTP_302_FOUND)
