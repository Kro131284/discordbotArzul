import discord
from discord.ext import commands
from datetime import datetime
from zoneinfo import ZoneInfo
import asyncio # Import asyncio
import traceback # Für detailliertere Fehlermeldungen

class EventView:
    def __init__(self, tank_emoji, healer_emoji, dps_emoji):
        self.tank_emoji = tank_emoji
        self.healer_emoji = healer_emoji
        self.dps_emoji = dps_emoji

    def format_title(self, title):
        """Formatiert den Titel für die Anzeige im Embed."""
        return f"**{title.upper()}**"

    # --- MODIFIED: Added guild parameter ---
    async def _build_user_cache(self, user_ids: set, guild: discord.Guild, bot: commands.Bot) -> dict:
        """Erstellt einen Cache mit Server-Nicknames (oder Usernamen) für die gegebenen IDs."""
        if not guild: # Fallback, falls kein Guild-Objekt vorhanden ist
             print("WARNUNG: Kein Guild-Objekt in _build_user_cache. Verwende globale Namen.")
             # Hier könnte man die alte Logik mit bot.get_user/fetch_user als Fallback einbauen
             # Aber für Server-Nicknames ist das Guild-Objekt essentiell.
             return {uid: "Fehler (Guild)" for uid in user_ids}

        user_cache = {}
        remaining_ids = set()

        # 1. Versuche, alle Member aus dem Guild-Cache zu holen
        for user_id in user_ids:
            member = guild.get_member(user_id) # Verwende guild.get_member
            if member:
                # display_name gibt Nickname zurück, wenn vorhanden, sonst globalen Namen
                user_cache[user_id] = member.display_name
            else:
                remaining_ids.add(user_id)

        # 2. Für die restlichen IDs, fetch_member parallel verwenden
        async def fetch_and_cache(uid):
            try:
                member = await guild.fetch_member(uid) # Verwende guild.fetch_member
                user_cache[uid] = member.display_name if member else "Unbekannt (API)"
            except discord.NotFound:
                print(f"Mitglied mit ID {uid} nicht im Server gefunden (API).")
                # Optional: Versuche User zu fetchen als letzten Fallback
                try:
                    user = await bot.fetch_user(uid)
                    user_cache[uid] = user.name if user else "Unbekannt"
                except discord.NotFound:
                    user_cache[uid] = "Unbekannt"
            except discord.HTTPException as e:
                print(f"HTTP Fehler beim Abrufen von Mitglied {uid}: {e}")
                user_cache[uid] = "Fehler" # Fallback bei API-Fehler
            except Exception as e:
                print(f"Unerwarteter Fehler beim Abrufen von Mitglied {uid}: {e}")
                traceback.print_exc()
                user_cache[uid] = "Fehler" # Allgemeiner Fallback

        if remaining_ids:
            tasks = [fetch_and_cache(uid) for uid in remaining_ids]
            await asyncio.gather(*tasks) # Führt die API-Aufrufe parallel aus

        return user_cache

    # --- MODIFIED: Added guild parameter ---
    async def create_event_embed(self, event, guild: discord.Guild, bot: commands.Bot):
        """Erstellt das Embed für ein neues Event."""
        embed = discord.Embed(
            title=self.format_title(event.title),
            description=event.description,
            color=discord.Color.blue()
        )
        event_date_aware = event.date
        if event.date.tzinfo is None:
            event_date_aware = event.date.replace(tzinfo=ZoneInfo("Europe/Berlin"))

        embed.add_field(name="📅 Datum", value=f"{event_date_aware.strftime('%d. %B %Y')}", inline=True)
        embed.add_field(name="⏰ Uhrzeit", value=f"{event_date_aware.strftime('%H:%M')}", inline=True)
        embed.add_field(name="⌛ Countdown", value=self.calculate_countdown(event_date_aware), inline=True)

        # --- Optimierter User Lookup ---
        all_user_ids = set()
        for group in event.groups:
            all_user_ids.update(group.get("Tank", []))
            all_user_ids.update(group.get("Healer", []))
            all_user_ids.update(group.get("Melee DD", []))
            all_user_ids.update(group.get("Range DD", []))
        all_user_ids.update(event.members.get("Verspätet", []))
        all_user_ids.update(event.members.get("Warscheinlich Ja", []))
        all_user_ids.update(event.members.get("Keine Zeit", []))

        # Baue den Cache mit Namen auf (Cache + API-Fallback)
        # --- MODIFIED: Pass guild ---
        user_cache = await self._build_user_cache(all_user_ids, guild, bot)
        # --- Ende Optimierung ---

        # Display the groups
        for idx, group in enumerate(event.groups, start=1):
            tank_names = ', '.join(user_cache.get(member_id, "Unbekannt") for member_id in group.get("Tank", [])) or "Leer"
            healer_names = ', '.join(user_cache.get(member_id, "Unbekannt") for member_id in group.get("Healer", [])) or "Leer"
            melee_dd_names = ', '.join(user_cache.get(member_id, "Unbekannt") for member_id in group.get("Melee DD", [])) or "Leer"
            range_dd_names = ', '.join(user_cache.get(member_id, "Unbekannt") for member_id in group.get("Range DD", [])) or "Leer"

            group_status = (
                f"{self.tank_emoji} Tank: {tank_names}\n"
                f"{self.healer_emoji} Healer: {healer_names}\n"
                f"{self.dps_emoji} Melee DD: {melee_dd_names}\n"
                f"{self.dps_emoji} Range DD: {range_dd_names}"
            )
            embed.add_field(name=f"Gruppe {idx}", value=group_status, inline=False)

        # Display the optional participants
        late_status = ', '.join(user_cache.get(member_id, "Unbekannt") for member_id in event.members.get("Verspätet", [])) or "Keine"
        maybe_status = ', '.join(user_cache.get(member_id, "Unbekannt") for member_id in event.members.get("Warscheinlich Ja", [])) or "Keine"
        absent_status = ', '.join(user_cache.get(member_id, "Unbekannt") for member_id in event.members.get("Keine Zeit", [])) or "Keine"

        embed.add_field(name="Komme Später", value=late_status, inline=True)
        embed.add_field(name="Warscheinlich Ja", value=maybe_status, inline=True)
        embed.add_field(name="Keine Zeit", value=absent_status, inline=True)

        return embed

    # --- MODIFIED: Added guild parameter ---
    async def update_event_embed(self, event, embed_color, guild: discord.Guild, bot: commands.Bot):
        """Aktualisiert das Embed mit den aktuellen Informationen."""
        embed = discord.Embed(title=self.format_title(event.title), description=event.description, color=embed_color)

        event_date_aware = event.date
        if event.date.tzinfo is None:
            event_date_aware = event.date.replace(tzinfo=ZoneInfo("Europe/Berlin"))

        embed.add_field(name="📅 Datum", value=f"{event_date_aware.strftime('%d. %B %Y')}", inline=True)
        embed.add_field(name="⏰ Uhrzeit", value=f"{event_date_aware.strftime('%H:%M')}", inline=True)
        embed.add_field(name="⌛ Countdown", value=self.calculate_countdown(event_date_aware), inline=True)

        # Count participants
        confirmed_participants = sum(len(group.get(role, [])) for group in event.groups for role in ["Tank", "Healer", "Melee DD", "Range DD"])
        optional_participants = sum(len(event.members.get(role, [])) for role in ["Verspätet", "Warscheinlich Ja"])
        total_participants = confirmed_participants + optional_participants

        embed.add_field(
            name="Anmeldungen",
            value=f"Bestätigt: {confirmed_participants} | Optional: {optional_participants} | Gesamt: {total_participants}",
            inline=False
        )

        # --- Optimierter User Lookup ---
        all_user_ids = set()
        for group in event.groups:
            all_user_ids.update(group.get("Tank", []))
            all_user_ids.update(group.get("Healer", []))
            all_user_ids.update(group.get("Melee DD", []))
            all_user_ids.update(group.get("Range DD", []))
        all_user_ids.update(event.members.get("Verspätet", []))
        all_user_ids.update(event.members.get("Warscheinlich Ja", []))
        all_user_ids.update(event.members.get("Keine Zeit", []))

        # Baue den Cache mit Namen auf (Cache + API-Fallback)
        # --- MODIFIED: Pass guild ---
        user_cache = await self._build_user_cache(all_user_ids, guild, bot)
        # --- Ende Optimierung ---

        # Display the groups
        for idx, group in enumerate(event.groups, start=1):
            tank_names = ', '.join(user_cache.get(member_id, "Unbekannt") for member_id in group.get("Tank", [])) or "Leer"
            healer_names = ', '.join(user_cache.get(member_id, "Unbekannt") for member_id in group.get("Healer", [])) or "Leer"
            melee_dd_names = ', '.join(user_cache.get(member_id, "Unbekannt") for member_id in group.get("Melee DD", [])) or "Leer"
            range_dd_names = ', '.join(user_cache.get(member_id, "Unbekannt") for member_id in group.get("Range DD", [])) or "Leer"

            group_status = (
                f"{self.tank_emoji} Tank: {tank_names}\n"
                f"{self.healer_emoji} Healer: {healer_names}\n"
                f"{self.dps_emoji} Melee DD: {melee_dd_names}\n"
                f"{self.dps_emoji} Range DD: {range_dd_names}"
            )
            embed.add_field(name=f"Gruppe {idx}", value=group_status, inline=False)

        # Display the optional participants
        late_status = ', '.join(user_cache.get(member_id, "Unbekannt") for member_id in event.members.get("Verspätet", [])) or "Keine"
        maybe_status = ', '.join(user_cache.get(member_id, "Unbekannt") for member_id in event.members.get("Warscheinlich Ja", [])) or "Keine"
        absent_status = ', '.join(user_cache.get(member_id, "Unbekannt") for member_id in event.members.get("Keine Zeit", [])) or "Keine"

        embed.add_field(name="Komme Später", value=late_status, inline=True)
        embed.add_field(name="Warscheinlich Ja", value=maybe_status, inline=True)
        embed.add_field(name="Keine Zeit", value=absent_status, inline=True)

        return embed

    def calculate_countdown(self, event_time):
        """Berechnet die verbleibende Zeit bis zum Event. Nimmt an, dass event_time aware ist."""
        if event_time.tzinfo is None:
            event_time = event_time.replace(tzinfo=ZoneInfo("Europe/Berlin"))

        now = datetime.now(event_time.tzinfo)

        if now < event_time:
            countdown = event_time - now
            days = countdown.days
            hours, remainder = divmod(countdown.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)

            parts = []
            if days > 1:
                parts.append(f"{days} Tagen")
            elif days == 1:
                parts.append("1 Tag")

            if hours > 1:
                parts.append(f"{hours} Std")
            elif hours == 1:
                parts.append("1 Std")

            if minutes > 1:
                parts.append(f"{minutes} Min")
            elif minutes == 1:
                parts.append("1 Min")

            if days == 0 and hours == 0 and minutes == 0:
                if seconds == 1:
                    return "in 1 Sekunde"
                else:
                    return f"in {seconds} Sekunden"

            if not parts:
                return "Jetzt"

            time_until = "in " + ", ".join(parts)

        else:
            elapsed = now - event_time
            days = elapsed.days
            hours, remainder = divmod(elapsed.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)

            parts = []
            if days > 1:
                parts.append(f"{days} Tagen")
            elif days == 1:
                parts.append("1 Tag")

            if hours > 1:
                parts.append(f"{hours} Std")
            elif hours == 1:
                parts.append("1 Std")

            if minutes > 1:
                parts.append(f"{minutes} Min")
            elif minutes == 1:
                parts.append("1 Min")

            if days == 0 and hours == 0 and minutes == 0:
                if seconds == 1:
                    return "vor 1 Sekunde"
                else:
                    return f"vor {seconds} Sekunden"

            if not parts:
                return "Gerade eben"

            time_until = "vor " + ", ".join(parts)

        return time_until
