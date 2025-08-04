from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="app/templates")

router = APIRouter()

@router.get("/services")
def services(request: Request):
    return templates.TemplateResponse("pages/services.html", {"request": request})
