import discord
import logging
from discord.ext import commands
from discord import app_commands
from cogs.model.lfgroup_model import Group  # Import aus dem 'model' Modul
# Sicherstellen, dass alle View-Komponenten korrekt importiert werden
from cogs.view.lfgroup_view import GameDropdown, GroupSizeDropdown, JoinGroupView, GroupDescriptionModal
from datetime import datetime

CATEGORY_NAME = "Temporäre Gruppen"

class LFGController(commands.Cog):
    """Cog für den LFG-Befehl, der das Erstellen von Gruppen ermöglicht."""

    def __init__(self, bot):
        self.bot = bot
        self.bot.temp_channels = {}  # temporäre Channel hinzufügen
        print("LFGController geladen und bereit.") # Debugging-Ausgabe

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
        # Der Callback wird direkt hier auf die Instanzmethode des Controllers gesetzt
        dropdown.callback = self.game_dropdown_callback  

        view = discord.ui.View()
        view.add_item(dropdown)
        await interaction.followup.send("Wähle ein Spiel aus:", view=view, ephemeral=True)

    async def game_dropdown_callback(self, interaction: discord.Interaction):
        game_name = interaction.data['values'][0]  # Wert aus dem Dropdown auslesen
        # Keine defer/followup hier, da show_group_size dies übernimmt
        await self.show_group_size(interaction, game_name)

    async def show_group_size(self, interaction: discord.Interaction, game_name: str):
        """Zeigt Dropdown für Gruppengrößen basierend auf dem Spiel oder öffnet direkt das Modal, wenn nur eine Größe vorhanden ist."""
        try:
            print(f"[DEBUG] show_group_size() aufgerufen mit game_name = {game_name}")


            group_sizes = await Group.fetch_group_sizes(game_name)

            group_sizes = await Group.fetch_group_sizes(game_name)  # Hier wird die SQL-Abfrage gemacht!

            if not group_sizes:
                print(f"[DEBUG] Keine Gruppengrößen für {game_name} gefunden!")
                # Hier muss auf die Interaktion geantwortet werden, wenn noch nicht geschehen
                # Da game_dropdown_callback pass ist, muss show_group_size antworten.
                await interaction.response.send_message( # <- Changed to response.send_message
                    f"Keine Gruppengrößen für {game_name} verfügbar. Bitte versuche es später erneut.", ephemeral=True
                )
                return

            # Gruppengrößen aufsteigend sortieren
            group_sizes = sorted(group_sizes)
            print(f"[DEBUG] Gefundene Gruppengrößen für {game_name}: {group_sizes}")

            # Dropdown für Gruppengrößen erstellen
            # Wichtig: Die interaction_original muss die aktuelle interaction sein
            dropdown = GroupSizeDropdown(interaction, self.bot, game_name) # <- interaction und game_name übergeben
            if len(group_sizes) == 1:
                # Nur eine Gruppengröße -> Modal direkt öffnen (ohne defer!)
                group_size = group_sizes[0]
                modal = GroupDescriptionModal(interaction, group_size, game_name)
                await interaction.response.send_modal(modal)
                return

            # Mehrere Gruppengrößen: jetzt defer und Dropdown anzeigen
            await interaction.response.defer(ephemeral=True)
            dropdown = GroupSizeDropdown(interaction, interaction.client, game_name)
            dropdown.options = [
                discord.SelectOption(label=f"{size} Spieler", description=f"Größe für {game_name}", value=str(size))
                for size in group_sizes
            ]
            # Callback der Dropdown Liste zuweisen (wird von der View-Klasse selbst gehandhabt)
            # dropdown.callback = self.group_size_dropdown_callback  # -> NICHT HIER ZUWEISEN

            view = discord.ui.View()
            view.add_item(dropdown)

            print(f"[DEBUG] Sende Gruppengrößen-Dropdown für {game_name}")
            # Dies ist die erste Antwort auf die game_dropdown_callback-Interaktion
            await interaction.response.send_message("Wähle die Gruppengröße:", view=view, ephemeral=True) # <- response.send_message
        except Exception as e:
            error_msg = f"Ein Fehler in show_group_size() für {game_name}: {e}"
            logging.error(error_msg)
            print(f"[ERROR] {error_msg}")
            # Fallback, falls show_group_size fehlschlägt
            if not interaction.response.is_done():
                await interaction.response.send_message(f"Ein Fehler ist aufgetreten: {e}", ephemeral=True)
            else:
                await interaction.followup.send(f"Ein Fehler ist aufgetreten: {e}", ephemeral=True)


    # Diese Methode wird nun vom GroupSizeDropdown.callback DIREKT aufgerufen,
    # da GroupSizeDropdown das Modal selbst sendet.
    # Der LFGController muss nur die create_group Methode bereitstellen.
    # Die Logik der Modal-Anzeige ist jetzt vollständig in der View.
    async def group_size_dropdown_callback(self, interaction: discord.Interaction):
        # Hole die Gruppengröße und den Spielnamen direkt aus der Auswahl
        group_size = int(interaction.data['values'][0])
        # Der Spielname wird im Dropdown-Objekt gespeichert
        # Finde das passende Dropdown-Objekt in der View
        game_name = None
        for item in interaction.message.components[0]['components']:
            if item['custom_id'] == 'group_size_dropdown':
                # Hole das Label der ersten Option (z.B. '5 Spieler') und die Description
                desc = item.get('options', [{}])[0].get('description', '')
                if 'Größe für ' in desc:
                    game_name = desc.split('Größe für ')[-1]
        if not game_name:
            game_name = 'Unbekanntes Spiel'
        modal = GroupDescriptionModal(interaction, group_size, game_name)
        await interaction.response.send_modal(modal)

    async def create_group(self, interaction: discord.Interaction, group_name : str, game_name : str, group_size: int, start_date: str, start_time: str):
        """Erstellt eine Gruppe und sendet eine Nachricht mit Buttons."""
        try:
            guild = interaction.guild
            member = interaction.user # Creator ist der Interagierende

            # Temporären Textkanalnamen vorbereiten
            channel_name_for_text_channel = f"{game_name.lower().replace(' ', '-')}-{group_name.lower().replace(' ', '-')}"

            channel_title = f"[{game_name}] {group_name}" # Titel für Embed und Voice-Channel

            # Kategorie für Gruppen prüfen/erstellen
            category = discord.utils.get(guild.categories, name=CATEGORY_NAME)
            if not category:
                category = await guild.create_category(CATEGORY_NAME)
            
            # Temporären Textkanal erstellen
            temp_channel = await guild.create_text_channel(name=channel_name_for_text_channel, category=category)

            # Gruppendaten speichern
            self.bot.temp_channels[temp_channel.id] = {
                "group_size": group_size,
                "members": [],
                "creator": member,
                "last_active": datetime.utcnow(),
                "game_name": game_name,
                "group_name": group_name,
                "channel_title": channel_title,
                "voice_channel": None
            }

            # Embed erstellen
            embed = discord.Embed(
                title=channel_title,
                color=discord.Color.green(),
                description=f"Eine Gruppe für **{game_name}** wurde erstellt."
            )
            embed.add_field(name="Teilnehmer", value=f"**1/{group_size}**\n{member.display_name}", inline=False)
            embed.set_footer(text="Drücke den Button, um beizutreten!")
            embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)

            # Den Ersteller sofort zur Mitgliederliste hinzufügen
            self.bot.temp_channels[temp_channel.id]["members"].append(member)

            # View mit Buttons erstellen
            view = JoinGroupView(temp_channel, self.bot, member, channel_title=channel_title)

            # Nachricht mit Buttons senden
            message = await temp_channel.send(embed=embed, view=view)

            # Nachricht in Gruppendaten speichern
            self.bot.temp_channels[temp_channel.id]["message"] = message

            # Erstelle Voice-Kanal und verschiebe den Ersteller
            await view.create_voice_channel(interaction)

            # Bestätigung an den Benutzer senden (ephemeral)
            if interaction.response.is_done():
                await interaction.followup.send(f"Gruppe für **{game_name}** wurde in {temp_channel.mention} erstellt!", ephemeral=True)
            else:
                await interaction.response.send_message(f"Gruppe für **{game_name}** wurde in {temp_channel.mention} erstellt!", ephemeral=True)
        except Exception as e:
            error_msg = f"Ein Fehler bei create_group(): {e}"
            logging.error(error_msg, exc_info=True) # exc_info für vollständigen Traceback
            print(f"[ERROR] {error_msg}")
            if not interaction.response.is_done():
                await interaction.response.send_message(f"Ein Fehler ist beim Erstellen der Gruppe aufgetreten: {e}", ephemeral=True)
            else:
                await interaction.followup.send(f"Ein Fehler ist beim Erstellen der Gruppe aufgetreten: {e}", ephemeral=True)


# Cog registrieren
async def setup(bot):
    await bot.add_cog(LFGController(bot))