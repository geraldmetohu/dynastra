try:
    from app.generated.prisma import Prisma
except ImportError:
    from prisma import Prisma

prisma = Prisma()
