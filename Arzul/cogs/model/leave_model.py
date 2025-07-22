# cogs/model/leave_model.py

class LeaveModel:
    def __init__(self, db_pool):
        self.pool = db_pool

    async def set_user_deleted(self, user_id):
        if self.pool is None:
            print("[Model] Fehler: DB-Pool nicht initialisiert.")
            return False

        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute('SELECT COUNT(*) FROM user_data WHERE user_id = %s', (user_id,))
                result = await cur.fetchone()

                if result[0] > 0:
                    await cur.execute('UPDATE user_data SET status = %s WHERE user_id = %s', (1, user_id))
                    print(f"[Model] Benutzer {user_id} auf 'deleted' gesetzt.")
                    return True
                else:
                    print(f"[Model] Benutzer {user_id} nicht gefunden.")
                    return False
