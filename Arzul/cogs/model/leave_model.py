# cogs/model/leave_model.py

class LeaveModel:
    def __init__(self, db_pool):
        self.db_pool = db_pool

    async def set_user_deleted(self, user_id: int):
        try:
            async with self.db_pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("SELECT COUNT(*) FROM user_data WHERE user_id = %s", (user_id,))
                    result = await cur.fetchone()
                    if result and result[0] > 0:
                        await cur.execute("UPDATE user_data SET status = %s WHERE user_id = %s", (1, user_id))
                        print(f"[DB] User {user_id} auf gelöscht gesetzt.")
        except Exception as e:
            print(f"[DB ERROR] {e}")
