import asyncio
import json
from datetime import datetime
from backend.database import get_db_connection

async def main():
    async with get_db_connection() as conn:
        char = {
            "entity_id": "char-001-artemis",
            "type": "CHARACTER",
            "name": "Artemis Blackthorn",
            "base_attributes_json": json.dumps({
                "aliases": ["The Shadow", "Art"],
                "personality": "冷静、精于算计，但内心深处渴望被接纳。表面的冷漠是对过往伤痛的盾牌。",
                "core_motive": "找到失落的家族魔典，解开血脉诅咒。",
                "background": "出生于没落的术士家族。12岁时家族惨遭屠灭，独自在黑市成长为顶级情报贩子。"
            }),
            "current_status_json": json.dumps({
                "health": "85/100",
                "inventory": ["暗影匕首", "情报密函"],
                "relationships": {},
                "recent_memory_summary": ["在酒馆暗道中从线人处得到了魔典的线索"]
            }),
            "is_deleted": 0,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        await conn.execute("""
            INSERT INTO entities (entity_id, type, name, base_attributes_json, current_status_json, is_deleted, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (char["entity_id"], char["type"], char["name"], char["base_attributes_json"], char["current_status_json"], char["is_deleted"], char["created_at"], char["updated_at"]))
        await conn.commit()
        print("Mock character Artemis added.")

if __name__ == "__main__":
    asyncio.run(main())
