# welcome_controller.py
import discord
from discord.ext import commands
from discord import app_commands, Interaction
import random
import os
import asyncio
from dotenv import load_dotenv
from cogs.model.welcome_model import GreetingsModel
from cogs.view.welcome_view import WelcomeView, WelcomeModal
from conn_db import create_db_pool

load_dotenv()
Willk_ID = int(os.getenv('Willk_ID'))

class WelcomeController(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.pool = None
        self.pool_initialized = asyncio.Event()
        self.bot.loop.create_task(self.create_pool())
        self.model = None
        self.view = WelcomeView()

        bot.add_listener(self.on_shutdown, "on_shutdown")

    async def create_pool(self):
        try:
            print("Initializing the database pool...")
            self.pool = await create_db_pool()
            self.bot.pool = self.pool
            self.model = GreetingsModel(self.pool)
            self.pool_initialized.set()
            print("Database pool created successfully")
        except Exception as e:
            print(f"Error creating database pool: {e}")

    async def close_pool(self):
        if self.pool is not None:
            self.pool.close()
            await self.pool.wait_closed()
            print("Database pool closed")

    async def on_shutdown(self):
        print("Shutting down bot gracefully...")
        await self.close_pool()

    def cog_unload(self):
        self.bot.loop.create_task(self.close_pool())

    @commands.Cog.listener()
    async def on_member_join(self, member):
        print(f"Mitglied beigetreten: {member.name}")
        # WICHTIG: Prüfe, ob self.model initialisiert ist
        if self.model is None:
            print("Fehler: self.model ist nicht initialisiert!")
            return
        channel = self.bot.get_channel(Willk_ID)
        if not channel:
            print(f"Kanal mit ID {Willk_ID} nicht gefunden.")
            return
        try:
            greetings = await self.model.fetch_greetings()
            if greetings:
                greeting = random.choice(greetings)[0]
            else:
                greeting = "Willkommen auf dem Server, {name}!"

            # Nachricht nach deinem Muster
            welcome_message = f"Herzlich willkommen, {member.mention}!\n{greeting.format(name=member.name)}"
            await channel.send(welcome_message)

        except Exception as e:
            print(f"Ein Fehler ist aufgetreten: {e}")

    @app_commands.command(name="welcome", description="Gebe eine individuelle Begrüssung für Neulinge ein")
    async def welcome(self, interaction: Interaction):
        modal = WelcomeModal(self.bot, self.pool_initialized)
        await interaction.response.send_modal(modal)

    async def add_greeting(self, interaction, message_content):
        user_name = interaction.user.name
        await self.model.add_greeting(message_content, user_name)

async def setup(bot):
    await bot.add_cog(WelcomeController(bot))
    await bot.tree.sync()
