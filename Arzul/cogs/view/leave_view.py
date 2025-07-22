# cogs/view/leave_view.py

class LeaveView:
    def __init__(self, bot):
        self.bot = bot

    async def send_dm(self, member, message):
        try:
            await member.send(message)
            print(f"[View] DM an {member.name} gesendet.")
        except Exception as e:
            print(f"[View] Konnte keine DM senden an {member.name}: {e}")

    async def send_leave_notification(self, member, channel_id, message):
        channel = self.bot.get_channel(channel_id)
        if channel:
            await channel.send(message)
            print(f"[View] Nachricht im Channel {channel_id}: {message}")
        else:
            print(f"[View] Channel mit ID {channel_id} nicht gefunden.")
