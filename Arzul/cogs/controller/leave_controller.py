# cogs/controller/leave_controller.py

import discord
from discord.ext import commands
from datetime import datetime, timezone
import asyncio
import os
from dotenv import load_dotenv

from conn_db import create_db_pool, db_pool
from cogs.model.leave_model import LeaveModel
from cogs.view.leave_view import LeaveView

load_dotenv()
CHANNEL_ID = int(os.getenv("Leave_ID"))

class MemberEventsController(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.channel_id = CHANNEL_ID
        self.db_pool = None
        self.model = None
        self.view = LeaveView(bot, CHANNEL_ID)
        self.recent_bans = set()
        self.bot.loop.create_task(self.ensure_db_pool())
        print("[Controller] Leave-System aktiv.")

    async def ensure_db_pool(self):
        global db_pool
        if db_pool is None:
            db_pool = await create_db_pool()
        self.db_pool = db_pool
        self.model = LeaveModel(db_pool)

    def mark_recent_ban(self, user_id: int, ttl: int = 10):
        """Merkt sich eine gebannte User-ID für kurze Zeit."""
        self.recent_bans.add(user_id)
        asyncio.create_task(self._unmark_recent_ban(user_id, ttl))

    async def _unmark_recent_ban(self, user_id: int, ttl: int):
        await asyncio.sleep(ttl)
        self.recent_bans.discard(user_id)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        if member.id in self.recent_bans:
            print(f"[INFO] Entferne Doppelmeldung (Ban) für {member.name}")
            return

        print(f"[EVENT] on_member_remove für {member.name}")
        kicked = False
        now = datetime.now(timezone.utc)
        if member.name != member.display_name:
            username = f"{member.name} ({member.display_name})"
        else:
            username = member.name

        try:
            await asyncio.sleep(1)  # AuditLog braucht manchmal etwas Zeit

            async for entry in member.guild.audit_logs(limit=5, action=discord.AuditLogAction.kick):
                time_diff = (now - entry.created_at).total_seconds()
                if entry.target.id == member.id and time_diff < 10:
                    kicked = True
                    print(f"[INFO] Kick erkannt: {entry.user.name} ({time_diff:.2f}s alt)")
                    break
        except Exception as e:
            print(f"[AuditLog ERROR] {e}")

        msg = f"{username} wurde aus dem Loch gekickt." if kicked else f"{username} hat das Loch verlassen."
        await self.view.send_leave_message(member, msg)
        await self.model.set_user_deleted(member.id)

    @commands.Cog.listener()
    async def on_member_ban(self, guild, member):
        print(f"[EVENT] on_member_ban für {member.name}")
        self.mark_recent_ban(member.id)  # 🛡️ markiere User sofort
        if member.name != member.display_name:
            username = f"{member.name} ({member.display_name})"
        else:
            username = member.name

        msg = f"{username} wurde aus dem Loch verbannt."
        await self.view.send_leave_message(member, msg)
        await self.model.set_user_deleted(member.id)

async def setup(bot):
    await bot.add_cog(MemberEventsController(bot))
