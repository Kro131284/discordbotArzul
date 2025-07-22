import discord
from discord.ext import commands, tasks
from discord import app_commands
from zoneinfo import ZoneInfo
from datetime import datetime, timedelta, timezone
from cogs.model.raidplaner_model import EventManager, Event # Assuming Event class has notification_sent attribute
from cogs.view.raidplaner_view import EventView
import asyncio
import traceback # Import traceback for detailed error logging
import os # Import os
from dotenv import load_dotenv # Import load_dotenv

# Lade die Umgebungsvariablen aus der .env Datei
load_dotenv()

class EventPlanner(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # EventManager lädt jetzt automatisch beim Initialisieren
        # Stelle sicher, dass das data-Verzeichnis existiert
        data_dir = "data"
        if not os.path.exists(data_dir):
             try:
                 os.makedirs(data_dir)
                 print(f"Verzeichnis '{data_dir}' erstellt.")
             except OSError as e:
                 print(f"FEHLER beim Erstellen des Verzeichnisses '{data_dir}': {e}")
                 # Handle den Fehler ggf. anders, z.B. Abbruch
        self.event_manager = EventManager(filename=os.path.join(data_dir, "events.json")) # Pfad korrekt zusammengesetzt
        self.event_view = EventView(
            tank_emoji="<:tank:1292758103128936468>",
            healer_emoji="<:healer:1292758088197341235>",
            dps_emoji="<:dps:1292758071894085682>"
        )
        # Lese die Voice Channel ID aus der .env Datei
        try:
            # Annahme: Du möchtest die ID von "VoiceChannel" verwenden
            self.default_event_voice_channel_id = int(os.getenv("VoiceChannel"))
            print(f"Standard Voice Channel ID für Events geladen: {self.default_event_voice_channel_id}")
        except (TypeError, ValueError):
            print("WARNUNG: 'VoiceChannel' ID in .env nicht gefunden oder ungültig. Events werden ohne spezifischen Voice Channel erstellt.")
            self.default_event_voice_channel_id = None

        self.countdown_updater.start()

    # --- Event Modal ---
    class EventModal(discord.ui.Modal, title="Event Planung"):
        def __init__(self, cog, interaction):
            super().__init__()
            self.cog = cog
            # Store interaction details needed later
            self.guild_id = interaction.guild_id
            self.channel_id = interaction.channel_id
            self.user_id = interaction.user.id

            self.event_name = discord.ui.TextInput(label="Event Titel", placeholder="Geben Sie den Titel des Events ein")
            self.event_date = discord.ui.TextInput(label="Datum (TT.MM.JJJJ)", placeholder="24.10.2024", max_length=10)
            self.event_time = discord.ui.TextInput(label="Uhrzeit (HH:MM)", placeholder="20:30", max_length=5)
            self.event_description = discord.ui.TextInput(label="Beschreibung", placeholder="Beschreibung des Events", style=discord.TextStyle.paragraph)

            self.add_item(self.event_name)
            self.add_item(self.event_date)
            self.add_item(self.event_time)
            self.add_item(self.event_description)

        async def on_submit(self, interaction: discord.Interaction):
            # Defer the response immediately
            await interaction.response.defer(ephemeral=True, thinking=True)
            print("EventModal.on_submit called")

            # --- Date/Time Parsing and Validation ---
            try:
                datetime_str = f"{self.event_date.value} {self.event_time.value}"
                datetime_format = "%d.%m.%Y %H:%M"
                naive_dt = datetime.strptime(datetime_str, datetime_format)
                berlin_tz = ZoneInfo("Europe/Berlin")
                event_datetime = naive_dt.replace(tzinfo=berlin_tz)
                event_end_time = event_datetime + timedelta(hours=2) # Assuming event duration is 2 hours

            except ValueError:
                print(f"Error parsing date/time: {self.event_date.value} {self.event_time.value}")
                await interaction.followup.send("Ungültiges Datum oder Uhrzeitformat. Bitte das Format TT.MM.JJJJ HH:MM verwenden (z.B. 24.10.2024 20:30).", ephemeral=True)
                return
            except Exception as e:
                print(f"Unexpected error during date/time processing: {e}")
                traceback.print_exc()
                await interaction.followup.send(f"Ein unerwarteter Fehler bei der Datums-/Uhrzeitverarbeitung ist aufgetreten: {e}", ephemeral=True)
                return

            # --- Past Date Check ---
            now = datetime.now(ZoneInfo("Europe/Berlin"))
            if event_datetime < now:
                await interaction.followup.send("Das Eventdatum liegt in der Vergangenheit. Bitte geben Sie ein zukünftiges Datum an.", ephemeral=True)
                return

            # --- Event Creation Logic ---
            message = None
            try:
                # --- Get guild object ---
                guild = interaction.guild
                if not guild:
                     print(f"Error: Guild {self.guild_id} not found in on_submit.")
                     await interaction.followup.send("Fehler: Der Server konnte nicht gefunden werden.", ephemeral=True)
                     return
                # --- END ---

                # 1. Create the initial embed and view
                temp_event_for_embed = Event(self.event_name.value, event_datetime, self.event_description.value)
                # --- Pass guild and bot ---
                initial_embed = await self.cog.event_view.create_event_embed(temp_event_for_embed, guild, self.cog.bot)
                # --- END ---
                initial_view = EventButtons(self.cog, temp_event_for_embed)

                # 2. Send the message to the channel
                channel = guild.get_channel(self.channel_id) # Use guild object
                if not channel:
                    print(f"Error: Channel {self.channel_id} not found in guild {guild.id}")
                    await interaction.followup.send("Fehler: Der Kanal zum Senden der Eventnachricht wurde nicht gefunden.", ephemeral=True)
                    return

                message = await channel.send(embed=initial_embed, view=initial_view)
                print(f"Event message sent: {message.id} in channel {channel.id}")

                # 3. Create the persistent Event object in the manager
                event = self.cog.event_manager.create_event(
                    title=self.event_name.value,
                    date=event_datetime,
                    description=self.event_description.value,
                    message_id=message.id
                )
                event.channel_id = channel.id
                if not hasattr(event, 'notification_sent'):
                    event.notification_sent = False

                # 4. Update the view with the *persistent* event object
                persistent_view = EventButtons(self.cog, event)
                await message.edit(view=persistent_view)
                print(f"View updated for message {message.id} with persistent event.")

                # --- Save after successful creation ---
                self.cog.event_manager.save_events()
                # --- END ---

                # 5. Prepare Discord Scheduled Event details
                time_until = self.cog.event_view.calculate_countdown(event_datetime)
                confirmed_participants = 0
                optional_participants = 0
                total_participants = 0

                scheduled_event_description = (
                    f"{self.event_description.value}\n\n"
                    f"Raidplaner: {message.jump_url}\n"
                    f"Startet {time_until}\n"
                    f"Bestätigte Teilnehmer: {confirmed_participants}\n"
                    f"Optionale Teilnehmer: {optional_participants}\n"
                    f"Gesamte Teilnehmer: {total_participants}"
                )

                # 6. Create the Discord Scheduled Event
                try:
                    # --- LOCATION LOGIC ---
                    event_location_channel = None
                    if self.cog.default_event_voice_channel_id:
                        event_location_channel = guild.get_channel(self.cog.default_event_voice_channel_id)
                        if not isinstance(event_location_channel, discord.VoiceChannel):
                            print(f"WARNUNG: Kanal mit ID {self.cog.default_event_voice_channel_id} ist kein Voice Channel oder nicht gefunden. Fallback zu externem Event.")
                            event_location_channel = None
                    # --- END LOCATION LOGIC ---

                    discord_scheduled_event = await guild.create_scheduled_event(
                        name=self.event_name.value,
                        start_time=event_datetime.astimezone(timezone.utc),
                        end_time=event_end_time.astimezone(timezone.utc),
                        description=scheduled_event_description,
                        channel=event_location_channel,
                        privacy_level=discord.PrivacyLevel.guild_only
                    )

                    event.discord_event_id = discord_scheduled_event.id
                    event_type = "Voice Channel" if event_location_channel else "External"
                    linked_channel_name = event_location_channel.name if event_location_channel else 'None'
                    print(f"Discord scheduled event created: {discord_scheduled_event.id} (Type: {event_type}, Linked Channel: {linked_channel_name})")
                    # --- Save again after adding discord_event_id ---
                    self.cog.event_manager.save_events()
                    # --- END ---

                except discord.Forbidden:
                    print(f"Error: Missing permissions to create scheduled events in guild {guild.id}")
                    await interaction.followup.send("Ich habe keine Berechtigung, geplante Events in diesem Server zu erstellen.", ephemeral=True)
                    return
                except discord.HTTPException as http_err:
                    print(f"HTTP Error creating Discord scheduled event: {http_err.status} {http_err.text}")
                    error_detail = f" ({http_err.text})" if http_err.text else ""
                    await interaction.followup.send(f"Fehler beim Erstellen des Discord-Events (HTTP {http_err.status}){error_detail}. Bitte überprüfe die Bot-Berechtigungen und Event-Details.", ephemeral=True)
                    return
                except Exception as e:
                    print(f"Unexpected Error creating Discord scheduled event: {e}")
                    traceback.print_exc()
                    await interaction.followup.send(f"Ein unerwarteter Fehler beim Erstellen des Discord-Events ist aufgetreten: {e}", ephemeral=True)
                    return

                # 7. Final success message
                await interaction.followup.send(f"Event `{self.event_name.value}` wurde erfolgreich erstellt! 🎉", ephemeral=True)

            except discord.Forbidden:
                print(f"Error: Missing permissions to send messages in channel {self.channel_id}")
                await interaction.followup.send("Ich habe keine Berechtigung, Nachrichten in diesem Kanal zu senden.", ephemeral=True)
            except discord.HTTPException as e:
                print(f"HTTP Error during event creation (sending message/editing view): {e.status} {e.text}")
                await interaction.followup.send(f"Fehler beim Senden der Event-Nachricht: {e}", ephemeral=True)
            except Exception as e:
                print(f"Unexpected error in on_submit after deferral: {e}")
                traceback.print_exc()
                # Check for the specific TypeError
                if isinstance(e, TypeError) and "missing" in str(e) and ("argument: 'guild'" in str(e) or "argument: 'bot'" in str(e)):
                     await interaction.followup.send(f"Ein interner Fehler ist aufgetreten (Fehlendes Argument beim Embed-Aufruf). Bitte kontaktiere einen Admin.", ephemeral=True)
                else:
                     await interaction.followup.send(f"Ein unerwarteter Fehler ist aufgetreten: {e}", ephemeral=True)


    # --- Slash Command ---
    @app_commands.command(name="planen", description="Plane einen Raid")
    @app_commands.checks.has_permissions(manage_events=True)
    async def planen(self, interaction: discord.Interaction):
        modal = self.EventModal(self, interaction)
        await interaction.response.send_modal(modal)

    @planen.error
    async def planen_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message("Du hast nicht die erforderlichen Berechtigungen (Events verwalten), um diesen Befehl zu verwenden.", ephemeral=True)
        else:
            print(f"Error in planen command: {error}")
            await interaction.response.send_message("Ein unerwarteter Fehler ist beim Ausführen des Befehls aufgetreten.", ephemeral=True)


    # --- Background Task ---
    @tasks.loop(minutes=1)
    async def countdown_updater(self):
        try:
            # Make a copy to avoid issues if the dict changes during iteration
            events_to_update = list(self.event_manager.get_all_events())
        except Exception as e:
            print(f"Error fetching events for countdown_updater: {e}")
            return

        # print(f"countdown_updater running - checking {len(events_to_update)} events.") # Less verbose logging
        events_removed = False # Flag to save only if needed
        events_updated = False # Flag to save if notification_sent changed

        for event in events_to_update:
            try:
                if event.date.tzinfo is None:
                    event_date_aware = event.date.replace(tzinfo=ZoneInfo("Europe/Berlin"))
                else:
                    event_date_aware = event.date

                now_utc = datetime.now(timezone.utc)
                event_time_utc = event_date_aware.astimezone(timezone.utc)

                # Remove old events
                if event_time_utc < now_utc - timedelta(hours=3):
                    print(f"Event '{event.title}' (Msg: {event.message_id}) is old, removing from manager.")
                    if self.event_manager.remove_event(event.message_id):
                        events_removed = True # Mark for saving
                    continue

                channel = self.bot.get_channel(event.channel_id)
                if channel and isinstance(channel, discord.TextChannel):
                    try:
                        message = await channel.fetch_message(event.message_id)
                        if message:
                            await self.update_event_message(message) # Pass message
                            await self.update_discord_event(event, message)

                            # --- 10-Minute Notification Logic ---
                            time_diff = event_time_utc - now_utc
                            notification_already_sent = getattr(event, 'notification_sent', False)

                            if timedelta(minutes=9) < time_diff <= timedelta(minutes=10) and not notification_already_sent:
                                await self.send_event_notification(event)
                                if hasattr(event, 'notification_sent'):
                                    event.notification_sent = True
                                    events_updated = True # Mark for saving
                                else:
                                    print(f"WARNUNG: Attribut 'notification_sent' fehlt für Event {event.message_id}.")
                            # --- End 10-Minute Notification Logic ---

                    except discord.NotFound:
                        print(f"Nachricht mit ID {event.message_id} nicht gefunden. Event wird entfernt.")
                        if self.event_manager.remove_event(event.message_id):
                            events_removed = True # Mark for saving
                    except discord.Forbidden:
                        print(f"Keine Berechtigung, auf die Nachricht mit ID {event.message_id} zuzugreifen oder zu bearbeiten.")
                    except discord.HTTPException as e:
                        print(f"HTTP Fehler beim Abrufen/Bearbeiten der Nachricht mit ID {event.message_id}: {e.status} {e.text}")
                    except Exception as e:
                        print(f"Unerwarteter Fehler beim Aktualisieren von Event-Nachricht (Msg ID: {event.message_id}): {e}")
                        traceback.print_exc()
                elif not channel:
                    print(f"Kanal mit ID {event.channel_id} für Event '{event.title}' nicht gefunden. Event wird entfernt.")
                    if self.event_manager.remove_event(event.message_id):
                        events_removed = True # Mark for saving
            except Exception as e:
                print(f"Unerwarteter Fehler bei der Verarbeitung von Event '{event.title}' (Msg ID: {event.message_id}) in countdown_updater: {e}")
                traceback.print_exc()

        # --- Save if events were removed or updated ---
        if events_removed or events_updated:
            self.event_manager.save_events()
        # --- END ---

    @countdown_updater.before_loop
    async def before_countdown(self):
        print("Waiting for bot to be ready before starting countdown_updater...")
        await self.bot.wait_until_ready()
        print("Bot is ready, countdown_updater loop starting.")

    # --- Update Logic ---
    async def update_event_message(self, message: discord.Message): # Takes message as argument
        try:
            event = self.event_manager.get_event(message.id)
            if event:
                # --- Get guild object ---
                guild = message.guild
                if not guild:
                    print(f"Error: Could not get guild from message {message.id} in update_event_message.")
                    return # Cannot fetch member names without guild
                # --- END ---

                if event.date.tzinfo is None:
                    event_time_aware = event.date.replace(tzinfo=ZoneInfo("Europe/Berlin"))
                else:
                    event_time_aware = event.date

                now_aware = datetime.now(event_time_aware.tzinfo)
                remaining_time = event_time_aware - now_aware

                if remaining_time <= timedelta(hours=0):
                    embed_color = discord.Color.dark_grey()
                elif remaining_time <= timedelta(hours=1):
                    embed_color = discord.Color.red()
                else:
                    embed_color = discord.Color.blue()

                # --- Pass guild and bot ---
                embed = await self.event_view.update_event_embed(event, embed_color, guild, self.bot)
                # --- END ---
                view = EventButtons(self, event)
                await message.edit(embed=embed, view=view)
        except discord.NotFound:
             print(f"Message {message.id} not found during update_event_message.")
             self.event_manager.remove_event(message.id) # Remove from manager if message is gone
             self.event_manager.save_events() # Save after removal
        except discord.Forbidden:
             print(f"Missing permissions to edit message {message.id}.")
        except discord.HTTPException as e:
             if e.status != 404:
                 print(f"HTTP error editing message {message.id}: {e.status} {e.text}")
        except Exception as e:
            print(f"Fehler in update_event_message für Nachricht {message.id}: {e}")
            traceback.print_exc()

    async def update_discord_event(self, event: Event, message: discord.Message):
        if not event.discord_event_id:
            return
        if not message.guild:
             return

        try:
            discord_scheduled_event = await message.guild.fetch_scheduled_event(event.discord_event_id)

            if event.date.tzinfo is None:
                event_date_aware = event.date.replace(tzinfo=ZoneInfo("Europe/Berlin"))
            else:
                event_date_aware = event.date

            time_until = self.event_view.calculate_countdown(event_date_aware)
            # Recalculate participants based on current event state
            confirmed_participants = sum(len(group.get(role, [])) for group in event.groups for role in ["Tank", "Healer", "Melee DD", "Range DD"])
            optional_participants = sum(len(event.members.get(role, [])) for role in ["Verspätet", "Warscheinlich Ja"])
            total_participants = confirmed_participants + optional_participants

            updated_description = (
                f"{event.description}\n\n"
                f"Raidplaner: {message.jump_url}\n"
                f"Startet {time_until}\n"
                f"Bestätigte Teilnehmer: {confirmed_participants}\n"
                f"Optionale Teilnehmer: {optional_participants}\n"
                f"Gesamte Teilnehmer: {total_participants}"
            )

            if discord_scheduled_event.description != updated_description:
                await discord_scheduled_event.edit(description=updated_description)

        except discord.NotFound:
            print(f"Discord-Event mit ID {event.discord_event_id} nicht gefunden. Es wurde möglicherweise gelöscht.")
            event.discord_event_id = None
            self.event_manager.save_events() # Save the change (removed discord_event_id)
        except discord.Forbidden:
            print(f"Keine Berechtigung, das Discord-Event mit ID {event.discord_event_id} zu bearbeiten.")
        except discord.HTTPException as e:
             if e.status != 404:
                 print(f"HTTP Fehler beim Abrufen/Bearbeiten des Discord-Events mit ID {event.discord_event_id}: {e.status} {e.text}")
        except Exception as e:
            print(f"Unerwarteter Fehler in update_discord_event für Event ID {event.discord_event_id}: {e}")
            traceback.print_exc()

    # --- Notification Logic ---
    async def send_event_notification(self, event: Event):
        """Sends an @everyone notification to confirmed participants 10 minutes before the event."""
        channel = self.bot.get_channel(event.channel_id)
        if not channel:
            print(f"Error: Channel {event.channel_id} not found for sending notification for event '{event.title}'.")
            return

        confirmed_member_ids = set()
        try:
            for group in event.groups:
                for role in ["Tank", "Healer", "Melee DD", "Range DD"]:
                    if role in group:
                        confirmed_member_ids.update(group[role])
        except Exception as e:
            print(f"Error gathering confirmed members for event '{event.title}': {e}")
            return

        if confirmed_member_ids:
            mentions = " ".join(f"<@{member_id}>" for member_id in confirmed_member_ids)
            message_content = f"@everyone Das Event **{event.title}** beginnt in 10 Minuten! Teilnehmer: {mentions}"
            try:
                await channel.send(message_content, allowed_mentions=discord.AllowedMentions(everyone=True, users=True))
                print(f"Sent @everyone notification for '{event.title}' in channel {channel.id}")
            except discord.Forbidden:
                print(f"Error: Missing permissions to send @everyone notification in channel {channel.id}.")
            except discord.HTTPException as e:
                print(f"HTTP Error sending notification for event '{event.title}': {e.status} {e.text}")
            except Exception as e:
                print(f"Unexpected error sending notification for event '{event.title}': {e}")
                traceback.print_exc()
        else:
            print(f"No confirmed members found for event '{event.title}'. Skipping notification.")


    # --- Button Interaction Handling ---
    async def clear_user_from_all_categories(self, event: Event, member: discord.Member) -> bool:
        """Removes user from all roles/categories and returns True if changes were made."""
        user_id = member.id
        cleared = False
        for group in event.groups:
            for role_list in group.values(): # Iterate through lists in the group dict
                 if user_id in role_list:
                    role_list.remove(user_id)
                    cleared = True
        for category_list in event.members.values(): # Iterate through lists in the members dict
            if user_id in category_list:
                category_list.remove(user_id)
                cleared = True
        return cleared


    async def handle_button_click(self, interaction: discord.Interaction, role: str, event: Event):
        await interaction.response.defer(ephemeral=True)
        member = interaction.user
        if not isinstance(member, discord.Member): # Ensure we have a Member object for guild context
             member = interaction.guild.get_member(interaction.user.id)
        if not member:
            await interaction.followup.send("Benutzer konnte nicht im Server gefunden werden.", ephemeral=True)
            print(f"Error: Could not get member object for user ID {interaction.user.id} in guild {interaction.guild_id}")
            return

        # --- Time Lock Check ---
        if event.date.tzinfo is None:
            event_time_aware = event.date.replace(tzinfo=ZoneInfo("Europe/Berlin"))
        else:
            event_time_aware = event.date
        now_aware = datetime.now(event_time_aware.tzinfo)
        remaining_time = event_time_aware - now_aware

        if remaining_time <= timedelta(hours=2):
            print(f"Event '{event.title}' starts soon (within 2h), changes locked for {member.name}.")
            try:
                await member.send(
                    f"Das Event `{event.title}` beginnt in weniger als zwei Stunden ({self.event_view.calculate_countdown(event_time_aware)}). Änderungen an der Anmeldung sind nicht mehr möglich."
                )
                await interaction.followup.send(
                     f"Das Event `{event.title}` beginnt bald (weniger als 2 Stunden). Änderungen sind nicht mehr möglich.", ephemeral=True
                )
            except discord.Forbidden:
                 await interaction.followup.send(
                     f"Das Event `{event.title}` beginnt bald (weniger als 2 Stunden). Änderungen sind nicht mehr möglich. (Konnte keine DM senden)", ephemeral=True
                 )
            except Exception as e:
                 print(f"Error sending 2h lock notification to {member.name}: {e}")
                 await interaction.followup.send(
                     f"Das Event `{event.title}` beginnt bald (weniger als 2 Stunden). Änderungen sind nicht mehr möglich. (Fehler beim Senden der DM)", ephemeral=True
                 )
            return

        # --- Update Logic ---
        try:
            # --- Flag for changes ---
            user_cleared = await self.clear_user_from_all_categories(event, member)
            user_added = False
            # --- END ---

            if role in ["Tank", "Healer", "Melee DD", "Range DD"]:
                if hasattr(event, 'add_member_to_group') and callable(getattr(event, 'add_member_to_group')):
                    try:
                        # Assume add_member_to_group returns True if added, False otherwise
                        if event.add_member_to_group(role, member.id):
                             user_added = True
                    except Exception as e: print(f"Error calling event.add_member_to_group: {e}")
                else:
                    print(f"Event object missing 'add_member_to_group' method.")
                    # Fallback logic (less reliable for tracking changes)
                    added_fallback = False
                    for group in event.groups:
                        if role in group:
                            if member.id not in group[role]:
                                 group[role].append(member.id)
                                 added_fallback = True
                                 break
                    if added_fallback: user_added = True
                    else: print(f"Could not add {member.name} to role {role} - fallback failed.")

            elif role in ["Verspätet", "Warscheinlich Ja", "Keine Zeit"]:
                if hasattr(event, 'add_member_to_optional') and callable(getattr(event, 'add_member_to_optional')):
                     try:
                         # Assume add_member_to_optional returns True if added
                         if event.add_member_to_optional(role, member.id):
                              user_added = True
                     except Exception as e:
                          print(f"Error calling event.add_member_to_optional: {e}")
                          # Fallback if method fails
                          if role in event.members:
                               if member.id not in event.members[role]:
                                    event.members[role].append(member.id)
                                    user_added = True
                          else:
                               event.members[role] = [member.id]
                               user_added = True
                else:
                     print(f"Event object missing 'add_member_to_optional' method.")
                     # Fallback logic
                     if role in event.members:
                          if member.id not in event.members[role]:
                               event.members[role].append(member.id)
                               user_added = True
                     else:
                          event.members[role] = [member.id]
                          user_added = True
            else:
                 print(f"Error: Unknown role '{role}' clicked.")
                 await interaction.followup.send(f"Unbekannte Rolle '{role}' ausgewählt.", ephemeral=True)
                 return

            # --- Only save and update if changes were made ---
            if user_cleared or user_added:
                await self.update_event_message(interaction.message) # Pass message
                await self.update_discord_event(event, interaction.message)
                # Save the new state
                self.event_manager.save_events()
                await interaction.followup.send(f"Deine Auswahl '{role}' wurde gespeichert.", ephemeral=True)
            else:
                 # Optional: Message if nothing changed (user clicked the same button again)
                 await interaction.followup.send(f"Du bist bereits für '{role}' eingetragen. Keine Änderung vorgenommen.", ephemeral=True)
            # --- END ---

        except Exception as e:
            print(f"Error during handle_button_click for {member.name} and role '{role}': {e}")
            traceback.print_exc()
            await interaction.followup.send(f"Ein Fehler ist beim Speichern deiner Auswahl aufgetreten: {e}", ephemeral=True)


    async def handle_button_remove(self, interaction: discord.Interaction, role: str, event: Event):
        await interaction.response.defer(ephemeral=True)
        member = interaction.user
        if not isinstance(member, discord.Member): # Ensure Member object
             member = interaction.guild.get_member(interaction.user.id)
        if not member:
            await interaction.followup.send("Benutzer konnte nicht im Server gefunden werden.", ephemeral=True)
            print(f"Error: Could not get member object for user ID {interaction.user.id} in guild {interaction.guild_id}")
            return

        # --- Time Lock Check ---
        if event.date.tzinfo is None:
            event_time_aware = event.date.replace(tzinfo=ZoneInfo("Europe/Berlin"))
        else:
            event_time_aware = event.date
        now_aware = datetime.now(event_time_aware.tzinfo)
        remaining_time = event_time_aware - now_aware

        if remaining_time <= timedelta(hours=2):
            print(f"Event '{event.title}' starts soon (within 2h), changes locked for {member.name}.")
            try:
                await member.send(
                    f"Das Event `{event.title}` beginnt in weniger als zwei Stunden ({self.event_view.calculate_countdown(event_time_aware)}). Änderungen an der Anmeldung sind nicht mehr möglich."
                )
                await interaction.followup.send(
                     f"Das Event `{event.title}` beginnt bald (weniger als 2 Stunden). Änderungen sind nicht mehr möglich.", ephemeral=True
                )
            except discord.Forbidden:
                 await interaction.followup.send(
                     f"Das Event `{event.title}` beginnt bald (weniger als 2 Stunden). Änderungen sind nicht mehr möglich. (Konnte keine DM senden)", ephemeral=True
                 )
            except Exception as e:
                 print(f"Error sending 2h lock notification to {member.name}: {e}")
                 await interaction.followup.send(
                     f"Das Event `{event.title}` beginnt bald (weniger als 2 Stunden). Änderungen sind nicht mehr möglich. (Fehler beim Senden der DM)", ephemeral=True
                 )
            return

        # --- Removal Logic ---
        try:
            # --- Check if user was actually removed ---
            user_cleared = await self.clear_user_from_all_categories(event, member)

            if user_cleared:
                 await self.update_event_message(interaction.message) # Pass message
                 await self.update_discord_event(event, interaction.message)
                 # Save the new state
                 self.event_manager.save_events()
                 await interaction.followup.send("Deine Auswahl wurde entfernt.", ephemeral=True)
            else:
                 # Optional: Message if user wasn't signed up
                 await interaction.followup.send("Du warst für keine Rolle angemeldet. Keine Änderung vorgenommen.", ephemeral=True)
            # --- END ---

        except Exception as e:
            print(f"Error during handle_button_remove for {member.name} and role '{role}': {e}")
            traceback.print_exc()
            await interaction.followup.send(f"Ein Fehler ist beim Entfernen deiner Auswahl aufgetreten: {e}", ephemeral=True)


# --- View Definition ---
class EventButtons(discord.ui.View):
    def __init__(self, cog: EventPlanner, event: Event):
        super().__init__(timeout=None)
        self.cog = cog
        self.event_message_id = event.message_id if hasattr(event, 'message_id') else None

        self.add_item(EventButton(self.cog, "Tank", "<:tank:1292758103128936468>", self.event_message_id, discord.ButtonStyle.primary, row=0))
        self.add_item(EventButton(self.cog, "Healer", "<:healer:1292758088197341235>", self.event_message_id, discord.ButtonStyle.success, row=0))
        self.add_item(EventButton(self.cog, "Melee DD", "<:dps:1292758071894085682>", self.event_message_id, discord.ButtonStyle.danger, row=0))
        self.add_item(EventButton(self.cog, "Range DD", "<:dps:1292758071894085682>", self.event_message_id, discord.ButtonStyle.danger, row=0))
        self.add_item(EventButton(self.cog, "Verspätet", "⏰", self.event_message_id, discord.ButtonStyle.secondary, row=1))
        self.add_item(EventButton(self.cog, "Warscheinlich Ja", "❓", self.event_message_id, discord.ButtonStyle.secondary, row=1))
        self.add_item(EventButton(self.cog, "Keine Zeit", "❌", self.event_message_id, discord.ButtonStyle.secondary, row=1))


# --- Button Definition ---
class EventButton(discord.ui.Button):
    def __init__(self, cog: EventPlanner, role: str, emoji: str, event_message_id: int | None, style: discord.ButtonStyle, row: int):
        # Use message_id in custom_id to link button to event
        msg_id_part = str(event_message_id) if event_message_id else "temp"
        # Ensure role names are filesystem/URL safe for custom_id
        role_id_part = role.replace(' ', '_').replace('ä', 'ae').replace('ö', 'oe').replace('ü', 'ue').replace('ß', 'ss')
        custom_id = f"event_{msg_id_part}_btn_{role_id_part}"

        # Shorten custom_id if it exceeds Discord's limit (100 chars)
        if len(custom_id) > 100:
             # A simple shortening strategy, might need refinement
             msg_id_short = msg_id_part[-10:] # Last 10 digits of message ID
             role_id_short = role_id_part[:20] # First 20 chars of role ID part
             custom_id = f"evt_{msg_id_short}_{role_id_short}"
             # Ensure it's definitely under 100
             custom_id = custom_id[:100]
             print(f"Warning: Custom ID for role '{role}' was too long, shortened to: {custom_id}")

        super().__init__(label=role, style=style, emoji=emoji, custom_id=custom_id, row=row)
        self.cog = cog
        self.role = role
        # Store the original message ID if available, used to find the event later
        self.event_message_id = event_message_id

    async def callback(self, interaction: discord.Interaction):
        # Try to get the event using the stored message ID or the interaction's message ID
        # The stored ID is more reliable if the view was created with a persistent event
        current_event_message_id = self.event_message_id or interaction.message.id
        active_event = self.cog.event_manager.get_event(current_event_message_id)

        if not active_event:
            print(f"Error: Event associated with message {current_event_message_id} not found in manager during button callback.")
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message("Fehler: Das zugehörige Event konnte nicht gefunden werden. Es wurde möglicherweise gelöscht.", ephemeral=True)
                else:
                    await interaction.followup.send("Fehler: Das zugehörige Event konnte nicht gefunden werden. Es wurde möglicherweise gelöscht.", ephemeral=True)
            except discord.HTTPException: pass
            try:
                # Attempt to remove buttons if event is gone
                await interaction.message.edit(view=None)
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                pass # Ignore errors if message is already gone or permissions are missing
            return

        # Check current selection state for the interacting user
        user_id = interaction.user.id
        is_currently_selected = False
        try:
            # Check group roles
            if self.role in ["Tank", "Healer", "Melee DD", "Range DD"]:
                is_currently_selected = any(user_id in group.get(self.role, []) for group in active_event.groups)
            # Check optional categories
            elif self.role in ["Verspätet", "Warscheinlich Ja", "Keine Zeit"]:
                is_currently_selected = user_id in active_event.members.get(self.role, [])
        except Exception as e:
             print(f"Error checking current selection for {user_id} in role {self.role}: {e}")
             try:
                 if not interaction.response.is_done(): await interaction.response.send_message("Fehler beim Überprüfen deiner aktuellen Auswahl.", ephemeral=True)
                 else: await interaction.followup.send("Fehler beim Überprüfen deiner aktuellen Auswahl.", ephemeral=True)
             except discord.HTTPException: pass
             return

        # Execute add or remove action based on current state
        try:
            if is_currently_selected:
                # If user clicked the button for the role they already have, remove them
                await self.cog.handle_button_remove(interaction, self.role, active_event)
            else:
                # If user clicked a new role button, add them
                await self.cog.handle_button_click(interaction, self.role, active_event)
        except Exception as e:
            print(f"Fehler in EventButton.callback für Rolle '{self.role}' von {interaction.user.name}: {e}")
            traceback.print_exc()
            try:
                # Try to inform user about the error
                if not interaction.response.is_done(): await interaction.response.send_message(f"Ein unerwarteter Fehler ist aufgetreten: {e}", ephemeral=True)
                else: await interaction.followup.send(f"Ein unerwarteter Fehler ist aufgetreten: {e}", ephemeral=True)
            except discord.HTTPException:
                 print("Konnte keine Fehlermeldung an Benutzer senden (Interaction möglicherweise bereits beantwortet).")


# --- Cog Setup ---
async def setup(bot):
    await bot.add_cog(EventPlanner(bot))
    print("EventPlanner Cog loaded.")
