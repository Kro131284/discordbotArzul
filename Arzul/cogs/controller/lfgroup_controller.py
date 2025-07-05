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
        """Zeigt Dropdown für Gruppengrößen basierend auf dem Spiel."""
        try:
            print(f"[DEBUG] show_group_size() aufgerufen mit game_name = {game_name}")

            # Wichtig: Diese Interaktion wurde bereits im game_dropdown_callback ausgelöst.
            # Wenn game_dropdown_callback nicht deferiert hat, muss hier deferiert werden.
            # Da es im lfg-Befehl schon deferiert und dann ein followup sendet,
            # ist die Interaktion aus dem ersten Dropdown 'beantwortet'.
            # Der Klick auf das zweite Dropdown (GameDropdown) ist eine NEUE Interaktion,
            # die eine neue Antwort erfordert.
            # Hier ist es entscheidend, dass show_group_size auf die INTERAKTION aus dem GameDropdown reagiert.
            
            # Wichtig: Prüfen, ob die Interaktion bereits geantwortet wurde. 
            # Das ist der Fall, wenn sie von einer vorherigen Dropdown-Auswahl kommt.
            # Daher sollte der game_dropdown_callback die Interaktion an show_group_size weitergeben
            # und NICHT selbst deferieren oder antworten.
            # show_group_size sollte dann deferieren ODER direkt die Antwort senden.
            # Da die GroupSizeDropdown später ein Modal sendet, muss hier nur das Followup gesendet werden.
            
            # Da game_dropdown_callback keine response sendet, muss hier die erste response erfolgen.
            # Wir deferieren nicht sofort, sondern warten auf die Datenbankabfrage
            # und senden dann direkt eine followup Nachricht.
            # Wenn die DB-Abfrage länger dauert, KÖNNTE hier ein Timeout entstehen,
            # aber da wir dann ein Modal schicken, ist die Interaktion ja noch offen.

            group_sizes = await Group.fetch_group_sizes(game_name)

            if not group_sizes:
                print(f"[DEBUG] Keine Gruppengrößen für {game_name} gefunden!")
                # Hier muss auf die Interaktion geantwortet werden, wenn noch nicht geschehen
                # Da game_dropdown_callback pass ist, muss show_group_size antworten.
                await interaction.response.send_message( # <- Changed to response.send_message
                    f"Keine Gruppengrößen für {game_name} verfügbar. Bitte versuche es später erneut.", ephemeral=True
                )
                return

            print(f"[DEBUG] Gefundene Gruppengrößen für {game_name}: {group_sizes}")

            # Dropdown für Gruppengrößen erstellen
            # Wichtig: Die interaction_original muss die aktuelle interaction sein
            dropdown = GroupSizeDropdown(interaction, self.bot, game_name) # <- interaction und game_name übergeben

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
        # Diese Callback-Methode wird hier eigentlich NICHT mehr benötigt,
        # da der GroupSizeDropdown-Callback in der View das Modal direkt sendet.
        # Ich lasse sie als Kommentar hier, falls der Callback-Pfad geändert wird.
        pass
        # group_size = int(interaction.data['values'][0])
        # game_name = interaction.message.content.split()[-1] # <- Diese Art der Extraktion ist unzuverlässig
        # modal = GroupDescriptionModal(interaction, group_size, game_name)
        # await interaction.response.send_modal(modal) # <- Diese Zeile wäre im GroupSizeDropdown.callback

    async def create_group(self, interaction: discord.Interaction, group_name : str, game_name : str, group_size: int):
        """Erstellt eine Gruppe und sendet eine Nachricht mit Buttons."""
        try:
            guild = interaction.guild
            member = interaction.user # Creator ist der Interagierende

            # Temporären Textkanalnamen vorbereiten
            # Besser: Eine Kombination aus GameName und GroupName für Eindeutigkeit
            # Oder einfach nur group_name, wenn game_name im Embed-Titel steht
            channel_name_for_text_channel = f"{game_name.lower().replace(' ', '-')}-{group_name.lower().replace(' ', '-')}"
            # Discord Channel-Namen sind limitiert, kürzere Namen sind besser
            channel_name_for_text_channel = channel_name_for_text_channel[:90] # Max 100 Zeichen, plus etwas Puffer

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
                "members": [], # Startet leer
                "creator": member, # Speichert das Member-Objekt des Erstellers
                "last_active": datetime.utcnow(),
                "game_name": game_name,
                "group_name": group_name,
                "channel_title" : channel_title, # channel_title gespeichert
                "voice_channel": None # Voice-Channel wird erst später zugewiesen
            }

            # Embed erstellen
            embed = discord.Embed(
                title=channel_title,
                color=discord.Color.green(),
                description=f"Eine Gruppe für **{game_name}** wurde erstellt."
            )
            embed.add_field(name="Teilnehmer", value=f"**1/{group_size}**\n{member.display_name}", inline=False) # Creator ist der erste Teilnehmer
            embed.set_footer(text="Drücke den Button, um beizutreten!")
            embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)

            # Den Ersteller sofort zur Mitgliederliste hinzufügen
            self.bot.temp_channels[temp_channel.id]["members"].append(member)


            # View mit Buttons erstellen
            view = JoinGroupView(temp_channel, self.bot, member, channel_title=channel_title)

            # Nachricht mit Buttons senden
            # interaction hier ist die des Modals. Sie muss jetzt deferiert oder gesendet werden.
            # Da modal.on_submit das Modal gesendet hat, können wir hier ein followup senden.
            message = await temp_channel.send(embed=embed, view=view)

            # Nachricht in Gruppendaten speichern
            self.bot.temp_channels[temp_channel.id]["message"] = message

            # Erstelle Voice-Kanal und Verschiebe den Ersteller
            # Dies ist der erste Aufruf, um den VC zu erstellen und den Ersteller zu bewegen
            await view.create_voice_channel(interaction) # interaction ist die des Modals

            # Bestätigung an den Benutzer senden (ephemeral)
            if interaction.response.is_done(): # Wenn das Modal bereits geantwortet hat
                await interaction.followup.send(f"Gruppe für **{game_name}** wurde in {temp_channel.mention} erstellt!", ephemeral=True)
            else: # Wenn das Modal noch nicht geantwortet hat (sollte nicht der Fall sein, aber als Fallback)
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