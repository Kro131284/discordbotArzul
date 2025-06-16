import discord
from discord.ext import commands
from discord import app_commands
from cogs.model.bewerbung_model import Application
from cogs.view.bewerbung_view import ApplicationModal, ApplicationManageButtons

class BewerbungController(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def create_application(self, user, hopes, values, role):
        return Application(user, hopes, values, role)

    async def send_application_embed(self, interaction, application):
        # Stelle sicher, dass der Bewerbungs-Kanal existiert
        guild = interaction.guild
        application_channel = discord.utils.get(guild.text_channels, name="bewerbungen")
        if application_channel is None:
            application_channel = await guild.create_text_channel("bewerbungen")

        # Erstelle und sende die Embed-Nachricht
        embed = application.generate_embed()
        await application_channel.send(embed=embed, view=ApplicationManageButtons(application_owner=interaction.user))
        await interaction.response.send_message(
            f"Deine Bewerbung wurde erfolgreich im Kanal {application_channel.mention} veröffentlicht.",
            ephemeral=True
        )
        
        

    @app_commands.command(name="bewerbung", description="Starte den Bewerbungsprozess")
    async def bewerbung(self, interaction: discord.Interaction):
        modal = ApplicationModal(interaction.user)  # Modal mit Benutzerdaten initialisieren
        await interaction.response.send_modal(modal)

async def setup(bot):
    await bot.add_cog(BewerbungController(bot))
