# app/internal/load_data.py

from app.internal.internal_db import INTERNAL_DB
from app.generated.prisma import Prisma

prisma = Prisma()

async def load_internal_data():
    try:
        print("🔄 Connecting to the database...")
        await prisma.connect()

        # Load all main data and populate internal cache
        INTERNAL_DB["users"] = await prisma.user.find_many()
        INTERNAL_DB["clients"] = await prisma.user.find_many(where={"role": "CLIENT"})
        INTERNAL_DB["invoices"] = await prisma.invoice.find_many(include={"services": True})
        INTERNAL_DB["messages"] = await prisma.message.find_many()
        INTERNAL_DB["repeat_rules"] = await prisma.repeatrule.find_many()

        print("✅ Internal DB loaded successfully.")

    except Exception as e:
        print(f"❌ Error loading data from Prisma: {e}")

    finally:
        await prisma.disconnect()
