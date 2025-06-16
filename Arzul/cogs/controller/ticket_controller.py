import discord
import asyncio
from cogs.model.ticket_model import TicketModel
from cogs.view.ticket_view import TicketView,TicketModal
from discord.ui import View
from discord import app_commands
from discord.ext import commands
import os
from dotenv import load_dotenv

load_dotenv()
# Support-Rollen-IDs
SUPPORT_ROLE_ID_1 = int(os.getenv('UV_ID'))
SUPPORT_ROLE_ID_2 = int(os.getenv('UV2_ID'))
SUPPORT_ROLE_ID_3 = int(os.getenv('Offi_ID'))

# ID des Channels, in dem der Button gesendet werden soll
TICKET_CHANNEL_ID = int(os.getenv('Support_ID'))


class TicketController(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Ticket-Erstellungslogik
    async def handle_ticket_creation(self, interaction, title, description):
        guild = interaction.guild
        support_roles = [
            guild.get_role(int(os.getenv('UV_ID'))),
            guild.get_role(int(os.getenv('UV2_ID'))),
            guild.get_role(int(os.getenv('Offi_ID')))
        ]

        # TicketModel instanziieren
        ticket_model = TicketModel(interaction.user, title, description, guild, support_roles)

        # Prüfen, ob der Kanal bereits existiert
        existing_channel = discord.utils.get(guild.text_channels, name=ticket_model.get_ticket_channel_name())
        if existing_channel:
            await TicketView.send_ticket_already_exists_message(interaction, existing_channel)
            return

        # Ticket-Kanal erstellen
        ticket_channel = await ticket_model.create_ticket_channel()

        # Embed und Nachrichten senden
        embed = TicketView.create_ticket_embed(ticket_model)
        await TicketView.send_ticket_creation_message(ticket_channel, embed, ticket_model)
        await TicketView.send_ticket_created_message(interaction, ticket_channel)

    # Slash-Befehl zum Öffnen des Ticket-Modals
    @app_commands.command(name="ticket", description="Erstellt ein neues Ticket")
    async def ticket(self, interaction: discord.Interaction):
        modal = TicketModal(interaction.user)  # Benutzer wird an den Konstruktor übergeben
        await interaction.response.send_modal(modal)

# Cog-Setup-Funktion
async def setup(bot):
    await bot.add_cog(TicketController(bot))