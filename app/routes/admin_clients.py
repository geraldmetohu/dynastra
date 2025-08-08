from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from app.generated.prisma import prisma
from app.templates import templates
from datetime import datetime

router = APIRouter()


@router.get("/admin/clients", response_class=HTMLResponse)
async def client_list(request: Request):
    clients = await prisma.user.find_many(
        where={"role": "CLIENT"},
        order={"createdAt": "desc"},
    )
    return templates.TemplateResponse("admin/client_list.html", {"request": request, "clients": clients})


@router.get("/admin/client/new", response_class=HTMLResponse)
async def new_client_form(request: Request):
    return templates.TemplateResponse("admin/new_client.html", {
        "request": request,
        "client": None,
        "form_action": "/admin/client/save"
    })


@router.get("/admin/client/edit/{client_id}", response_class=HTMLResponse)
async def edit_client_form(request: Request, client_id: str):
    client = await prisma.user.find_unique(where={"id": client_id})
    return templates.TemplateResponse("admin/new_client.html", {
        "request": request,
        "client": client,
        "form_action": "/admin/client/save"
    })


@router.post("/admin/client/save")
async def save_client(
    request: Request,
    name: str = Form(...),
    surname: str = Form(...),
    phone: str = Form(...),
    email: str = Form(...),
    address: str = Form(None),
    dob: str = Form(None),
    place_of_birth: str = Form(None),
    sex: str = Form(None),
    client_type: str = Form(None),
    status: str = Form(None),
    description: str = Form(None),
    tasks: list[str] = Form([]),
    client_id: str = Form(None)
):
    data = {
        "name": name,
        "surname": surname,
        "phone": phone,
        "email": email,
        "address": address,
        "dateOfBirth": datetime.strptime(dob, "%Y-%m-%d") if dob else None,
        "placeOfBirth": place_of_birth,
        "sex": sex,
        "clientType": client_type,
        "status": status,
        "description": description,
        "tasks": tasks,
        "role": "CLIENT",
    }

    if client_id:
        await prisma.user.update(where={"id": client_id}, data=data)
    else:
        await prisma.user.create(data=data)

    return RedirectResponse("/admin/clients", status_code=303)


@router.get("/admin/client/delete/{client_id}")
async def delete_client(client_id: str):
    await prisma.user.delete(where={"id": client_id})
    return RedirectResponse("/admin/clients", status_code=303)
