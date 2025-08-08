from fastapi import APIRouter, Request, Form, Depends, HTTPException
from fastapi.responses import RedirectResponse
from prisma import Prisma
from app.backend.auth_utilis import verify_authorization  # import your global check

router = APIRouter()
db = Prisma()

# In-memory internal store
INTERNAL_CLIENTS = {}

# ✅ Initialize Prisma DB
async def init_db():
    await db.connect()

# ✅ CREATE CLIENT
@router.post("/admin/client/create")
async def create_client(
    request: Request,
    name: str = Form(...),
    surname: str = Form(...),
    phone: str = Form(...),
    email: str = Form(...),
    address: str = Form(""),
    dob: str = Form(""),
    place_of_birth: str = Form(""),
    sex: str = Form(""),
    client_type: str = Form(""),
    tasks: list[str] = Form([]),
    status: str = Form("Negotiating"),
    description: str = Form("")
):
    # Check authorization
    if not await verify_authorization(request):
        raise HTTPException(status_code=403, detail="Unauthorized")

    client_data = {
        "name": name,
        "surname": surname,
        "phone": phone,
        "email": email,
        "address": address,
        "dob": dob,
        "place_of_birth": place_of_birth,
        "sex": sex,
        "client_type": client_type,
        "tasks": tasks,
        "status": status,
        "description": description,
    }

    INTERNAL_CLIENTS[email] = client_data

    await db.client.create(data={**client_data, "tasks": ",".join(tasks)})

    return RedirectResponse(url="/admin/client_list", status_code=303)


# ✅ UPDATE CLIENT
@router.post("/admin/client/{client_id}/edit")
async def update_client(client_id: str, request: Request):
    if not await verify_authorization(request):
        raise HTTPException(status_code=403, detail="Unauthorized")

    form = await request.form()
    data = dict(form)

    # Update internal store
    INTERNAL_CLIENTS[client_id] = data

    await db.client.update(
        where={"id": client_id},
        data={**data, "tasks": ",".join(form.getlist("tasks"))}
    )

    return RedirectResponse(url="/admin/client_list", status_code=303)


# ✅ DELETE CLIENT
@router.post("/admin/client/{client_id}/delete")
async def delete_client(client_id: str, request: Request):
    if not await verify_authorization(request):
        raise HTTPException(status_code=403, detail="Unauthorized")

    INTERNAL_CLIENTS.pop(client_id, None)

    await db.client.delete(where={"id": client_id})

    return RedirectResponse(url="/admin/client_list", status_code=303)

# File: crud_clients.py
@app.get("/admin/client/summary/{client_id}")
async def download_summary(request: Request, client_id: str):
    require_admin(request)
    client = await db.client.find_unique(where={"id": client_id})
    # Generate PDF logic here and return file
    return FileResponse("generated_summary.pdf", media_type="application/pdf", filename="client_summary.pdf")


# File: crud_clients.py
@app.post("/admin/client/note/{client_id}")
async def add_note(request: Request, client_id: str):
    require_admin(request)
    form = await request.form()
    note = form.get("note")
    await db.client.update(where={"id": client_id}, data={"note": note})  # Requires note field in model
    return RedirectResponse("/admin/client_list", status_code=303)
