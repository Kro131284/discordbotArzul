# cogs/controller/leave_controller.py
import discord
from discord.ext import commands
from conn_db import create_db_pool
from cogs.model.leave_model import LeaveModel
from cogs.view.leave_view import LeaveView
from dotenv import load_dotenv
import os

load_dotenv()
CHANNEL_ID = int(os.getenv('Leave_ID').strip())            # Channel für normales Verlassen
ACTION_CHANNEL_ID = int(os.getenv('Loch_ID').strip())      # Channel für Kick/Ban-Nachrichten

class MemberEventsController(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.pool = None
        self.bot.loop.create_task(self.ensure_db_pool())
        self.model = None
        self.view = LeaveView(bot)
        print("[LeaveController] Initialisiert.")

    async def ensure_db_pool(self):
        """Stellt sicher, dass der Verbindungspool existiert und initialisiert das Model."""
        self.pool = await create_db_pool()
        self.model = LeaveModel(self.pool)
        print("[LeaveController] DB-Pool erstellt und Modell geladen.")

    async def handle_member_leave(self, member, kicked=False, banned=False):
        """Verarbeitet das Verlassen eines Mitglieds."""
        try:
            if kicked:
                await self.view.send_leave_notification(member, ACTION_CHANNEL_ID, f'{member.name} wurde aus dem Loch gekickt.')
            elif banned:
                await self.view.send_leave_notification(member, ACTION_CHANNEL_ID, f'{member.name} wurde aus dem Loch verbannt.')
            else:
                await self.view.send_leave_notification(member, CHANNEL_ID, f'{member.name} hat das Loch verlassen.')
                await self.view.send_dm(member, f'Schade, dass du unser Loch verlässt, {member.name}. Viel Erfolg auf deiner weiteren Reise . . . Du Ratte!')

        except Exception as e:
            print(f"[Fehler] Beim Senden der Leave-Nachricht: {e}")

        # Datenbankeintrag setzen, wenn Modell verfügbar ist
        if self.model:
            try:
                updated = await self.model.set_user_deleted(member.id)
                if not updated:
                    print(f"[Info] Kein DB-Eintrag für User {member.id} gefunden. Überspringe DB-Update.")
            except Exception as e:
                print(f"[Fehler] Beim Setzen des Benutzerstatus in der Datenbank: {e}")

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        """Wird ausgelöst, wenn ein Mitglied den Server verlässt."""
        print(f"[Event] on_member_remove für {member.name} ({member.id})")
        kicked = False

        try:
            async for entry in member.guild.audit_logs(limit=1, action=discord.AuditLogAction.kick):
                if entry.target.id == member.id:
                    kicked = True
                    break
        except Exception as e:
            print(f"[Fehler] AuditLog konnte nicht gelesen werden: {e}")

        await self.handle_member_leave(member, kicked=kicked)

    @commands.Cog.listener()
    async def on_member_ban(self, guild, member):
        """Wird ausgelöst, wenn ein Mitglied gebannt wird."""
        print(f"[Event] on_member_ban für {member.name} ({member.id})")
        await self.handle_member_leave(member, banned=True)

async def setup(bot):
    await bot.add_cog(MemberEventsController(bot))
