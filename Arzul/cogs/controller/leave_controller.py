import discord
from discord.ext import commands
from conn_db import create_db_pool, db_pool
from cogs.model.leave_model import LeaveModel
from cogs.view.leave_view import LeaveView
from dotenv import load_dotenv
import os
import asyncio

load_dotenv()
CHANNEL_ID = int(os.getenv('Leave_ID'))
ACTION_CHANNEL_ID = int(os.getenv('Loch_ID'))

class MemberEventsController(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.pool = None
        self.model = None
        self.view = LeaveView(bot)
        self.bot.loop.create_task(self.ensure_db_pool())
        print("[LeaveController] Initialisiert.")

    async def ensure_db_pool(self):
        """Stellt sicher, dass der Verbindungspool existiert und initialisiert das Model."""
        global db_pool
        if db_pool is None:
            print("[LeaveController] Erstelle neuen Datenbankpool...")
            db_pool = await create_db_pool()
        self.pool = db_pool
        self.model = LeaveModel(self.pool)
        print("[LeaveController] DB-Pool erstellt und Modell geladen.")

    async def handle_member_leave(self, member, kicked=False, banned=False):
        """Verarbeitet das Verlassen eines Mitglieds."""
        print(f"[DEBUG] handle_member_leave für {member.name} ({member.id}). Kicked: {kicked}, Banned: {banned}")
        
        try:
            # Channel-ID basierend auf dem Event-Typ wählen
            channel_id = ACTION_CHANNEL_ID if (kicked or banned) else CHANNEL_ID
            
            # Nachricht basierend auf dem Event-Typ erstellen
            if kicked:
                message = f'{member.name} wurde aus dem Loch gekickt.'
            elif banned:
                message = f'{member.name} wurde aus dem Loch verbannt.'
            else:
                message = f'{member.name} hat das Loch verlassen.'
                # Bei freiwilligem Leave eine DM senden
                try:
                    await self.view.send_dm(member, f'Schade, dass du unser Loch verlässt, {member.name}. Viel Erfolg auf deiner weiteren Reise . . . Du Ratte!')
                except:
                    print(f"[INFO] Konnte keine DM an {member.name} senden.")

            # Nachricht im Channel senden
            await self.view.send_leave_notification(member, channel_id, message)

            # Datenbank-Status aktualisieren
            if self.model:
                await self.model.set_user_deleted(member.id)
            
        except Exception as e:
            print(f"[ERROR] Fehler in handle_member_leave: {e}")

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        """Wird ausgelöst, wenn ein Mitglied den Server verlässt."""
        print(f"[EVENT] on_member_remove für {member.name}")
        
        # Kleine Verzögerung für das Audit Log
        await asyncio.sleep(1)
        
        kicked = False
        if member.guild:
            try:
                async for entry in member.guild.audit_logs(limit=5, action=discord.AuditLogAction.kick):
                    if entry.target.id == member.id:
                        time_diff = (discord.utils.utcnow() - entry.created_at).total_seconds()
                        if time_diff < 5:  # Nur Kicks der letzten 5 Sekunden
                            kicked = True
                            break
            except Exception as e:
                print(f"[ERROR] Fehler beim Lesen der Audit Logs: {e}")

        await self.handle_member_leave(member, kicked=kicked)

    @commands.Cog.listener()
    async def on_member_ban(self, guild, member):
        """Wird ausgelöst, wenn ein Mitglied gebannt wird."""
        print(f"[EVENT] on_member_ban für {member.name}")
        await self.handle_member_leave(member, banned=True)

async def setup(bot):
    await bot.add_cog(MemberEventsController(bot))