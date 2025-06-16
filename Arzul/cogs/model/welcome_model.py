# welcome_model.py

class GreetingsModel:
    def __init__(self, pool):
        self.pool = pool

    async def fetch_greetings(self):
        """Holt alle Begrüßungsnachrichten aus der Datenbank."""
        try:
            async with self.pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute('SELECT message FROM greetings')
                    results = await cursor.fetchall()
                    return results
        except Exception as e:
            print(f"Fehler beim Abrufen der Begrüßungsnachrichten: {e}")
            return []

    async def add_greeting(self, message, author_username):
        """Fügt eine neue Begrüßungsnachricht in die Datenbank ein."""
        try:
            async with self.pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    query = 'INSERT INTO greetings (message, author_username) VALUES (%s, %s)'
                    await cursor.execute(query, (message, author_username))
                    print(f"Neue Begrüßungsnachricht von {author_username} hinzugefügt.")
        except Exception as e:
            print(f"Fehler beim Hinzufügen der Begrüßungsnachricht: {e}")
