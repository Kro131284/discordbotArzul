# cogs/controller/member_events_controller.py

import discord
from discord.ext import commands
import asyncio
from datetime import datetime
from conn_db import create_db_pool, db_pool
from cogs.model.leave_model import LeaveModel
from cogs.view.leave_view import LeaveView
import os
from dotenv import load_dotenv

load_dotenv()
LEAVE_CHANNEL_ID = int(os.getenv('Leave_ID'))


class MemberEventsController(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.model = None
        self.view = LeaveView(bot)
        self.bot.loop.create_task(self.setup_components())

    async def setup_components(self):
        global db_pool
        if db_pool is None:
            db_pool = await create_db_pool()
        self.model = LeaveModel(db_pool)
        print("[Controller] Komponenten initialisiert.")

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        print(f"[EVENT] on_member_remove für {member.name} ({member.id})")
        kicked = False

        await asyncio.sleep(2)  # Verzögerung für verlässliche AuditLogs
        now = datetime.utcnow()

        try:
            async for entry in member.guild.audit_logs(limit=5, action=discord.AuditLogAction.kick):
                print(f"[DEBUG] Kick-Eintrag geprüft: Target={entry.target}, User={entry.user}, Zeit={entry.created_at}")

                # Kick nur akzeptieren, wenn er sehr kürzlich war (z. B. unter 10 Sekunden her)
                if entry.target.id == member.id and (now - entry.created_at).total_seconds() < 10:
                    kicked = True
                    print(f"[DEBUG] Kick erkannt von {entry.user.name} ({entry.user.id})")
                    break
        except Exception as e:
            print(f"[ERROR] Fehler beim Lesen der Audit Logs: {e}")

        # Kick-Meldung senden
        await self.send_leave_notifications(member, kicked=kicked)

        # DM nur bei freiwilligem Leave
        if not kicked:
            try:
                await member.send(f'Schade, dass du unser Loch verlässt, {member.name}. Viel Erfolg auf deiner weiteren Reise . . . Du Ratte!')
            except discord.Forbidden:
                print(f"[INFO] Konnte {member.name} keine DM senden (vermutlich blockiert).")

        # Status in der Datenbank setzen
        await self.set_user_deleted(member.id)

    @commands.Cog.listener()
    async def on_member_ban(self, guild, member):
        print(f"[Controller] on_member_ban: {member.name}")
        await self.view.send_leave_notification(member, LEAVE_CHANNEL_ID, f"{member.name} wurde aus dem Loch verbannt.")
        if self.model:
            await self.model.set_user_deleted(member.id)

async def setup(bot):
    await bot.add_cog(MemberEventsController(bot))
