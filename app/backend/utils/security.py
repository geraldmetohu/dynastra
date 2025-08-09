# app/utils/security.py

from fastapi import Request

ADMIN_EMAILS = ["geraldmetohu@gmail.com", "metohu.gerald@gmail.com", "info@dynastra.co.uk"]

def is_authorized(request: Request):
    user_email = request.session.get("user_email")
    return user_email in ADMIN_EMAILS
