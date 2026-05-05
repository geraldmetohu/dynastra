# main.py
from contextlib import asynccontextmanager
from datetime import datetime
import os
import asyncio
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse, HTMLResponse
from starlette.middleware.sessions import SessionMiddleware
from dotenv import load_dotenv

# Prisma client wrapper you already use
from app.db import prisma
from app.internal.load_data import load_internal_data

# Routers (your existing modular routes)
from app.routes import (
    home as home_routes,
    about,
    services,
    pricing,
    contact,
    admin_auth,
    admin_clients,
    admin_invoices,
    admin_marketing,

)

# Our background scheduler (recurring invoices & marketing)
from app.core import scheduler

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
APP_DIR = BASE_DIR / "app"
STATIC_DIR = APP_DIR / "static"
TEMPLATES_DIR = APP_DIR / "templates"


def _is_vercel() -> bool:
    return os.getenv("VERCEL") == "1"

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.db_available = False

    # --- Startup ---
    print("🔄 Connecting to the database...")
    try:
        await prisma.connect()
        app.state.db_available = True
        print("✅ DB connected.")
    except Exception as exc:
        app.state.db_available = False
        print(f"⚠️ Database startup skipped: {exc}")

    # Warm internal cache without blocking startup on long-running environments.
    if app.state.db_available and not _is_vercel():
        asyncio.create_task(load_internal_data())

        # APScheduler is not suitable for Vercel's serverless runtime.
        try:
            scheduler.start()
            print("⏰ Scheduler started.")
        except Exception as exc:
            print(f"⚠️ Scheduler startup skipped: {exc}")

    try:
        yield
    finally:
        # --- Shutdown ---
        if not _is_vercel():
            print("🛑 Stopping scheduler...")
            try:
                scheduler.scheduler.shutdown(wait=False)
            except Exception:
                pass

        if app.state.db_available:
            print("🔌 Disconnecting from the database...")
            try:
                await prisma.disconnect()
                print("✅ DB disconnected.")
            except Exception as exc:
                print(f"⚠️ Database shutdown skipped: {exc}")

app = FastAPI(title="Dynastra Tech", lifespan=lifespan)

# Sessions
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("FLASK_SECRET_KEY", "dev-key"),
)

# CORS (tighten in prod)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static & templates
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
templates.env.globals["current_year"] = datetime.now().year
# expose templates both ways (for old/new code paths)
app.templates = templates
app.state.templates = templates

# Middleware
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

# Legacy login redirect
@app.get("/login")
async def legacy_login_redirect():
    return RedirectResponse("/admin/login", status_code=303)

# Admin dashboard (kept simple — you already gate with session)
@app.get("/admin/dashboard", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    if not request.session.get("is_admin"):
        return RedirectResponse("/admin/login", status_code=303)
    return app.templates.TemplateResponse("admin/dashboard.html", {"request": request})

# Routers
app.include_router(admin_marketing.router)
app.include_router(admin_invoices.router)
app.include_router(admin_clients.router)
app.include_router(home_routes.router)
app.include_router(about.router)
app.include_router(services.router)
app.include_router(pricing.router)
app.include_router(contact.router)
app.include_router(admin_auth.router)
