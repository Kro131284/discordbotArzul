# cogs/view/buttons_view.py
import discord
from discord.ui import Button, View

class EmbedView:
    """Erstellt die Embeds und Buttons."""

    @staticmethod
    def create_main_embed():
        """Erstellt das Haupt-Embed."""
        embed = discord.Embed(
            title="Kontrollmenü für Tickets und Bewerbungen",
            description="Bitte wähle die gewünschte Aktion:",
            color=discord.Color.green()
        )
        embed.add_field(name="Tickets", value="Mit dem Button könnt ihr den /ticket-Befehl ausführen.", inline=False)
        embed.add_field(name="Bewerbungen", value="Sende uns eine Bewerbung, um ein Teil der Gilde zu werden.", inline=False)
        embed.add_field(name="LfG", value="Starte eine Gruppen suche für ein bestimmtes Spiel.", inline=False)
        return embed

    @staticmethod
    def create_roles_embed(category):
        """Erstellt das Rollen-Embed für die angegebene Kategorie."""
        if category == 'pve':
            title = "PvE Rollen-Auswahl"
            description = "Wählt eine Rolle für PvE-Aktivitäten:"
            color = discord.Color.green()
        elif category == 'pvp':
            title = "PvP Rollen-Auswahl"
            description = "Wählt eine Rolle für PvP-Aktivitäten:"
            color = discord.Color.red()
        else:
            return None

        embed = discord.Embed(
            title=title,
            description=description,
            color=color
        )
        return embed

    @staticmethod
    def create_role_button(label, emoji, role_name, style=discord.ButtonStyle.primary):
        """Erstellt einen Rollen-Button."""
        return Button(label=label, style=style, emoji=emoji, custom_id=role_name)
