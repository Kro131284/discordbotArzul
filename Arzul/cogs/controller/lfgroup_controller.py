import discord
import logging
from discord.ext import commands
from discord import app_commands
from cogs.model.lfgroup_model import Group  # Import aus dem 'model' Modul
from cogs.view.lfgroup_view import GameDropdown, GroupSizeDropdown, JoinGroupView, GroupDescriptionModal
from datetime import datetime

CATEGORY_NAME = "Temporäre Gruppen"

class LFGController(commands.Cog):
    """Cog für den LFG-Befehl, der das Erstellen von Gruppen ermöglicht."""

    def __init__(self, bot):
        self.bot = bot
        self.bot.temp_channels = {}  # temporäre Channel hinzufügen

    @app_commands.command(name="lfg", description="Erstelle eine Gruppe für ein Spiel.")
    async def lfg(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)  # Interaktion verzögern, um Zeit für DB-Abfrage zu haben

        game_names = await Group.fetch_game_options()
        if not game_names:
            await interaction.followup.send("Keine Spiele verfügbar.", ephemeral=True)
            return

        dropdown = GameDropdown(self.bot)
        dropdown.options = [
            discord.SelectOption(label=game, description=f"Erstelle eine Gruppe für {game}", value=game)
            for game in game_names
        ]
        dropdown.callback = self.game_dropdown_callback  # Callback der Dropdown Liste zuweisen

        view = discord.ui.View()
        view.add_item(dropdown)
        await interaction.followup.send("Wähle ein Spiel aus:", view=view, ephemeral=True)

    async def game_dropdown_callback(self, interaction: discord.Interaction):
        game_name = interaction.data['values'][0]  # Wert aus dem Dropdown auslesen
        await self.show_group_size(interaction, game_name)

    async def show_group_size(self, interaction: discord.Interaction, game_name: str):
        """Zeigt Dropdown für Gruppengrößen basierend auf dem Spiel."""
        try:
            print(f"[DEBUG] show_group_size() aufgerufen mit game_name = {game_name}")

            await interaction.response.defer(ephemeral=True)

            group_sizes = await Group.fetch_group_sizes(game_name)  # Hier wird die SQL-Abfrage gemacht!

            if not group_sizes:
                print(f"[DEBUG] Keine Gruppengrößen für {game_name} gefunden!")
                await interaction.followup.send(
                    f"Keine Gruppengrößen für {game_name} verfügbar. Bitte versuche es später erneut.", ephemeral=True
                )
                return

            print(f"[DEBUG] Gefundene Gruppengrößen für {game_name}: {group_sizes}")

            # Dropdown für Gruppengrößen erstellen
            dropdown = GroupSizeDropdown(interaction, interaction.client, game_name)

            dropdown.options = [
                discord.SelectOption(label=f"{size} Spieler", description=f"Größe für {game_name}", value=str(size))
                for size in group_sizes
            ]
            dropdown.callback = self.group_size_dropdown_callback  # Callback der Dropdown Liste zuweisen

            view = discord.ui.View()
            view.add_item(dropdown)

            print(f"[DEBUG] Sende Gruppengrößen-Dropdown für {game_name}")
            await interaction.followup.send("Wähle die Gruppengröße:", view=view, ephemeral=True)
        except Exception as e:
            error_msg = f"Ein Fehler in show_group_size() für {game_name}: {e}"
            logging.error(error_msg)
            print(f"[ERROR] {error_msg}")
            await interaction.followup.send(f"Ein Fehler ist aufgetreten: {e}", ephemeral=True)

    async def group_size_dropdown_callback(self, interaction: discord.Interaction):
        group_size = int(interaction.data['values'][0])
        game_name = interaction.message.content.split()[-1]
        modal = GroupDescriptionModal(interaction, group_size, game_name)
        await interaction.response.send_modal(modal)

    async def create_group(self, interaction: discord.Interaction, group_name : str, game_name : str, group_size: int, start_date: str, start_time: str):
        """Erstellt eine Gruppe und sendet eine Nachricht mit Buttons."""
        try:
            guild = interaction.guild
            member = interaction.user
            # Channel-Titel mit Spielname und Gruppenname
            channel_title = f"[* {game_name} *] {group_name}"

            # Kategorie für Gruppen prüfen/erstellen
            category = discord.utils.get(guild.categories, name=CATEGORY_NAME)
            if not category:
                category = await guild.create_category(CATEGORY_NAME)
            
            # Temporären Textkanal erstellen
            temp_channel = await guild.create_text_channel(name=channel_title, category=category)

            # Gruppendaten speichern
            self.bot.temp_channels[temp_channel.id] = {
                "group_size": group_size,
                "members": [],
                "creator": member,
                "last_active": datetime.utcnow(),
                "game_name": game_name,
                "group_name": group_name,
                "channel_title" : channel_title,
                "start_date": start_date,
                "start_time": start_time
            }

            # Embed erstellen
            embed = discord.Embed(
                title=channel_title,
                color=discord.Color.green(),
                description=f"**Startdatum:** {start_date}\n**Startzeit:** {start_time}\n\nNoch keine Beschreibung."
            )
            embed.add_field(name="Teilnehmer", value="Noch keine Anmeldungen", inline=False)
            embed.set_footer(text="Drücke den Button, um beizutreten!")
            embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)

            # View mit Buttons erstellen
            view = JoinGroupView(temp_channel, self.bot, member, channel_title=channel_title)

            # Nachricht mit Buttons senden
            message = await temp_channel.send(embed=embed, view=view)

            # Nachricht in Gruppendaten speichern
            self.bot.temp_channels[temp_channel.id]["message"] = message

            # Erstelle Voice-Kanal und Verschiebe den ersteller.
            await view.create_voice_channel(interaction)

            await interaction.followup.send(f"Gruppe für {game_name} wurde in {temp_channel.mention} erstellt!", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"Ein Fehler ist aufgetreten: {e}", ephemeral=True)

# Cog registrieren
async def setup(bot):
    await bot.add_cog(LFGController(bot))
