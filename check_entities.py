import asyncio
from backend.database import get_db_connection

async def main():
    async with get_db_connection() as conn:
        async with conn.execute("SELECT COUNT(*) FROM entities") as cursor:
            row = await cursor.fetchone()
            print(f"Entities count: {row[0]}")
        async with conn.execute("SELECT name FROM entities") as cursor:
            rows = await cursor.fetchall()
            for r in rows:
                print(f"Entity: {r[0]}")

if __name__ == "__main__":
    asyncio.run(main())
