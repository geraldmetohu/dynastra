# app/internal/load_data.py

from prisma import Prisma
from app.internal.internal_db import INTERNAL_DB

async def load_internal_data():
    db = Prisma()
    await db.connect()

    INTERNAL_DB["users"] = await db.user.find_many()
    INTERNAL_DB["clients"] = await db.client.find_many()
    INTERNAL_DB["invoices"] = await db.invoice.find_many()
    INTERNAL_DB["messages"] = await db.message.find_many()
    INTERNAL_DB["repeat_rules"] = await db.repeatrule.find_many()

    await db.disconnect()
