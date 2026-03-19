import asyncio
from backend.database import get_db_connection

async def main():
    async with get_db_connection() as conn:
        # 清空内容数据表
        await conn.execute("DELETE FROM entities")
        await conn.execute("DELETE FROM story_nodes")
        await conn.execute("DELETE FROM story_ir_blocks")
        # 提交更改
        await conn.commit()
        print("Successfully cleared all story data (entities, nodes, blocks).")
        print("Project settings (API Keys & Model) have been preserved.")

if __name__ == "__main__":
    asyncio.run(main())
