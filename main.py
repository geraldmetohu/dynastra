# main.py

from fastapi import FastAPI, Request, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse, HTMLResponse
from starlette.middleware.sessions import SessionMiddleware
from datetime import datetime
from dotenv import load_dotenv
import os

# Route imports
from app.routes import home, about, services, pricing, contact, admin_clients
from app.backend.routes import client, invoice

# Load environment variables
load_dotenv()

# Create FastAPI app
app = FastAPI()

# Add session middleware
app.add_middleware(SessionMiddleware, secret_key=os.getenv("FLASK_SECRET_KEY", "dev-key"))

# Enable CORS (can restrict origin in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files and Jinja templates
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")
templates.env.globals["current_year"] = datetime.now().year

# Admin emails
ADMIN_EMAILS = ["gerald@metohu.com", "metohu.gerald@gmail.com", "info@dynastra.co.uk"]

# Middleware: add year to context
@app.middleware("http")
async def add_year_to_context(request: Request, call_next):
    request.state.year = datetime.now().year
    return await call_next(request)

# API root health check
@app.get("/api")
def root():
    return {"message": "Dynastra Tech API is running!"}

# Home fallback
@app.get("/", response_class=HTMLResponse)
def fallback_home(request: Request):
    return templates.TemplateResponse("pages/home.html", {"request": request})

# Login page
@app.get("/login", response_class=HTMLResponse)
async def login_form(request: Request):
    return templates.TemplateResponse("pages/login.html", {"request": request})

# Load data function
from app.internal.load_data import load_internal_data

# Login submission
@app.post("/login")
async def login_submit(request: Request, email: str = Form(...)):
    request.session["user_email"] = email
    if email in ADMIN_EMAILS:
        await load_internal_data()
        return RedirectResponse("/admin/dashboard", status_code=303)
    return RedirectResponse("/user-dashboard", status_code=303)

# Logout route
@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/", status_code=303)

# Admin dashboard
@app.get("/admin/dashboard", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    if request.session.get("user_email") not in ADMIN_EMAILS:
        return RedirectResponse("/", status_code=303)
    return templates.TemplateResponse("admin/dashboard.html", {"request": request})

# User dashboard (non-admin users)
@app.get("/user-dashboard", response_class=HTMLResponse)
async def user_dashboard(request: Request):
    return templates.TemplateResponse("user/dashboard.html", {"request": request})

# Optional: preload internal data on app startup
@app.on_event("startup")
async def startup():
    try:
        print("🚀 Server started.")
        await load_internal_data()
    except Exception as e:
        print(f"❌ Error during startup: {e}")

# Include all route modules
app.include_router(home.router)
app.include_router(about.router)
app.include_router(services.router)
app.include_router(pricing.router)
app.include_router(contact.router)

app.include_router(admin_clients.router)
app.include_router(client.router)
app.include_router(invoice.router)
