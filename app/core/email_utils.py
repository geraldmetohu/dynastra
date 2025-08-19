# app/core/email_utils.py
import os, smtplib, ssl, mimetypes, base64
from email.message import EmailMessage
from typing import Iterable, Optional

SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")
FROM_EMAIL = os.getenv("FROM_EMAIL") or SMTP_USER

RESEND_API_KEY = os.getenv("RESEND_API_KEY")

def _send_via_smtp(to_email: str, subject: str, html: str, attachments: Optional[Iterable[str]] = None):
    if not (SMTP_HOST and SMTP_PORT and SMTP_USER and SMTP_PASS and FROM_EMAIL):
        raise RuntimeError("SMTP is not configured. Set SMTP_HOST/SMTP_PORT/SMTP_USER/SMTP_PASS/FROM_EMAIL.")

    msg = EmailMessage()
    msg["From"] = FROM_EMAIL
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content("Your email client does not support HTML.")
    msg.add_alternative(html, subtype="html")

    for p in attachments or []:
        if not p or not os.path.exists(p):
            continue
        ctype, encoding = mimetypes.guess_type(p)
        maintype, subtype = (ctype or "application/octet-stream").split("/", 1)
        with open(p, "rb") as f:
            msg.add_attachment(f.read(), maintype=maintype, subtype=subtype, filename=os.path.basename(p))

    context = ssl.create_default_context()
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as s:
        s.ehlo()
        s.starttls(context=context)
        s.login(SMTP_USER, SMTP_PASS)
        s.send_message(msg)

def _send_via_resend(to_email: str, subject: str, html: str, attachments: Optional[Iterable[str]] = None):
    if not RESEND_API_KEY:
        raise RuntimeError("RESEND_API_KEY not set")
    try:
        import httpx
    except ImportError:
        raise RuntimeError("httpx missing; pip install httpx")

    files_json = []
    for p in attachments or []:
        if p and os.path.exists(p):
            with open(p, "rb") as f:
                b64 = base64.b64encode(f.read()).decode("utf-8")
            files_json.append({
                "filename": os.path.basename(p),
                "content": b64,
            })

    payload = {
        "from": FROM_EMAIL,
        "to": [to_email],
        "subject": subject,
        "html": html,
    }
    if files_json:
        payload["attachments"] = files_json

    headers = {"Authorization": f"Bearer {RESEND_API_KEY}"}
    with httpx.Client(timeout=30) as client:
        r = client.post("https://api.resend.com/emails", json=payload, headers=headers)
        r.raise_for_status()
# app/core/email_utils.py
def send_email(to_email: str, subject: str, html: str, attachments: list[str] | None = None):
    provider = (os.getenv("EMAIL_PROVIDER") or "").lower()
    if not provider:
        provider = "smtp" if SMTP_HOST else ("resend" if RESEND_API_KEY else "")
    print(f"[mail] provider={provider} from={FROM_EMAIL} host={SMTP_HOST} resend_key={'set' if RESEND_API_KEY else 'missing'}")

    if provider == "smtp":
        return _send_via_smtp(to_email, subject, html, attachments)
    if provider == "resend":
        return _send_via_resend(to_email, subject, html, attachments)
    raise RuntimeError("No email provider configured")
