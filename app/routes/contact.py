from fastapi import APIRouter, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
import resend
import os
from dotenv import load_dotenv

load_dotenv()
resend.api_key = os.getenv("RESEND_API_KEY")

templates = Jinja2Templates(directory="app/templates")
router = APIRouter()

@router.get("/contact", response_class=HTMLResponse)
def contact_get(request: Request):
    return templates.TemplateResponse("pages/contact.html", {"request": request, "submitted": False})

@router.post("/contact", response_class=HTMLResponse)
def contact_post(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    subject: str = Form("New Contact Form Submission"),
    message: str = Form(...)
):
    resend.Emails.send({
        "from": os.getenv("FROM_EMAIL"),
        "to": os.getenv("TO_EMAIL"),
        "subject": f"{subject} — from {name}",
        "html": f"""
            <h3>New Contact Message</h3>
            <p><strong>Name:</strong> {name}</p>
            <p><strong>Email:</strong> {email}</p>
            <p><strong>Subject:</strong> {subject}</p>
            <p><strong>Message:</strong><br>{message}</p>
        """
    })

    return templates.TemplateResponse("pages/contact.html", {
        "request": request,
        "submitted": True
    })
