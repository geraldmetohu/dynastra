# utils/auth.py
from fastapi import Request, HTTPException, status

ADMIN_EMAILS = ["info@dynastra.co.uk", "geraldmetohu@gmail.com", "metohu.gerald@gmail.com"]

def is_admin_email(email: str) -> bool:
    return email in ADMIN_EMAILS

def require_admin(request: Request):
    user = request.session.get("user")
    if not user or user.get("role") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
