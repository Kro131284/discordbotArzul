import discord
from discord.ui import View, Button, Select, Modal, TextInput
from datetime import datetime
from discord import Interaction

class GameDropdown(Select):
    def __init__(self, bot):
        self.bot = bot
        super().__init__(
            placeholder="Wähle ein Spiel aus",
            options=[],
            custom_id="game_dropdown"
        )

    async def callback(self, interaction: discord.Interaction):
        game_name = self.values[0]
        await interaction.response.defer(ephemeral=True)
        
        # LFG Controller holen
        controller = interaction.client.get_cog("LFGController")
        if controller:
            await controller.show_group_size(interaction, game_name)
        else:
            await interaction.followup.send("Fehler: LFG-System nicht verfügbar.", ephemeral=True)


class GroupSizeDropdown(Select):
    def __init__(self, interaction, bot, game_name):
        self.interaction = interaction
        self.bot = bot
        self.game_name = game_name
        super().__init__(
            placeholder="Wähle die Gruppengröße aus", 
            options=[], 
            custom_id="group_size_dropdown"
        )

    async def callback(self, interaction: Interaction):
        try:
            group_size = int(self.values[0].split()[0])  # Extrahiere die Zahl aus "X Spieler"
            modal = GroupDescriptionModal(interaction, group_size, self.game_name)
            await interaction.response.send_modal(modal)
        except ValueError as e:
            await interaction.response.send_message(f"Fehler bei der Verarbeitung der Gruppengröße: {e}", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"Ein unerwarteter Fehler ist aufgetreten: {e}", ephemeral=True)
# Button-Klassen
class JoinGroupButton(Button):
    def __init__(self, channel, bot):
        self.channel = channel
        self.bot = bot
        super().__init__(label="Ich bin dabei", style=discord.ButtonStyle.success, custom_id="join_group_button")

    async def callback(self, interaction: discord.Interaction):
        group_data = self.bot.temp_channels.get(self.channel.id)

        if not group_data:
            await interaction.response.send_message("Fehler: Diese Gruppe existiert nicht mehr.", ephemeral=True)
            return

        if len(group_data["members"]) >= group_data["group_size"]:
            await interaction.response.send_message("Diese Gruppe ist bereits voll.", ephemeral=True)
            return

        if interaction.user.display_name in group_data["members"]:
            await interaction.response.send_message("Du bist bereits in dieser Gruppe.", ephemeral=True)
            return

        # Benutzer hinzufügen
        group_data["members"].append(interaction.user.display_name)

        # Aktualisiere das Embed
        embed = group_data["message"].embeds[0]
        members_list = "\n".join(group_data["members"]) or "Noch keine Anmeldungen"
        embed.set_field_at(
            0,
            name="Teilnehmer",
            value=members_list,
            inline=False,
        )
        embed.set_footer(
            text=f"{len(group_data['members'])}/{group_data['group_size']} Teilnehmer"
        )

        await group_data["message"].edit(embed=embed)
        await interaction.response.send_message("Du wurdest erfolgreich hinzugefügt!", ephemeral=True)

    async def update_embed(self, group_data):
        embed = group_data["message"].embeds[0]
        members_list = "\n".join(group_data["members"]) or "Noch keine Teilnehmer"
        embed.set_field_at(1, name="Teilnehmer", value=f"{members_list}", inline=False)
        embed.set_footer(text=f"{len(group_data['members'])}/{group_data['group_size']} Teilnehmer")
        await group_data["message"].edit(embed=embed)

    async def check_start_group(self):
        group_data = self.bot.temp_channels.get(self.channel.id)
        if group_data and len(group_data["members"]) == group_data["group_size"]:
            guild = self.channel.guild
            category = discord.utils.get(guild.categories, name="Temporäre Gruppen")
            voice_channel = await guild.create_voice_channel(
                name=group_data["channel_title"], category=category
            )

            await self.channel.send(f"Die Gruppe ist voll! Sprachkanal erstellt: {voice_channel.mention}")
            group_data["voice_channel"] = voice_channel

class LeaveGroupButton(Button):
    def __init__(self, channel, bot):
        self.channel = channel
        self.bot = bot
        super().__init__(label="Gruppe verlassen", style=discord.ButtonStyle.danger)

    async def callback(self, interaction: discord.Interaction):
        group_data = self.bot.temp_channels.get(self.channel.id)
        if not group_data:
            await interaction.response.send_message("Fehler: Diese Gruppe existiert nicht mehr.", ephemeral=True)
            return
        if interaction.user.display_name not in group_data["members"]:
            await interaction.response.send_message("Du bist nicht in dieser Gruppe.", ephemeral=True)
            return

        group_data["members"].remove(interaction.user.display_name)
        group_data["last_active"] = datetime.utcnow()

        await self.update_embed(group_data)
        await interaction.response.send_message("Du hast die Gruppe verlassen.", ephemeral=True)

    async def update_embed(self, group_data):
        embed = group_data["message"].embeds[0]
        members_list = "\n".join(group_data["members"]) or "Noch keine Teilnehmer"
        embed.set_field_at(1, name="Teilnehmer", value=f"{members_list}", inline=False)
        embed.set_footer(text=f"{len(group_data['members'])}/{group_data['group_size']} Teilnehmer")
        await group_data["message"].edit(embed=embed)

class CloseGroupButton(Button):
    def __init__(self, channel, bot):
        self.channel = channel
        self.bot = bot
        super().__init__(label="Schließen", style=discord.ButtonStyle.danger)

    async def callback(self, interaction: discord.Interaction):
        group_data = self.bot.temp_channels.get(self.channel.id)
        if not group_data:
            await interaction.response.send_message("Fehler: Diese Gruppe existiert nicht mehr.", ephemeral=True)
            return

        if interaction.user != group_data["creator"]:
            await interaction.response.send_message(
                "Nur der Ersteller der Gruppe kann den Kanal schließen.", ephemeral=True
            )
            return

        await interaction.response.defer()
        try:
            if "voice_channel" in group_data and group_data["voice_channel"]:
                await group_data["voice_channel"].delete()
            await self.channel.delete()
            del self.bot.temp_channels[self.channel.id]
        except discord.NotFound:
            pass
            
class CreateVoiceChannelButton(Button):
    def __init__(self, channel, bot, member, channel_title):
        self.channel = channel
        self.bot = bot
        self.member = member
        self.channel_title = channel_title
        super().__init__(label="Sprachkanal erstellen", style=discord.ButtonStyle.blurple)

    async def callback(self, interaction: discord.Interaction):
        group_data = self.bot.temp_channels.get(self.channel.id)
        if not group_data:
            await interaction.response.send_message("Fehler: Diese Gruppe existiert nicht mehr.", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True) # Interaktion verzögern
        guild = self.channel.guild
        category = discord.utils.get(guild.categories, name="Temporäre Gruppen")
        voice_channel = await guild.create_voice_channel(
            name=self.channel_title, category=category
        )
        await self.member.move_to(voice_channel)
        await interaction.followup.send(f"Sprachkanal {voice_channel.mention} wurde erstellt.", ephemeral=True)

class JoinGroupView(View):
    def __init__(self, channel, bot, member, channel_title):
        super().__init__(timeout=None)
        self.add_item(JoinGroupButton(channel, bot))
        self.add_item(LeaveGroupButton(channel, bot))
        self.add_item(CloseGroupButton(channel, bot))
        self.add_item(CreateVoiceChannelButton(channel, bot, member, channel_title))

    async def create_voice_channel(self, interaction):
        group_data = self.bot.temp_channels.get(self.channel.id)
        if not group_data:
            await interaction.followup.send("Fehler: Diese Gruppe existiert nicht mehr.", ephemeral=True)
            return
        guild = self.channel.guild
        category = discord.utils.get(guild.categories, name="Temporäre Gruppen")
        voice_channel = await guild.create_voice_channel(
            name=group_data['channel_title'], category=category
        )
        await group_data['creator'].move_to(voice_channel)

class GroupDescriptionModal(Modal):
    def __init__(self, interaction, group_size, game_name):
        super().__init__(title=f"[* {game_name} *] Neue Gruppe")
        self.interaction = interaction
        self.group_size = group_size
        self.game_name = game_name
        
        self.group_name = TextInput(
            label="Gruppenname",
            placeholder="Gib hier den Namen der Gruppe ein",
            max_length=50,
            required=True
        )
        self.start_date = TextInput(
            label="Startdatum (TT.MM.JJJJ)",
            placeholder="z.B. 29.06.2025",
            max_length=10,
            required=True
        )
        self.start_time = TextInput(
            label="Startzeit (HH:MM)",
            placeholder="z.B. 20:00",
            max_length=5,
            required=True
        )
        self.add_item(self.group_name)
        self.add_item(self.start_date)
        self.add_item(self.start_time)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            group_name = self.group_name.value
            start_date = self.start_date.value
            start_time = self.start_time.value
            controller = interaction.client.get_cog("LFGController")
            if not controller:
                await interaction.response.send_message("Fehler: LFG-System nicht verfügbar.", ephemeral=True)
                return
                
            # Gruppe erstellen, jetzt mit Datum und Zeit
            await controller.create_group(
                interaction,
                group_name,
                self.game_name,
                self.group_size,
                start_date,
                start_time
            )
        except Exception as e:
            if not interaction.response.is_done():
                await interaction.response.send_message(f"Fehler beim Erstellen der Gruppe: {str(e)}", ephemeral=True)
            else:
                await interaction.followup.send(f"Fehler beim Erstellen der Gruppe: {str(e)}", ephemeral=True)