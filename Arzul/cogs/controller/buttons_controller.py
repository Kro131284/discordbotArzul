# cogs/controller/buttons_controller.py
import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button
from cogs.model.buttons_model import RoleModel
from cogs.view.buttons_view import EmbedView

class EmbedCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.role_model = RoleModel()

    # --- Button Handler für Ticket/Bewerbung ---
    async def handle_ticket_button(self, interaction: discord.Interaction):
        ticket_command = self.bot.tree.get_command("ticket")
        ticket_cog = self.bot.get_cog("TicketController")
        if ticket_command and ticket_cog:
            try:
                await ticket_command.callback(ticket_cog, interaction)
            except discord.errors.InteractionResponded:
                try:
                    await interaction.followup.send("Ticket-Prozess gestartet.", ephemeral=False)
                except discord.HTTPException:
                    pass
            except Exception:
                try:
                    if not interaction.response.is_done():
                        await interaction.response.send_message("Fehler beim Öffnen des Ticket-Modals.", ephemeral=False)
                    else:
                        await interaction.followup.send("Fehler beim Öffnen des Ticket-Modals.", ephemeral=False)
                except discord.HTTPException:
                    pass
        else:
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message("Ticket-Befehl/Cog nicht gefunden.", ephemeral=False)
                else:
                    await interaction.followup.send("Ticket-Befehl/Cog nicht gefunden.", ephemeral=False)
            except discord.HTTPException:
                pass

    async def handle_bewerbung_button(self, interaction: discord.Interaction):
        bewerbung_command = self.bot.tree.get_command("bewerbung")
        bewerbung_cog = self.bot.get_cog("BewerbungController")
        if bewerbung_command and bewerbung_cog:
            try:
                await bewerbung_command.callback(bewerbung_cog, interaction)
            except discord.errors.InteractionResponded:
                try:
                    await interaction.followup.send("Bewerbungs-Prozess gestartet.", ephemeral=False)
                except discord.HTTPException:
                    pass
            except Exception:
                try:
                    if not interaction.response.is_done():
                        await interaction.response.send_message("Fehler beim Öffnen des Bewerbungs-Modals.", ephemeral=False)
                    else:
                        await interaction.followup.send("Fehler beim Öffnen des Bewerbungs-Modals.", ephemeral=False)
                except discord.HTTPException:
                    pass
        else:
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message("Bewerbungs-Befehl/Cog nicht gefunden.", ephemeral=False)
                else:
                    await interaction.followup.send("Bewerbungs-Befehl/Cog nicht gefunden.", ephemeral=False)
            except discord.HTTPException:
                pass

    # --- Button Handler für LFG ---
    async def handle_lfg_button(self, interaction: discord.Interaction):
        lfg_command = self.bot.tree.get_command("lfg")
        lfg_cog = self.bot.get_cog("LFGController")
        if lfg_command and lfg_cog:
            try:
                await lfg_command.callback(lfg_cog, interaction)
            except discord.errors.InteractionResponded:
                try:
                    await interaction.followup.send("LFG gestartet.", ephemeral=False)
                except discord.HTTPException:
                    pass
            except Exception:
                try:
                    if not interaction.response.is_done():
                        await interaction.response.send_message("Fehler beim Öffnen des LFG-Modals.", ephemeral=False)
                    else:
                        await interaction.followup.send("Fehler beim Öffnen des LFG-Modals.", ephemeral=False)
                except discord.HTTPException:
                    pass
        else:
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message("LFG-Befehl/Cog nicht gefunden.", ephemeral=False)
                else:
                    await interaction.followup.send("LFG-Befehl/Cog nicht gefunden.", ephemeral=False)
            except discord.HTTPException:
                pass

    # --- Button Handler für Rollen (Antworten als ephemeral) ---
    async def handle_role_button(self, interaction: discord.Interaction, category: str, role_name: str):
        await interaction.response.defer()
        if not interaction.guild:
            await interaction.followup.send("Dieser Befehl kann nur auf einem Server verwendet werden.", ephemeral=True)
            return
        
        # Versuche, den Member über den Cache zu erhalten; andernfalls via API.
        member = interaction.guild.get_member(interaction.user.id)
        if not member:
            try:
                member = await interaction.guild.fetch_member(interaction.user.id)
            except Exception:
                await interaction.followup.send("Benutzerinformationen konnten nicht abgerufen werden.", ephemeral=True)
                return

        role_id = RoleModel.get_role_id(category, role_name)
        if not role_id:
            await interaction.followup.send(f"Rollen-ID für '{role_name}' nicht gefunden.", ephemeral=True)
            return

        role = interaction.guild.get_role(role_id)
        if not role:
            await interaction.followup.send(f"Rolle '{role_name}' (ID: {role_id}) nicht gefunden.", ephemeral=True)
            return

        try:
            if role in member.roles:
                await member.remove_roles(role, reason="User clicked role button again")
                await interaction.followup.send(f"{interaction.user.mention} hat die Rolle '{role.name}' entfernt.", ephemeral=True)
            else:
                await member.add_roles(role, reason="User clicked role button")
                await interaction.followup.send(f"{interaction.user.mention} hat die Rolle '{role.name}' erhalten!", ephemeral=True)
        except discord.Forbidden:
            await interaction.followup.send(f"Ich habe keine Berechtigung, die Rolle '{role.name}' zu verwalten.", ephemeral=True)
        except discord.HTTPException:
            await interaction.followup.send(f"Netzwerkfehler beim Verwalten der Rolle '{role.name}'.", ephemeral=True)
        except Exception:
            await interaction.followup.send(f"Unerwarteter Fehler beim Verwalten der Rolle '{role.name}'.", ephemeral=True)

    # --- Hauptbefehl zum Senden der Nachrichten in separaten Nachrichten ---
    @app_commands.command(name="button", description="Sendet die Embeds für Ticket/Bewerbung, PvE und PvP Rollen-Auswahl.")
    @app_commands.checks.has_permissions(administrator=True)
    async def embed_message(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)
        try:
            # 1. Nachricht: Haupt-Embed mit Ticket, Bewerbung und LFG
            embed_main = EmbedView.create_main_embed()
            if not isinstance(embed_main, discord.Embed):
                await interaction.followup.send("Fehler beim Erstellen des Haupt-Embeds.")
                return

            main_view = View(timeout=None)
            button_ticket = discord.ui.Button(
                label="Ticket erstellen",
                style=discord.ButtonStyle.primary,
                custom_id="main_create_ticket_temp",
                emoji="🔧"
            )
            button_bewerbung = discord.ui.Button(
                label="Bewerbung senden",
                style=discord.ButtonStyle.primary,
                custom_id="main_send_bewerbung_temp",
                emoji="📇"
            )
            button_lfg = discord.ui.Button(
                label="LFG",
                style=discord.ButtonStyle.primary,
                custom_id="main_lfg_temp",
                emoji="🔍"
            )
            button_ticket.callback = self.handle_ticket_button
            button_bewerbung.callback = self.handle_bewerbung_button
            button_lfg.callback = self.handle_lfg_button
            main_view.add_item(button_ticket)
            main_view.add_item(button_bewerbung)
            main_view.add_item(button_lfg)

            await interaction.followup.send(embed=embed_main, view=main_view)

            # 2. Nachricht: PvE Rollen-Embed mit zugehörigen Buttons
            embed_roles_pve = EmbedView.create_roles_embed('pve')
            if not embed_roles_pve:
                await interaction.followup.send("Fehler beim Erstellen des PvE-Rollen-Embeds.")
                return

            pve_view = View(timeout=None)
            role_button_tank = EmbedView.create_role_button("Tank", "<:Tank:1292758103128936468>", "pve_tank_temp")
            role_button_dps = EmbedView.create_role_button("DPS", "<:DPSrole:1292758071894085682>", "pve_dps_temp", discord.ButtonStyle.danger)
            role_button_healer = EmbedView.create_role_button("Healer", "<:healer:1292758088197341235>", "pve_healer_temp", discord.ButtonStyle.success)
            role_button_tank.callback = lambda i, cat="pve", rn="tank": self.handle_role_button(i, cat, rn)
            role_button_dps.callback = lambda i, cat="pve", rn="dps": self.handle_role_button(i, cat, rn)
            role_button_healer.callback = lambda i, cat="pve", rn="healer": self.handle_role_button(i, cat, rn)
            pve_view.add_item(role_button_tank)
            pve_view.add_item(role_button_dps)
            pve_view.add_item(role_button_healer)

            await interaction.followup.send(embed=embed_roles_pve, view=pve_view)

            # 3. Nachricht: PvP Rollen-Embed mit zugehörigen Buttons
            embed_roles_pvp = EmbedView.create_roles_embed('pvp')
            if not embed_roles_pvp:
                await interaction.followup.send("Fehler beim Erstellen des PvP-Rollen-Embeds.")
                return

            pvp_view = View(timeout=None)
            role_button_pvp_tank = EmbedView.create_role_button("PvP-Tank", "<:Tank:1292758103128936468>", "pvp_tank_temp")
            role_button_pvp_dps = EmbedView.create_role_button("PvP-DPS", "<:DPSrole:1292758071894085682>", "pvp_dps_temp", discord.ButtonStyle.danger)
            role_button_pvp_healer = EmbedView.create_role_button("PvP-Healer", "<:healer:1292758088197341235>", "pvp_healer_temp", discord.ButtonStyle.success)
            role_button_pvp_tank.callback = lambda i, cat="pvp", rn="pvp_tank": self.handle_role_button(i, cat, rn)
            role_button_pvp_dps.callback = lambda i, cat="pvp", rn="pvp_dps": self.handle_role_button(i, cat, rn)
            role_button_pvp_healer.callback = lambda i, cat="pvp", rn="pvp_healer": self.handle_role_button(i, cat, rn)
            pvp_view.add_item(role_button_pvp_tank)
            pvp_view.add_item(role_button_pvp_dps)
            pvp_view.add_item(role_button_pvp_healer)

            await interaction.followup.send(embed=embed_roles_pvp, view=pvp_view)

        except discord.Forbidden:
            await interaction.followup.send("Fehler: Keine Berechtigung, Nachricht zu senden.")
        except discord.HTTPException as e:
            await interaction.followup.send(f"Fehler beim Senden der Nachricht (HTTP {e.status}): {e.text}")
        except Exception as e:
            await interaction.followup.send(f"Unerwarteter Fehler beim Senden der Nachricht: {e}")

    @embed_message.error
    async def embed_message_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            if interaction.response.is_done():
                await interaction.followup.send("Keine Admin-Berechtigungen für diesen Befehl.")
            else:
                await interaction.response.send_message("Keine Admin-Berechtigungen für diesen Befehl.")
        else:
            try:
                if interaction.response.is_done():
                    await interaction.followup.send(f"Fehler beim Starten des Befehls: {error}")
                else:
                    await interaction.response.send_message(f"Fehler beim Starten des Befehls: {error}")
            except discord.HTTPException:
                pass

async def setup(bot):
    await bot.add_cog(EmbedCog(bot))
