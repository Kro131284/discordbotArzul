import discord
from discord.ui import View, Button, Modal
from discord.ext import commands
import os
import asyncio

class TicketManageButtons(discord.ui.View):
    def __init__(self, ticket_owner):
        super().__init__(timeout=None)  # Timeout deaktivieren
        self.ticket_owner = ticket_owner

    @discord.ui.button(label="Ticket bearbeiten", style=discord.ButtonStyle.blurple)
    async def bearbeiten(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()  # Antwort verzögern
        ticket_channel = interaction.channel
        await ticket_channel.set_permissions(self.ticket_owner, read_messages=True, send_messages=True)
        await ticket_channel.send(f"{self.ticket_owner.mention} wurde wieder in das Ticket hinzugefügt.")
        await self.ticket_owner.send(f"Du wurdest in das Ticket {ticket_channel.name} zurückgeholt.")

    @discord.ui.button(label="Ticket schließen", style=discord.ButtonStyle.red)
    async def schliessen(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()  # Antwort verzögern
        ticket_channel = interaction.channel
        await self.ticket_owner.send(f"Dein Ticket {ticket_channel.name} wird jetzt geschlossen.")
        await ticket_channel.send("Dieses Ticket wird in 5 Sekunden geschlossen...")

        # Manuelle Verzögerung von 5 Sekunden
        await asyncio.sleep(5)

        try:
            await ticket_channel.delete()  # Kanal nach der Verzögerung löschen
        except discord.Forbidden:
            await ticket_channel.send("Fehler: Ich habe keine Berechtigung, diesen Kanal zu löschen.")
        except discord.HTTPException as e:
            await ticket_channel.send(f"Ein Fehler ist aufgetreten: {e}")


class TicketModal(discord.ui.Modal, title="Erstelle ein neues Ticket"):
    title_input = discord.ui.TextInput(label="Überschrift", style=discord.TextStyle.short)
    description_input = discord.ui.TextInput(label="Grobe Beschreibung", style=discord.TextStyle.long)

    def __init__(self, user):
        super().__init__()
        self.user = user

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild

        # Ticket-Channel Name
        channel_name = f"ticket-{self.user.name}-{self.user.discriminator}"

        # Überprüfen, ob der Ticket-Kanal bereits existiert
        existing_channel = discord.utils.get(guild.text_channels, name=channel_name)
        if existing_channel:
            await interaction.response.send_message(f"Du hast bereits ein offenes Ticket: {existing_channel.mention}", ephemeral=True)
            return

        # Berechtigungen für den Kanal setzen
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            self.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        }
        support_roles = [
            guild.get_role(int(os.getenv('UV_ID'))),
            guild.get_role(int(os.getenv('UV2_ID'))),
            guild.get_role(int(os.getenv('Offi_ID')))
        ]
        for role in support_roles:
            if role:
                overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        # Ticket-Kanal erstellen
        ticket_channel = await guild.create_text_channel(channel_name, overwrites=overwrites)

        # Embed erstellen
        embed = discord.Embed(title="Neues Ticket", color=discord.Color.blue())
        embed.add_field(name="Ersteller", value=f"{self.user.name}#{self.user.discriminator} (ID: {self.user.id})", inline=False)
        embed.add_field(name="Überschrift", value=self.title_input.value, inline=False)
        embed.add_field(name="Grobe Beschreibung", value=self.description_input.value, inline=False)
        embed.set_footer(text=f"Erstellt von {self.user}", icon_url=self.user.avatar.url)

        # Nachricht mit Embed und Buttons senden
        view = TicketManageButtons(ticket_owner=self.user)
        await ticket_channel.send(embed=embed, view=view)
        await interaction.response.send_message(f"Dein Ticket wurde erstellt: {ticket_channel.mention}", ephemeral=True)


class TicketView:
    @staticmethod
    def create_ticket_embed(ticket_model):
        embed = discord.Embed(title="Neues Ticket", color=discord.Color.blue())
        embed.add_field(name="Ersteller", value=f"{ticket_model.user.name}#{ticket_model.user.discriminator} (ID: {ticket_model.user.id})", inline=False)
        embed.add_field(name="Überschrift", value=ticket_model.title, inline=False)
        embed.add_field(name="Grobe Beschreibung", value=ticket_model.description, inline=False)
        embed.set_footer(text=f"Erstellt von {ticket_model.user}", icon_url=ticket_model.user.avatar.url)
        return embed

    @staticmethod
    async def send_ticket_creation_message(ticket_channel, embed, ticket_model):
        view = TicketManageButtons(ticket_owner=ticket_model.user)  # Buttons-View erstellen
        await ticket_channel.send(embed=embed, view=view)  # Nachricht mit Embed und Buttons senden

    @staticmethod
    async def send_ticket_already_exists_message(interaction, existing_channel):
        await interaction.response.send_message(f"Du hast bereits ein offenes Ticket: {existing_channel.mention}", ephemeral=True)

    @staticmethod
    async def send_ticket_created_message(interaction, ticket_channel):
        await interaction.response.send_message(f"Dein Ticket wurde erstellt: {ticket_channel.mention}", ephemeral=True)
