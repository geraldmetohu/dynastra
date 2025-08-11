# app/internal/load_data.py
from app.internal.internal_db import INTERNAL_DB
from app.db import prisma

async def load_internal_data():
    # Assumes prisma is already connected by main.py lifespan
    try:
        INTERNAL_DB["users"] = await prisma.user.find_many()
        INTERNAL_DB["clients"] = await prisma.user.find_many(where={"role": "CLIENT"})
        INTERNAL_DB["invoices"] = await prisma.invoice.find_many(include={"services": True})
        INTERNAL_DB["messages"] = await prisma.message.find_many()
        INTERNAL_DB["repeat_rules"] = await prisma.repeatrule.find_many()
        print("✅ Internal DB loaded successfully.")
    except Exception as e:
        print(f"❌ Error loading data from Prisma: {e}")
