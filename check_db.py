import asyncio
import aiosqlite
import json

async def main():
    async with aiosqlite.connect("grimoire.sqlite") as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM settings") as cursor:
            row = await cursor.fetchone()
            if row:
                print(f"ID: {row['id']}")
                print(f"Model: {row['llm_model']}")
                print(f"Keys: {row['llm_api_keys_json']}")
                print(f"Base: {row['llm_api_base']}")
            else:
                print("No settings found in DB")

if __name__ == "__main__":
    asyncio.run(main())
