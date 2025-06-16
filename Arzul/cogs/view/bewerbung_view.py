import discord
from discord.ui import Modal, View, Button, TextInput
from discord import ButtonStyle
import os
import asyncio
from cogs.model.bewerbung_model import Application

SUPPORT_ROLE_ID_1 = int(os.getenv('UV_ID', 0))
SUPPORT_ROLE_ID_2 = int(os.getenv('UV2_ID', 0))
SUPPORT_ROLE_ID_3 = int(os.getenv('Offi_ID', 0))

class ApplicationModal(Modal):
    def __init__(self, user: discord.User):
        super().__init__(title="Bewerbung")
        self.user = user

        self.hopes = TextInput(label="Hoffnungen", placeholder="Was erhoffst du dir von der Bewerbung?")
        self.values = TextInput(label="Werte", placeholder="Welche Werte sind dir wichtig?")
        self.role = TextInput(label="Rolle", placeholder="Welche Rolle möchtest du übernehmen?")

        self.add_item(self.hopes)
        self.add_item(self.values)
        self.add_item(self.role)

    async def on_submit(self, interaction: discord.Interaction):
        # Erstelle ein Bewerbungsobjekt
        application = Application(
            user=self.user,
            hopes=self.hopes.value,
            values=self.values.value,
            role=self.role.value,
        )

        # Verarbeite die Bewerbung (leite sie an den Controller weiter)
        controller = interaction.client.get_cog("BewerbungController")
        if controller:
            await controller.send_application_embed(interaction, application)
        else:
            await interaction.response.send_message("Fehler: Bewerbungscontroller nicht gefunden.", ephemeral=True)


class ApplicationManageButtons(View):
    def __init__(self, application_owner):
        super().__init__(timeout=None)
        self.application_owner = application_owner

    @discord.ui.button(label="Bewerbung genehmigen", style=ButtonStyle.green)
    async def genehmigen(self, interaction: discord.Interaction, button: Button):
        if not self._has_permission(interaction):
            await interaction.response.send_message("Du hast keine Berechtigung, diese Bewerbung zu genehmigen.", ephemeral=True)
            return

        await interaction.response.send_message("Bewerbung wurde genehmigt!", ephemeral=True)

    @discord.ui.button(label="Bewerbung ablehnen", style=ButtonStyle.red)
    async def ablehnen(self, interaction: discord.Interaction, button: Button):
        if not self._has_permission(interaction):
            await interaction.response.send_message("Du hast keine Berechtigung, diese Bewerbung abzulehnen.", ephemeral=True)
            return

        # Schließe den Bewerbungskanal
        await interaction.response.send_message("Bewerbung wurde abgelehnt und der Kanal wird geschlossen.", ephemeral=True)
        
        # Schließe den Kanal nach einer kurzen Verzögerung
        await asyncio.sleep(3)  # 3 Sekunden warten, um den Benutzer die Nachricht sehen zu lassen
        
        application_channel = interaction.channel  # Hole den aktuellen Kanal
        try:
            await application_channel.delete()  # Lösche den Kanal
        except discord.Forbidden:
            await application_channel.send("Fehler: Ich habe keine Berechtigung, diesen Kanal zu löschen.")
        except discord.HTTPException as e:
            await application_channel.send(f"Ein Fehler ist aufgetreten: {e}")

    def _has_permission(self, interaction):
        return any(
            role.id in [SUPPORT_ROLE_ID_1, SUPPORT_ROLE_ID_2, SUPPORT_ROLE_ID_3]
            for role in interaction.user.roles
        )
