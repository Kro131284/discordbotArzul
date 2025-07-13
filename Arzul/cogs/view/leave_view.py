# cogs/view/leave_view.py
import discord

class LeaveView:
    def __init__(self, bot):
        self.bot = bot

    async def send_leave_notification(self, member, channel_id, message):
        """Sendet eine Nachricht in den angegebenen Kanal."""
        if not channel_id:
            print(f"[LeaveView] Fehler: Keine Channel-ID angegeben")
            return

        try:
            channel = self.bot.get_channel(channel_id)
            if not channel:
                print(f"[LeaveView] Channel-ID {channel_id} nicht im Cache, versuche fetch_channel...")
                try:
                    channel = await self.bot.fetch_channel(channel_id)
                except discord.NotFound:
                    print(f"[LeaveView] Channel mit ID {channel_id} existiert nicht.")
                    return
                except discord.Forbidden:
                    print(f"[LeaveView] Keine Berechtigung für Channel {channel_id}.")
                    return

            if channel:
                await channel.send(message)
                print(f"[LeaveView] Nachricht erfolgreich gesendet: {message}")
            else:
                print(f"[LeaveView] Channel konnte nicht gefunden werden: {channel_id}")

        except Exception as e:
            print(f"[LeaveView] Fehler beim Senden der Nachricht: {e}")

    async def send_dm(self, member, message):
        """Sendet eine DM an den Benutzer."""
        if not member:
            return

        try:
            await member.send(message)
            print(f"[LeaveView] DM an {member.name} gesendet")
        except discord.Forbidden:
            print(f"[LeaveView] Konnte keine DM an {member.name} senden (DMs deaktiviert)")
        except Exception as e:
            print(f"[LeaveView] Fehler beim Senden der DM: {e}")
