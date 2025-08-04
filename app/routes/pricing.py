from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="app/templates")

router = APIRouter()

@router.get("/pricing")
def pricing(request: Request):
    return templates.TemplateResponse("pages/pricing.html", {"request": request})
