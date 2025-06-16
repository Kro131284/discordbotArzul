import logging
import discord
import aiomysql
from conn_db import db_pool

# Logger für Fehlerprotokollierung
logger = logging.getLogger("discord_bot")

CATEGORY_NAME = "Temporäre Gruppen"

class Group:
    temp_channels = {}  # Speicherung temporärer Kanäle

    @staticmethod
    async def fetch_game_options():
        """Ruft verfügbare Spiele aus der Datenbank ab."""
        if not db_pool:
            logger.error("Datenbankverbindung nicht verfügbar.")
            return []

        try:
            async with db_pool.acquire() as conn, conn.cursor() as cursor:
                await cursor.execute("SELECT name FROM spiele")
                return list(map(lambda g: g[0], await cursor.fetchall()))  # Direkte Umwandlung in Liste
        except aiomysql.Error as e:
            logger.error(f"SQL-Fehler bei fetch_game_options: {e}")
            return []

    @staticmethod
    async def fetch_group_sizes(game_name: str):
        """Ruft die Gruppengrößen für ein bestimmtes Spiel ab."""
        try:
            async with db_pool.acquire() as conn, conn.cursor() as cursor:
                await cursor.execute("SELECT g.grösse FROM spiel_gruppengroesse sg INNER JOIN spiele s ON sg.spiel_id = s.id INNER JOIN gruppengrösse g ON sg.grösse_id = g.id WHERE s.name = %s", (game_name,))
                sizes = await cursor.fetchall()
                return [size[0] for size in sizes]
        except aiomysql.Error as e:
            logger.error(f"SQL-Fehler bei fetch_group_sizes: {e}")
            return []

    @staticmethod
    async def create_temp_channel(guild: discord.Guild, group_name: str):
        """Erstellt einen temporären Textkanal in der 'Temporäre Gruppen' Kategorie."""
        try:
            # Falls die Kategorie nicht existiert, erstelle sie
            category = discord.utils.get(guild.categories, name=CATEGORY_NAME) or await guild.create_category(CATEGORY_NAME)

            # Erstelle den temporären Kanal in dieser Kategorie
            return await guild.create_text_channel(name=group_name, category=category)
        except discord.DiscordException as e:
            logger.error(f"Fehler beim Erstellen des Kanals {group_name}: {e}")
            return None
