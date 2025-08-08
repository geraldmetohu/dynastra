# app/internal/load_data.py

from app.generated.prisma import Prisma  # Import your Prisma client
from app.internal.internal_db import INTERNAL_DB

async def load_internal_data():
    try:
        print("🔄 Connecting to the database...")
        db = Prisma()
        await db.connect()

        # Load all main data and populate internal cache
        INTERNAL_DB["users"] = await db.user.find_many()
        INTERNAL_DB["clients"] = await db.user.find_many(where={"role": "CLIENT"})  # Optional filter
        INTERNAL_DB["invoices"] = await db.invoice.find_many(include={"services": True})
        INTERNAL_DB["messages"] = await db.message.find_many()
        INTERNAL_DB["repeat_rules"] = await db.repeatrule.find_many()

        await db.disconnect()
        print("✅ Internal DB loaded successfully.")

    except Exception as e:
        print(f"❌ Error loading data from Prisma: {e}")
