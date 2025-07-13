import aiomysql
from conn_db import db_pool  # Importiere den globalen Pool

class LeaveModel:
    def __init__(self, pool):
        self.pool = pool or db_pool  # Verwende den übergebenen Pool oder den globalen Pool
        if self.pool is None:
            print("[LeaveModel] Warnung: Kein Datenbankpool verfügbar.")

    async def set_user_deleted(self, user_id):
        """Setzt den Status eines Benutzers in der Datenbank auf 'deleted' (1)."""
        if self.pool is None:
            print("[LeaveModel] Fehler: Kein Datenbankpool verfügbar.")
            return False

        try:
            async with self.pool.acquire() as conn:
                async with conn.cursor() as cur:
                    # Prüfen, ob der Benutzer in der Datenbank existiert
                    await cur.execute('SELECT COUNT(*) FROM user_data WHERE user_id = %s', (user_id,))
                    result = await cur.fetchone()

                    if result and result[0] > 0:
                        await cur.execute('UPDATE user_data SET status = %s WHERE user_id = %s', (1, user_id))
                        await conn.commit()
                        print(f"[LeaveModel] Benutzer {user_id}: Status auf gelöscht (1) gesetzt.")
                        return True
                    else:
                        print(f"[LeaveModel] Benutzer {user_id} nicht in der DB gefunden.")
                        return False

        except Exception as e:
            print(f"[LeaveModel] Fehler beim Setzen des Status für {user_id}: {e}")
            return False