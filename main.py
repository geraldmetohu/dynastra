# main.py
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse, HTMLResponse
from starlette.middleware.sessions import SessionMiddleware
from datetime import datetime
from dotenv import load_dotenv
import os

# ✅ Import the shared Prisma instance
from app.db import prisma  

load_dotenv()

app = FastAPI(title="Dynastra Tech")

# Sessions
app.add_middleware(SessionMiddleware, secret_key=os.getenv("FLASK_SECRET_KEY", "dev-key"))

# CORS (tighten in prod)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static & templates
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")
templates.env.globals["current_year"] = datetime.now().year

# Attach templates to app so all routes can use request.app.templates
app.templates = templates

# Middleware: add year on request
@app.middleware("http")
async def add_year_to_context(request: Request, call_next):
    request.state.year = datetime.now().year
    return await call_next(request)

# Health
@app.get("/api")
def root():
    return {"message": "Dynastra Tech API is running!"}

# Home
@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return app.templates.TemplateResponse("pages/home.html", {"request": request})

# Keep /login but redirect to admin login
@app.get("/login")
async def legacy_login_redirect():
    return RedirectResponse("/admin/login", status_code=303)

# Admin dashboard (guarded)
@app.get("/admin/dashboard", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    if not request.session.get("is_admin"):
        return RedirectResponse("/admin/login", status_code=303)
    return app.templates.TemplateResponse("admin/dashboard.html", {"request": request})

# Prisma connection events
@app.on_event("startup")
async def startup_event():
    print("🔄 Connecting to the database...")
    await prisma.connect()
    print("✅ Internal DB loaded successfully.")

@app.on_event("shutdown")
async def shutdown_event():
    await prisma.disconnect()

# Include routers
from app.routes import (
    home as home_routes,
    about,
    services,
    pricing,
    contact,
    admin_auth,
    admin_clients,  # ✅ already uses prisma from app/db.py
)
from app.routes import admin_invoices

app.include_router(admin_invoices.router)
app.include_router(admin_clients.router)
app.include_router(home_routes.router)
app.include_router(about.router)
app.include_router(services.router)
app.include_router(pricing.router)
app.include_router(contact.router)
app.include_router(admin_auth.router)

# Optional: small startup log
@app.on_event("startup")
async def on_startup():
    print("✅ App started. Ensure FIREBASE_API_KEY is set in your .env")
