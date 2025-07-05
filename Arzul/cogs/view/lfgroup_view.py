import discord
from discord.ui import View, Button, Select, Modal, TextInput
from datetime import datetime
from discord import Interaction

# Define the category name, assuming it's consistent across files.
CATEGORY_NAME = "Temporäre Gruppen"

class GameDropdown(Select):
    def __init__(self, bot):
        self.bot = bot
        super().__init__(
            placeholder="Wähle ein Spiel aus",
            options=[],
            custom_id="game_dropdown"
        )

    async def callback(self, interaction: discord.Interaction):
        # Der Callback des Dropdowns wird im Controller zugewiesen (game_dropdown_callback).
        # Diese Methode wird also nicht direkt aufgerufen, sondern dient nur als Blaupause.
        pass


class GroupSizeDropdown(Select):
    def __init__(self, original_interaction: Interaction, bot, game_name: str):
        # Die ursprüngliche Interaktion ist hier nicht direkt notwendig,
        # da der Callback dieses Dropdowns eine NEUE Interaktion ist.
        # Wichtig ist, dass game_name korrekt gespeichert wird.
        self.bot = bot
        self.game_name = game_name
        super().__init__(
            placeholder="Wähle die Gruppengröße aus", options=[], custom_id="group_size_dropdown"
        )

    async def callback(self, interaction: Interaction):
        # Wichtig: Die Interaktion des Dropdown-Klicks muss beantwortet werden.
        # Wir senden ein Modal, was eine gültige Antwort ist.
        group_size = int(interaction.data['values'][0])
        
        # Holen des LFGController-Cogs
        # WICHTIG: Hier muss der korrekte Klassenname des Cogs stehen!
        controller = interaction.client.get_cog("LFGController")

        if controller:
            # Erstelle das Modal und sende es als Antwort auf die Dropdown-Interaktion
            modal = GroupDescriptionModal(interaction, group_size, self.game_name)
            await interaction.response.send_modal(modal)
        else:
            # Falls der Controller nicht gefunden wird, sende eine Fehlermeldung
            print(f"[ERROR] LFGController nicht gefunden in GroupSizeDropdown callback.")
            await interaction.response.send_message(
                "Ein interner Fehler ist aufgetreten (LFGController nicht gefunden). Bitte versuche es später erneut.", 
                ephemeral=True
            )


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

        # Überprüfen, ob die Gruppe bereits voll ist
        if len(group_data["members"]) >= group_data["group_size"]:
            await interaction.response.send_message("Diese Gruppe ist bereits voll.", ephemeral=True)
            return

        # Überprüfen, ob der Benutzer bereits in der Gruppe ist (durch ID für Robustheit)
        if interaction.user.id in [member.id for member in group_data["members"]]:
            await interaction.response.send_message("Du bist bereits in dieser Gruppe.", ephemeral=True)
            return

        # Benutzer hinzufügen (Speichern des Member-Objekts ist besser)
        group_data["members"].append(interaction.user)
        group_data["last_active"] = datetime.utcnow()

        # Aktualisiere das Embed mit den neuen Mitgliedern
        await self.update_embed(group_data)
        
        await interaction.response.send_message("Du wurdest erfolgreich hinzugefügt!", ephemeral=True)

        # Überprüfen, ob die Gruppe jetzt voll ist und den Sprachkanal starten
        await self.check_start_group(group_data)

    async def update_embed(self, group_data):
        embed = group_data["message"].embeds[0]
        # Anzeige der Mitgliedernamen (display_name), aber in der Liste sind Member-Objekte
        members_list = "\n".join([m.display_name for m in group_data["members"]]) or "Noch keine Anmeldungen"
        
        # Stellen Sie sicher, dass Sie den richtigen Feldindex verwenden (0, wenn es das erste Feld ist)
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

    async def check_start_group(self, group_data):
        # Erstellt den Sprachkanal, wenn die Gruppe voll ist UND er noch nicht existiert.
        if len(group_data["members"]) == group_data["group_size"]:
            guild = self.channel.guild
            category = discord.utils.get(guild.categories, name=CATEGORY_NAME)
            
            # Nur erstellen, wenn voice_channel noch nicht in group_data oder None ist
            if not group_data.get("voice_channel"):
                voice_channel = await guild.create_voice_channel(
                    name=group_data["channel_title"], category=category
                )
                group_data["voice_channel"] = voice_channel # Speichern des VoiceChannel-Objekts
                await self.channel.send(f"Die Gruppe ist voll! Sprachkanal erstellt: {voice_channel.mention}")
            else:
                # Falls er schon existiert (z.B. vom Ersteller erstellt), informiere einfach
                await self.channel.send(f"Die Gruppe ist voll! Tretet dem Sprachkanal bei: {group_data['voice_channel'].mention}")


class LeaveGroupButton(Button):
    def __init__(self, channel, bot):
        self.channel = channel
        self.bot = bot
        super().__init__(label="Gruppe verlassen", style=discord.ButtonStyle.danger, custom_id="leave_group_button")

    async def callback(self, interaction: discord.Interaction):
        group_data = self.bot.temp_channels.get(self.channel.id)
        if not group_data:
            await interaction.response.send_message("Fehler: Diese Gruppe existiert nicht mehr.", ephemeral=True)
            return
        
        # Benutzer anhand der ID finden und entfernen
        member_to_remove = None
        for member in group_data["members"]:
            if member.id == interaction.user.id:
                member_to_remove = member
                break

        if member_to_remove is None:
            await interaction.response.send_message("Du bist nicht in dieser Gruppe.", ephemeral=True)
            return

        group_data["members"].remove(member_to_remove)
        group_data["last_active"] = datetime.utcnow()

        await self.update_embed(group_data)
        await interaction.response.send_message("Du hast die Gruppe verlassen.", ephemeral=True)

    async def update_embed(self, group_data):
        embed = group_data["message"].embeds[0]
        members_list = "\n".join([m.display_name for m in group_data["members"]]) or "Noch keine Teilnehmer"
        embed.set_field_at(
            0, # Stellen Sie sicher, dass der Index korrekt ist
            name="Teilnehmer", 
            value=f"{members_list}", 
            inline=False
        )
        embed.set_footer(text=f"{len(group_data['members'])}/{group_data['group_size']} Teilnehmer")
        await group_data["message"].edit(embed=embed)


class CloseGroupButton(Button):
    def __init__(self, channel, bot):
        self.channel = channel
        self.bot = bot
        super().__init__(label="Schließen", style=discord.ButtonStyle.danger, custom_id="close_group_button")

    async def callback(self, interaction: discord.Interaction):
        group_data = self.bot.temp_channels.get(self.channel.id)
        if not group_data:
            await interaction.response.send_message("Fehler: Diese Gruppe existiert nicht mehr.", ephemeral=True)
            return

        # Nur der Ersteller kann die Gruppe schließen
        if interaction.user.id != group_data["creator"].id: # Vergleich der IDs für Robustheit
            await interaction.response.send_message(
                "Nur der Ersteller der Gruppe kann den Kanal schließen.", ephemeral=True
            )
            return

        await interaction.response.defer() # Interaktion verzögern, da Kanal löschen Zeit braucht
        try:
            # Voice-Kanal löschen, falls vorhanden
            if "voice_channel" in group_data and group_data["voice_channel"]:
                # Prüfen, ob der Kanal noch existiert, bevor versucht wird zu löschen
                if discord.utils.get(self.channel.guild.voice_channels, id=group_data["voice_channel"].id):
                    await group_data["voice_channel"].delete()
            
            # Text-Kanal löschen, falls vorhanden
            if discord.utils.get(self.channel.guild.text_channels, id=self.channel.id):
                await self.channel.delete()

            # Gruppendaten aus dem Bot entfernen
            if self.channel.id in self.bot.temp_channels:
                del self.bot.temp_channels[self.channel.id]
        except discord.NotFound:
            # Kanal könnte bereits manuell gelöscht worden sein
            pass
        except Exception as e:
            await interaction.followup.send(f"Ein Fehler ist beim Schließen aufgetreten: {e}", ephemeral=True)
            print(f"[ERROR] Fehler beim Schließen der Gruppe {self.channel.id}: {e}") # Loggen für Debugging


class CreateVoiceChannelButton(Button):
    def __init__(self, channel, bot, member, channel_title):
        self.channel = channel
        self.bot = bot
        self.creator_member = member # Speichern des Ersteller-Member-Objekts
        self.channel_title = channel_title
        super().__init__(label="Sprachkanal erstellen", style=discord.ButtonStyle.blurple, custom_id="create_vc_button")

    async def callback(self, interaction: discord.Interaction):
        group_data = self.bot.temp_channels.get(self.channel.id)
        if not group_data:
            await interaction.response.send_message("Fehler: Diese Gruppe existiert nicht mehr.", ephemeral=True)
            return
        
        # Nur der Ersteller darf den Sprachkanal per Button erstellen
        if interaction.user.id != self.creator_member.id:
            await interaction.response.send_message("Nur der Ersteller der Gruppe kann den Sprachkanal erstellen.", ephemeral=True)
            return

        # Wenn bereits ein Sprachkanal existiert, informiere den Benutzer
        if "voice_channel" in group_data and group_data["voice_channel"]:
            await interaction.response.send_message(f"Der Sprachkanal existiert bereits: {group_data['voice_channel'].mention}", ephemeral=True)
            return
            
        await interaction.response.defer(ephemeral=True) # Interaktion verzögern
        guild = self.channel.guild
        category = discord.utils.get(guild.categories, name=CATEGORY_NAME)
        
        # Falls die Kategorie nicht existiert, erstelle sie
        if not category:
            category = await guild.create_category(CATEGORY_NAME)

        voice_channel = await guild.create_voice_channel(
            name=self.channel_title, category=category
        )
        group_data["voice_channel"] = voice_channel # Speichern des VoiceChannel-Objekts

        # Versuche, den Ersteller in den neuen Sprachkanal zu verschieben, falls er sich in einem Sprachkanal befindet
        if self.creator_member.voice and self.creator_member.voice.channel:
            await self.creator_member.move_to(voice_channel)
            await interaction.followup.send(f"Sprachkanal {voice_channel.mention} wurde erstellt und du wurdest verschoben.", ephemeral=True)
        else:
            await interaction.followup.send(f"Sprachkanal {voice_channel.mention} wurde erstellt. Du bist in keinem Sprachkanal, um verschoben zu werden.", ephemeral=True)


class JoinGroupView(View):
    def __init__(self, channel, bot, member, channel_title):
        super().__init__(timeout=None)
        self.channel = channel
        self.bot = bot
        self.add_item(JoinGroupButton(channel, bot))
        self.add_item(LeaveGroupButton(channel, bot))
        self.add_item(CloseGroupButton(channel, bot))
        self.add_item(CreateVoiceChannelButton(channel, bot, member, channel_title))

    async def create_voice_channel(self, interaction: Interaction):
        # Dies wird von LFGController.create_group aufgerufen, um den Initial-VC zu erstellen
        group_data = self.bot.temp_channels.get(self.channel.id)
        if not group_data:
            # Dies sollte hier nicht passieren, da es direkt nach der Kanalkreation aufgerufen wird
            print(f"[ERROR] Gruppe nicht gefunden für Sprachkanalerstellung in JoinGroupView.")
            return
        
        guild = self.channel.guild
        category = discord.utils.get(guild.categories, name=CATEGORY_NAME)
        
        if not category:
            category = await guild.create_category(CATEGORY_NAME)

        # Erstelle den Voice Channel nur, wenn er noch nicht existiert
        if "voice_channel" not in group_data or group_data["voice_channel"] is None:
            voice_channel = await guild.create_voice_channel(
                name=group_data['channel_title'], category=category
            )
            group_data["voice_channel"] = voice_channel # Speichern des VoiceChannel-Objekts
        else:
            voice_channel = group_data["voice_channel"] # Verwende den bereits vorhandenen

        # Verschiebe den Ersteller in den Sprachkanal, wenn er in einem Sprachkanal ist
        creator = group_data['creator']
        if creator and creator.voice and creator.voice.channel != voice_channel:
            await creator.move_to(voice_channel)
        # Keine Notwendigkeit, hier eine response zu senden, da dies Teil der create_group-Sequenz ist.


class GroupDescriptionModal(Modal):
    group_name_input = TextInput(
        label="Gruppenname",
        placeholder="Gib hier den Namen der Gruppe ein",
        max_length=50,
        required=True
    )

    def __init__(self, interaction_for_modal: Interaction, group_size: int, game_name: str):
        # Der Titel des Modals wird dynamisch gesetzt
        super().__init__(title=f"[{game_name}] Neue Gruppe")
        self.interaction_for_modal = interaction_for_modal # Die Interaktion, die das Modal ausgelöst hat
        self.group_size = group_size
        self.game_name = game_name
        
        self.add_item(self.group_name_input)

    async def on_submit(self, interaction: discord.Interaction):
        group_name = self.group_name_input.value
        
        # Holen des LFGController-Cogs
        # WICHTIG: Hier muss der korrekte Klassenname des Cogs stehen!
        controller = interaction.client.get_cog("LFGController")

        if controller:
            # Rufe die create_group Methode im Controller auf
            # Die Interaktion hier ist die SUBMIT-Interaktion des Modals.
            await controller.create_group(interaction, group_name, self.game_name, self.group_size)
        else:
            print(f"[ERROR] LFGController nicht gefunden in GroupDescriptionModal on_submit.")
            await interaction.followup.send( # followup, da das Modal bereits eine Antwort gesendet hat
                "Es ist ein Fehler aufgetreten. Die Gruppe konnte nicht erstellt werden (Controller nicht gefunden).", 
                ephemeral=True
            )