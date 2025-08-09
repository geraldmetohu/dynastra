import os
import httpx
from fastapi import APIRouter, Request, Form, status
from fastapi.responses import RedirectResponse
from app.internal.load_data import load_internal_data

router = APIRouter()
FIREBASE_API_KEY = os.getenv("FIREBASE_API_KEY")

ADMIN_EMAILS = {
    "geraldmetohu@gmail.com",
    "metohu.gerald@gmail.com",
    "info@dynastra.co.uk",
}

@router.get("/admin/login")
async def login_form(request: Request):
    return request.app.templates.TemplateResponse(
        "pages/admin_login.html", {"request": request, "error": None}
    )

@router.post("/admin/login")
async def login_submit(request: Request, email: str = Form(...), password: str = Form(...)):
    email = (email or "").strip().lower()

    if not FIREBASE_API_KEY:
        # show clear error so you know to set it
        return request.app.templates.TemplateResponse(
            "pages/admin_login.html",
            {"request": request, "error": "Server misconfigured: FIREBASE_API_KEY missing."},
        )

    # 1) Firebase email+password auth
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_API_KEY}",
                json={"email": email, "password": password, "returnSecureToken": True},
            )
            data = resp.json()
        if resp.status_code != 200 or "idToken" not in data:
            # Bubble up Firebase error message if available
            err = data.get("error", {}).get("message", "Invalid email or password.")
            print(f"[LOGIN] Firebase error: {err}")
            return request.app.templates.TemplateResponse(
                "pages/admin_login.html",
                {"request": request, "error": "Invalid email or password."},
            )
    except Exception as e:
        print(f"[LOGIN] Firebase request failed: {e}")
        return request.app.templates.TemplateResponse(
            "pages/admin_login.html",
            {"request": request, "error": "Login failed. Please try again."},
        )

    # 2) Admin allowlist
    if email not in ADMIN_EMAILS:
        print(f"[LOGIN] Non-admin attempted login: {email}")
        return request.app.templates.TemplateResponse(
            "pages/admin_login.html",
            {"request": request, "error": "You are not authorized to access this area."},
        )

    # 3) Set session + load internal data (non-fatal)
    request.session["is_admin"] = True
    request.session["user_email"] = email

    try:
        await load_internal_data()
    except Exception as e:
        print(f"[LOGIN] load_internal_data() failed: {e}")

    # 4) Redirect to dashboard
    return RedirectResponse("/admin/dashboard", status_code=status.HTTP_303_SEE_OTHER)

@router.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)

# in app/routes/admin_auth.py (or main.py)


@router.get("/__debug/firebase-key")
def debug_key():
    key = os.getenv("FIREBASE_API_KEY", "")
    return {"loaded": bool(key), "length": len(key), "preview": (key[:6] + "..." if key else "")}
