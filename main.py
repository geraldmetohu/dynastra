from fastapi import FastAPI, Request, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse, HTMLResponse
from starlette.middleware.sessions import SessionMiddleware
from datetime import datetime
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Create app
app = FastAPI()

# Add session middleware
app.add_middleware(SessionMiddleware, secret_key=os.getenv("FLASK_SECRET_KEY", "dev-key"))

# Mount static files and setup templates
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")
templates.env.globals["current_year"] = datetime.now().year

# Middleware to add current year
@app.middleware("http")
async def add_year_to_context(request: Request, call_next):
    request.state.year = datetime.now().year
    return await call_next(request)

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API root
@app.get("/api")
def root():
    return {"message": "Dynastra Tech API is running!"}

# Default homepage
@app.get("/", response_class=HTMLResponse)
def fallback_home(request: Request):
    return templates.TemplateResponse("pages/home.html", {"request": request})

# Admin emails
ADMIN_EMAILS = ["gerald@metohu.com", "metohu.gerald@gmail.com", "info@dynastra.co.uk"]

# Login form
@app.get("/login", response_class=HTMLResponse)
async def login_form(request: Request):
    return templates.TemplateResponse("pages/login.html", {"request": request})

# Login submit
@app.post("/login")
async def login_submit(request: Request, email: str = Form(...)):
    request.session["user_email"] = email
    if email in ADMIN_EMAILS:
        return RedirectResponse("/admin/dashboard", status_code=303)
    return RedirectResponse("/user-dashboard", status_code=303)

# Admin dashboard
@app.get("/admin/dashboard", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    if request.session.get("user_email") not in ADMIN_EMAILS:
        return RedirectResponse("/", status_code=303)
    return templates.TemplateResponse("admin/dashboard.html", {"request": request})

# User dashboard
@app.get("/user-dashboard", response_class=HTMLResponse)
async def user_dashboard(request: Request):
    return templates.TemplateResponse("user/dashboard.html", {"request": request})

# Include other routes
from app.routes import home, about, services, pricing, contact
app.include_router(home.router)
app.include_router(about.router)
app.include_router(services.router)
app.include_router(pricing.router)
app.include_router(contact.router)
