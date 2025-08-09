# backend/utils/auth.py
from fastapi import Request, HTTPException, status

ADMIN_EMAILS = ["info@dynastra.co.uk", "geraldmetohu@gmail.com", "metohu.gerald@gmail.com"]

def is_admin(email: str) -> bool:
    return email in ADMIN_EMAILS

def require_admin(request: Request):
    user_email = request.session.get("user_email")
    if not user_email or not is_admin(user_email):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
