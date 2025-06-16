import discord
from discord.ext import commands
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()  # Lade die Umgebungsvariablen aus der .env-Datei

VOICECHANNEL_3_ID = os.getenv('VoiceChannel_ID3')
VOICECHANNEL_5_ID = os.getenv('VoiceChannel_ID5')
VOICECHANNEL_6_ID = os.getenv('VoiceChannel_ID6')
VOICECHANNEL_12_ID = os.getenv('VoiceChannel_ID12')
VOICECHANNEL_Raid_ID = os.getenv('VoiceChannel_IDRaid')


# Debug-Ausgabe um sicherzustellen, dass die Variablen geladen wurden
print(f"VoiceChannel_3_ID: {VOICECHANNEL_3_ID}")
print(f"VoiceChannel_5_ID: {VOICECHANNEL_5_ID}")	
print(f"VoiceChannel_6_ID: {VOICECHANNEL_6_ID}")
print(f"VoiceChannel_12_ID: {VOICECHANNEL_12_ID}")
print(f"VoiceChannel_Raid_ID: {VOICECHANNEL_Raid_ID}")  # Debugging für den neuen Kanal

class VoiceChannelController(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.channel_3_people = int(VOICECHANNEL_3_ID)
        self.channel_5_people = int(VOICECHANNEL_5_ID)
        self.channel_6_people = int(VOICECHANNEL_6_ID)
        self.channel_12_people = int(VOICECHANNEL_12_ID)
        self.channel_Raid_people = int(VOICECHANNEL_Raid_ID)
        self.group_channels = []
        self.onleave_channels = []

    async def create_group_channel(self, member, limit, category):
        """Erstellt einen neuen Sprachkanal und bewegt den Benutzer hinein."""
        print(f"Erstelle einen neuen Sprachkanal für {member.display_name} mit Limit {limit}")
        new_channel = await category.create_voice_channel(f"{member.name}'s Bau")
        if limit > 0:
            await new_channel.edit(user_limit=limit)
        elif limit == 40:
            await new_channel.edit(user_limit=40)
        self.group_channels.append(new_channel.id)
        self.onleave_channels.append(new_channel.id)

        # Bewege den Benutzer in den neuen Kanal
        await member.move_to(new_channel)
        print(f"Channel {new_channel.name} wurde erstellt und {member.display_name} wurde verschoben.")

        # Überprüfen, ob der Benutzer erfolgreich verschoben wurde
        await asyncio.sleep(2)
        if member.voice and member.voice.channel != new_channel:
            print(f"{member.display_name} wurde nicht erfolgreich verschoben. Versuch erneut...")
            await asyncio.sleep(5)
            await member.move_to(new_channel)
            print(f"Versuch erneut: {member.display_name} wurde in den Kanal {new_channel.name} verschoben.")
            
    async def check_before_channels(self, before_channel):
        """Überprüft, ob ein Sprachkanal leer ist und gelöscht werden kann."""
        if before_channel and before_channel.id in self.onleave_channels:
            # Verzögerung, um sicherzustellen, dass der Kanal wirklich leer ist
            await asyncio.sleep(5)
            if len(before_channel.members) == 0:
                if before_channel.id in self.onleave_channels:
                    self.onleave_channels.remove(before_channel.id)
                    self.group_channels.remove(before_channel.id)
                    await before_channel.delete()
                    print(f"Channel {before_channel.name} wurde gelöscht, da er leer war.")
                    
    async def check_after_channels(self, member, after_channel):
        """Überprüft, ob ein Benutzer in einen bestimmten Kanal beigetreten ist."""
        if after_channel:
            if after_channel.id == self.channel_3_people:
                await self.create_group_channel(member, 3, after_channel.category)
            elif after_channel.id == self.channel_5_people:
                await self.create_group_channel(member, 5, after_channel.category)
            elif after_channel.id == self.channel_6_people:
                await self.create_group_channel(member, 6, after_channel.category)
            elif after_channel.id == self.channel_12_people:
                await self.create_group_channel(member, 12, after_channel.category)
            elif after_channel.id == self.channel_Raid_people:
                await self.create_group_channel(member, 40, after_channel.category)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        """Listener für Sprachzustandsaktualisierungen."""
        # Überprüfe, ob der Benutzer den Kanal verlassen hat
        await self.check_before_channels(before.channel)
        # Überprüfe, ob der Benutzer in einen neuen Kanal beigetreten ist
        await self.check_after_channels(member, after.channel)

    @commands.command(name="createchannel")
    async def create_channel_command(self, ctx, limit: int):
        """Befehl, um einen neuen Sprachkanal zu erstellen und den Benutzer zu verschieben."""
        category = discord.utils.get(ctx.guild.categories, name="Voice Channels")
        if category is None:
            category = await ctx.guild.create_category("Voice Channels")
        await self.create_group_channel(ctx.author, limit, category)
        await ctx.send(f"Channel wurde erstellt und {ctx.author.display_name} wurde verschoben.")

async def setup(bot):
    await bot.add_cog(VoiceChannelController(bot))
