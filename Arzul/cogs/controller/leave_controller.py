import discord
from discord.ext import commands
from conn_db import create_db_pool
from cogs.model.leave_model import LeaveModel
from cogs.view.leave_view import LeaveView
from dotenv import load_dotenv
import os

load_dotenv()
CHANNEL_ID = int(os.getenv('Leave_ID').strip())
ACTION_CHANNEL_ID = int(os.getenv('Loch_ID').strip())

class MemberEventsController(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.pool = None
        self.model = None
        self.bot.loop.create_task(self.ensure_db_pool())
        self.view = LeaveView(bot)
        print("[LeaveController] Initialisiert.")

    async def ensure_db_pool(self):
        """Stellt sicher, dass der Verbindungspool existiert und initialisiert das Model."""
        if self.pool is None:
            self.pool = await create_db_pool()
            self.model = LeaveModel(self.pool)
            print("[LeaveController] DB-Pool erstellt und Modell geladen.")
        else:
            if self.model is None:
                self.model = LeaveModel(self.pool)
                print("[LeaveController] Modell nach Wiederverbindung des DB-Pools geladen.")

    async def handle_member_leave(self, member, kicked=False, banned=False):
        """Verarbeitet das Verlassen eines Mitglieds."""
        # Debug-Ausgaben (beibehalten, solange sie nützlich sind)
        print(f"[DEBUG] handle_member_leave aufgerufen für {member.name} ({member.id}). Kicked: {kicked}, Banned: {banned}")

        target_channel_id = ACTION_CHANNEL_ID if kicked or banned else CHANNEL_ID
        print(f"[DEBUG] Zielkanal-ID: {target_channel_id}")

        target_channel = self.bot.get_channel(target_channel_id)

        if not target_channel:
            print(f"[FEHLER] Zielkanal mit ID {target_channel_id} nicht gefunden. Ist die ID korrekt oder hat der Bot Berechtigungen?")
            return

        print(f"[DEBUG] Zielkanal gefunden: {target_channel.name} ({target_channel.id}). Versuche Nachricht zu senden...")

        try:
            if kicked:
                await self.view.send_leave_notification(member, target_channel.id, f'{member.name} wurde aus dem Loch gekickt.')
                print(f"[DEBUG] Kick-Nachricht gesendet für {member.name}.")
            elif banned:
                await self.view.send_leave_notification(member, target_channel.id, f'{member.name} wurde aus dem Loch verbannt.')
                print(f"[DEBUG] Bann-Nachricht gesendet für {member.name}.")
            else:
                await self.view.send_leave_notification(member, target_channel.id, f'{member.name} hat das Loch verlassen.')
                print(f"[DEBUG] Normale Austrittsnachricht gesendet für {member.name}.")

                try:
                    await self.view.send_dm(member, f'Schade, dass du unser Loch verlässt, {member.name}. Viel Erfolg auf deiner weiteren Reise . . . Du Ratte!')
                    print(f"[DEBUG] DM gesendet an {member.name}.")
                except discord.Forbidden:
                    print(f"[FEHLER] Konnte keine DM an {member.name} senden. Möglicherweise DMs deaktiviert oder Bot blockiert.")
                except Exception as dm_e:
                    print(f"[FEHLER] Fehler beim Senden der DM an {member.name}: {dm_e}")

        except discord.Forbidden:
            print(f"[FEHLER] Bot hat keine Berechtigung, Nachrichten in Kanal {target_channel.name} ({target_channel.id}) zu senden. Überprüfe die Bot-Rollenberechtigungen.")
        except discord.HTTPException as http_e:
            print(f"[FEHLER] HTTP-Fehler beim Senden der Leave-Nachricht für {member.name}: {http_e}")
        except Exception as e:
            print(f"[FEHLER] Unerwarteter Fehler beim Senden der Leave-Nachricht für {member.name}: {e}")

        # Datenbankeintrag **setzen** (status = 1), wenn Modell verfügbar ist
        if self.model:
            try:
                # Hier wird die Methode zum Setzen des Status aufgerufen
                updated = await self.model.set_user_deleted(member.id)
                if not updated:
                    print(f"[Info] Benutzer {member.id} war nicht in der DB oder konnte nicht aktualisiert werden (Status = 1).")
            except Exception as e:
                print(f"[Fehler] Beim Setzen des Benutzerstatus in der Datenbank für {member.id}: {e}")
        else:
            print("[Info] DB-Model nicht verfügbar. Überspringe DB-Status-Update für Benutzer.")

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        """Wird ausgelöst, wenn ein Mitglied den Server verlässt."""
        print(f"[EVENT] on_member_remove ausgelöst für {member.name} ({member.id}).")
        kicked = False
        if member.guild:
            print(f"[DEBUG] Prüfe Audit Logs für Gilde {member.guild.name}...")
            try:
                async for entry in member.guild.audit_logs(limit=5, action=discord.AuditLogAction.kick):
                    if entry.target and entry.target.id == member.id:
                        kicked = True
                        print(f"[DEBUG] {member.name} wurde als gekickt identifiziert durch Audit Log von {entry.user.name}.")
                        break
                if not kicked:
                    print(f"[DEBUG] {member.name} wurde NICHT als gekickt identifiziert in Audit Logs (normaler Austritt oder andere Aktion).")
            except discord.Forbidden:
                print(f"[FEHLER] Bot hat keine Berechtigung, AuditLogs für Gilde {member.guild.name} zu lesen. Kick-Erkennung könnte fehlschlagen.")
            except Exception as e:
                print(f"[FEHLER] Fehler beim Lesen der AuditLogs für {member.name}: {e}")
        else:
            print(f"[WARNung] Gilde-Objekt für {member.name} nicht verfügbar in on_member_remove. Keine Audit-Log-Prüfung möglich.")

        await self.handle_member_leave(member, kicked=kicked)

    @commands.Cog.listener()
    async def on_member_ban(self, guild, member):
        """Wird ausgelöst, wenn ein Mitglied gebannt wird."""
        print(f"[EVENT] on_member_ban ausgelöst für {member.name} ({member.id}) in Gilde {guild.name}.")
        await self.handle_member_leave(member, banned=True)

async def setup(bot):
    await bot.add_cog(MemberEventsController(bot))