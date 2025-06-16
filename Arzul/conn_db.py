import aiomysql
import os
from dotenv import load_dotenv

# Laden der Umgebungsvariablen aus der .env-Datei
load_dotenv()

# Zugriff auf die Datenbank-Umgebungsvariablen
DB_HOST = os.getenv('DaBAHOST')
DB_USER = os.getenv('DaBaUser')
DB_PASSWORD = os.getenv('DaBaPassword')
DB_NAME = os.getenv('DaBaName')
DB_PORT = int(os.getenv('DaBaPort'))

# Globale Variable für den Datenbankpool
db_pool = None

async def create_db_pool():
    """Erstellt den Datenbankpool, falls er noch nicht existiert."""
    global db_pool
    if db_pool is None:
        try:
            db_pool = await aiomysql.create_pool(
                host=DB_HOST,
                user=DB_USER,
                password=DB_PASSWORD,
                db=DB_NAME,
                port=DB_PORT,
                autocommit=True
            )
            print("Database pool created successfully")
        except Exception as e:
            print(f"Fehler beim Erstellen des Datenbankpools: {e}")
    return db_pool

async def close_db_pool():
    """Schließt den Datenbankpool und setzt die Variable auf None."""
    global db_pool
    if db_pool:
        db_pool.close()
        await db_pool.wait_closed()
        db_pool = None  # Entferne die Referenz, um alle Verbindungen aufzuräumen
        print("Database pool closed")
