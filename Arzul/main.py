import discord
from discord.ext import commands
import os
import asyncio
from conn_db import create_db_pool, close_db_pool
from dotenv import load_dotenv

load_dotenv()  # Lädt die Umgebungsvariablen aus der .env-Datei
app_id = os.getenv("Application_ID")  # Application ID aus der .env-Datei holen
TOKEN = os.getenv("Discord_Token")  # Token aus der .env-Datei holen
if not TOKEN:
    print("Fehler: Discord-Token ist nicht gesetzt.")  # Ausgabe bei fehlendem Token
    exit()

print(f"Token erfolgreich geladen: {TOKEN[:5]}...")  # Zum Testen, dass das Token korrekt geladen wurde

# Create bot instance
intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
bot = commands.Bot(command_prefix='!', intents=intents,application_id=app_id)

# Function to load cogs
async def load_cogs():
    for filename in os.listdir('./cogs/controller'):
        if filename.endswith('.py') and filename != '__init__.py':
            cog_name = f'cogs.controller.{filename[:-3]}'
            try:
                await bot.load_extension(cog_name)
                print(f'Loaded {cog_name}')
            except Exception as e:
                print(f'Fehler beim Laden des Cogs {cog_name}: {e}')

# Event to sync commands when the bot is ready
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    await load_cogs()
    await bot.tree.sync()
    

# Main function to start the bot
async def main():
    async with bot:
        # Create the database pool and store it in the bot
        bot.pool = await create_db_pool()
        print("Database pool initialized")

        # Start the bot with the token
        await bot.start(TOKEN)

# Function to close the database pool when the bot shuts down
@bot.event
async def on_shutdown():
    """Funktion zum sauberen Herunterfahren."""
    print("Shutdown-Prozedur läuft...")
    if bot.pool:
        await close_db_pool()  # Close the pool properly
        print("Database pool closed on shutdown")
    await bot.close()  # Shut down the bot
    print("Bot wurde geschlossen.")

if __name__ == "__main__":
    asyncio.run(main())  # Das Token ist jetzt direkt im `main()` Aufruf
