# File: crud_marketing.py
@app.get("/admin/marketing/send/{client_id}")
async def send_marketing(request: Request, client_id: str):
    require_admin(request)
    # You would call an email/sms function here
    client = await db.client.find_unique(where={"id": client_id})
    # Call send_marketing_email(client.email) or similar
    return RedirectResponse("/admin/client_list", status_code=303)
