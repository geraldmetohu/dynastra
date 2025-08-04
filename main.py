from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from datetime import datetime
from dotenv import load_dotenv
import os
from app.routes import home, about, services, pricing, contact
from fastapi import FastAPI, Request, Form, Depends
from fastapi.responses import RedirectResponse, HTMLResponse
from starlette.middleware.sessions import SessionMiddleware
# Load environment variables
load_dotenv()

# Create app
app = FastAPI()

# Mount static files and set up templates
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")
templates.env.globals["current_year"] = datetime.now().year

# Middleware to add current year to request state
@app.middleware("http")
async def add_year_to_context(request: Request, call_next):
    request.state.year = datetime.now().year
    response = await call_next(request)
    return response

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Test root route
@app.get("/api")
def root():
    return {"message": "Dynastra Tech API is running!"}

from fastapi.responses import HTMLResponse

@app.get("/", response_class=HTMLResponse)
def test_home(request: Request):
    return templates.TemplateResponse("pages/home.html", {"request": request})


app.include_router(home.router)
app.include_router(about.router)
app.include_router(services.router)
app.include_router(pricing.router)
app.include_router(contact.router)

from fastapi.responses import HTMLResponse

@app.get("/", response_class=HTMLResponse)
def fallback_home(request: Request):
    return templates.TemplateResponse("pages/home.html", {"request": request})




ADMIN_EMAILS = ["gerald@metohu.com", "metohu.gerald@gmail.com", "info@dynastra.co.uk"]

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key=os.getenv("FLASK_SECRET_KEY", "dev-key"))

# Login form route (GET)
@app.get("/login", response_class=HTMLResponse)
async def login_form(request: Request):
    return templates.TemplateResponse("pages/login.html", {"request": request})

# Login form handler (POST)
@app.post("/login")
async def login_submit(request: Request, email: str = Form(...)):
    request.session["user_email"] = email
    if email in ADMIN_EMAILS:
        return RedirectResponse("/admin/dashboard", status_code=303)
    return RedirectResponse("/user-dashboard", status_code=303)

@app.get("/admin/dashboard", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    if request.session.get("user_email") not in ADMIN_EMAILS:
        return RedirectResponse("/", status_code=303)
    return templates.TemplateResponse("admin/dashboard.html", {"request": request})

@app.get("/user-dashboard", response_class=HTMLResponse)
async def user_dashboard(request: Request):
    return templates.TemplateResponse("user/dashboard.html", {"request": request})
