from discord.ext import commands
from cogs.model.voicemonitor_model import UserActivity
from cogs.view.voicemonitor_view import voice_join_notification
from dotenv import load_dotenv
import os
import time

load_dotenv()
LochID = os.getenv("Systemmeldung_ID")

COOLDOWN_TIME = 1800  # 30 Minuten in Sekunden

class VoiceMonitor(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.recent_joins = {}  # Speichert den letzten Beitritt (user_id: timestamp)

        if LochID is None:
            print(f"❌ Fehler: Umgebungsvariable LochID ist nicht gesetzt!")
            return

        try:
            self.LochID_int = int(LochID)
        except ValueError:
            print(f"❌ Fehler: Umgebungsvariable LochID ist kein gültiger Integer!")
            return

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        """Wird ausgelöst, wenn ein User einem Voice-Channel beitritt oder ihn verlässt."""

        current_time = time.time()

        # === Falls jemand einem neuen Voice-Channel beitritt ===
        if before.channel is None and after.channel is not None:
            last_join_time = self.recent_joins.get(member.id, 0)

            # Prüfen, ob der Cooldown aktiv ist
            if current_time - last_join_time < COOLDOWN_TIME:
                return  

            # Prüfen, ob der User alleine im Voice-Channel ist
            if len(after.channel.members) == 1:
                self.recent_joins[member.id] = current_time  # Cooldown speichern
                await self.send_notification(member, after.channel)

        # === Falls jemand einen Voice-Channel verlässt ===
        if before.channel is not None and after.channel is None:
            # Prüfen, ob jemand im alten Kanal alleine zurückbleibt
            if len(before.channel.members) == 1:
                last_user = before.channel.members[0]
                last_join_time = self.recent_joins.get(last_user.id, 0)

                # Prüfen, ob der Cooldown aktiv ist
                if current_time - last_join_time >= COOLDOWN_TIME:
                    self.recent_joins[last_user.id] = current_time  # Cooldown speichern
                    await self.send_notification(last_user, before.channel)

    async def send_notification(self, user, channel):
        """Sendet eine Nachricht in den Textkanal."""
        activity = UserActivity(user.id, channel.id)
        text_channel = self.bot.get_channel(self.LochID_int)

        if text_channel:
            message = voice_join_notification(user.mention, channel)
            await text_channel.send(message)
        else:
            print(f"❌ Fehler: Textkanal mit ID {LochID} nicht gefunden!")

async def setup(bot):
    await bot.add_cog(VoiceMonitor(bot))

