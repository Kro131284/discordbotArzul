# cogs/view/leave_view.py

import discord

class LeaveView:
    def __init__(self, bot, channel_id: int):
        self.bot = bot
        self.channel_id = channel_id

    async def send_leave_message(self, member: discord.Member, message: str):
        """Sendet eine Nachricht in den Leave-Channel."""
        channel = self.bot.get_channel(self.channel_id)
        if not channel:
            print(f"[VIEW ERROR] Channel mit ID {self.channel_id} nicht gefunden.")
            return

        try:
            await channel.send(message)
            print(f"[VIEW] Nachricht gesendet: {message}")
        except Exception as e:
            print(f"[VIEW ERROR] Nachricht konnte nicht gesendet werden: {e}")
