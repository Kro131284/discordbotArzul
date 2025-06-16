# cogs/model/level_model.py
import aiomysql

class UserData:
    def __init__(self, pool):
        self.pool = pool
        self.table_created = False  # Flag, um zu überprüfen, ob die Tabelle bereits erstellt wurde

    async def create_table(self):
        """Erstellt die Tabelle 'user_data' in der Datenbank, falls sie nicht existiert."""
        if self.table_created:
            print("Table 'user_data' already exists. Skipping creation.")
            return

        try:
            async with self.pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    # Check if the table exists
                    await cursor.execute("SHOW TABLES LIKE 'user_data'")
                    result = await cursor.fetchone()
                    if not result:
                        # Table doesn't exist, create it
                        print("Table 'user_data' does not exist. Creating...")
                        await cursor.execute("""
                            CREATE TABLE IF NOT EXISTS user_data (
                                user_id BIGINT PRIMARY KEY,
                                xp INT DEFAULT 0,
                                level INT DEFAULT 1,
                                status INT DEFAULT 0,
                                discord_name VARCHAR(255),
                                server_name VARCHAR(255)
                            )
                        """)
                        await conn.commit()
                        print("Table 'user_data' created successfully.")
                    else:
                        print("Table 'user_data' already exists. Skipping creation.")
                    self.table_created = True  # Setze das Flag auf True
        except aiomysql.Error as e:
            print(f"Datenbankfehler beim Erstellen der Tabelle: {e}")

    async def get_or_create_user(self, user_id, discord_name=None, server_name=None):
        """Ruft die XP und das Level eines Benutzers ab oder erstellt einen neuen Eintrag, falls der Benutzer nicht existiert."""
        try:
            async with self.pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute("SELECT xp, level, discord_name, server_name FROM user_data WHERE user_id = %s", (user_id,))
                    result = await cursor.fetchone()
                    if result:
                        xp, level, db_discord_name, db_server_name = result
                        # Update discord_name and server_name if provided and different
                        if discord_name and discord_name != db_discord_name:
                            await cursor.execute("UPDATE user_data SET discord_name = %s WHERE user_id = %s", (discord_name, user_id))
                            print(f"Updated discord_name for user {user_id} to {discord_name}")
                        # Update the server_name with the user's nickname on the server
                        if server_name and server_name != db_server_name:
                            await cursor.execute("UPDATE user_data SET server_name = %s WHERE user_id = %s", (server_name, user_id))
                            print(f"Updated server_name for user {user_id} to {server_name}")
                        await conn.commit()
                        return xp, level
                    else:
                        # Ensure discord_name and server_name are not None before inserting
                        await cursor.execute("INSERT INTO user_data (user_id, discord_name, server_name) VALUES (%s, %s, %s)", (user_id, discord_name, server_name))
                        await conn.commit()
                        print(f"New user {user_id} created with 0 XP and level 1")
                        return 0, 1
        except aiomysql.Error as e:
            print(f"Datenbankfehler beim Abrufen oder Erstellen des Benutzers: {e}")
            return 0, 1

    async def update_user_xp(self, user_id, new_xp):
        """Aktualisiert die XP eines Benutzers."""
        try:
            async with self.pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute("UPDATE user_data SET xp = %s WHERE user_id = %s", (new_xp, user_id))
                    await conn.commit()
        except aiomysql.Error as e:
            print(f"Datenbankfehler beim Aktualisieren der Benutzer-XP: {e}")

    async def update_user_level(self, user_id, new_xp, new_level):
        """Aktualisiert das Level und die XP eines Benutzers."""
        try:
            async with self.pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute("UPDATE user_data SET xp = %s, level = %s WHERE user_id = %s", (new_xp, new_level, user_id))
                    await conn.commit()
        except aiomysql.Error as e:
            print(f"Datenbankfehler beim Aktualisieren des Benutzerlevels: {e}")

    async def get_user_name_and_avatar(self, user_id):
        """Ruft den Discord-Namen und die Avatar-URL eines Benutzers aus der Datenbank ab."""
        try:
            async with self.pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute("SELECT discord_name FROM user_data WHERE user_id = %s", (user_id,))
                    result = await cursor.fetchone()
                    if result:
                        discord_name = result[0]
                        return discord_name, None #keine Avatar URL in der Datenbank
                    else:
                        return None, None
        except aiomysql.Error as e:
            print(f"Datenbankfehler beim Abrufen des Benutzernamens: {e}")
            return None, None
    
    async def get_top_users(self, limit=10):
        """Ruft die Top-Benutzer basierend auf Level und XP ab."""
        try:
            async with self.pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute("SELECT user_id, xp, level FROM user_data WHERE status = 0 ORDER BY level DESC, xp DESC LIMIT %s", (limit,))
                    return await cursor.fetchall()
        except aiomysql.Error as e:
            print(f"Datenbankfehler beim Abrufen der Top-Benutzer: {e}")
            return []
