# cogs/view/leave_view.py
import discord

class LeaveView:
    def __init__(self, bot):
        self.bot = bot

    async def send_leave_notification(self, member, channel_id, message):
        """Sendet eine Nachricht in den angegebenen Kanal."""
        try:
            channel = self.bot.get_channel(channel_id)
            if not channel:
                # Fallback: versuche über API
                print(f"[LeaveView] Channel-ID {channel_id} nicht im Cache, versuche fetch_channel...")
                channel = await self.bot.fetch_channel(channel_id)

            if channel:
                print(f"[LeaveView] Sende Nachricht an Channel-ID {channel_id}")
                await channel.send(message)
            else:
                print(f"[LeaveView] Fehler: Channel mit ID {channel_id} konnte nicht gefunden werden.")
        except discord.Forbidden:
            print(f"[LeaveView] Keine Berechtigung, in Channel {channel_id} zu senden.")
        except discord.HTTPException as e:
            print(f"[LeaveView] HTTP-Fehler beim Senden der Nachricht: {e}")
        except Exception as e:
            print(f"[LeaveView] Unerwarteter Fehler beim Senden der Nachricht: {e}")

    async def send_dm(self, member, message):
        """Sendet eine DM an den Benutzer."""
        try:
            await member.send(message)
            print(f"[LeaveView] DM an {member.name} gesendet.")
        except discord.Forbidden:
            print(f"[LeaveView] Konnte {member.name} keine DM senden (vermutlich DMs deaktiviert).")
        except Exception as e:
            print(f"[LeaveView] Fehler beim Senden der DM an {member.name}: {e}")
