# cogs/model/raidplaner_model.py
import json
import traceback # Für detailliertere Fehlermeldungen
from datetime import datetime, timezone # Import timezone
from zoneinfo import ZoneInfo # Import ZoneInfo

# --- Konstanten für Rollenlimits pro Gruppe ---
MAX_TANK_PER_GROUP = 1
MAX_HEALER_PER_GROUP = 1
MAX_DD_PER_GROUP = 4 # Melee + Range DDs kombiniert

class Event:
    def __init__(self, title, date, description, message_id=None, channel_id=None, discord_event_id=None, notification_sent=False):
        self.title = title
        # Stelle sicher, dass das Datum immer timezone-aware ist (z.B. Europe/Berlin)
        if date.tzinfo is None:
            self.date = date.replace(tzinfo=ZoneInfo("Europe/Berlin"))
        else:
            self.date = date
        self.description = description
        self.message_id = message_id
        self.channel_id = channel_id
        self.discord_event_id = discord_event_id
        self.notification_sent = notification_sent # Wichtig für Persistenz
        # Startet mit einer leeren Gruppe, weitere werden bei Bedarf hinzugefügt
        self.groups = [
            {"Tank": [], "Healer": [], "Melee DD": [], "Range DD": []}
        ]
        self.members = {
            "Verspätet": [],
            "Warscheinlich Ja": [],
            "Keine Zeit": []
        }

    def to_dict(self):
        return {
            "title": self.title,
            "date_iso": self.date.isoformat(),
            "description": self.description,
            "message_id": self.message_id,
            "channel_id": self.channel_id,
            "discord_event_id": self.discord_event_id,
            "notification_sent": self.notification_sent,
            "groups": self.groups,
            "members": self.members,
        }

    @classmethod
    def from_dict(cls, data):
        event_date = datetime.fromisoformat(data["date_iso"])
        if event_date.tzinfo is None:
             event_date = event_date.replace(tzinfo=ZoneInfo("Europe/Berlin"))

        event = cls(
            title=data["title"],
            date=event_date,
            description=data["description"],
            message_id=data.get("message_id"),
            channel_id=data.get("channel_id"),
            discord_event_id=data.get("discord_event_id"),
            notification_sent=data.get("notification_sent", False)
        )
        # Stelle sicher, dass 'groups' immer mindestens eine Gruppe enthält, wenn geladen
        event.groups = data.get("groups", [{"Tank": [], "Healer": [], "Melee DD": [], "Range DD": []}])
        if not event.groups: # Falls groups leer war, füge eine Standardgruppe hinzu
             event.groups.append({"Tank": [], "Healer": [], "Melee DD": [], "Range DD": []})
        event.members = data.get("members", {"Verspätet": [], "Warscheinlich Ja": [], "Keine Zeit": []})
        return event

    # --- ÜBERARBEITETE GRUPPENLOGIK ---
    def add_member_to_group(self, role, member_id):
        """
        Fügt ein Mitglied zu einer Gruppe hinzu, basierend auf Rolle und Verfügbarkeit.
        Erstellt neue Gruppen, wenn nötig.
        Gibt True zurück, wenn hinzugefügt, False sonst.
        """
        if role not in ["Tank", "Healer", "Melee DD", "Range DD"]:
            print(f"FEHLER: Ungültige Rolle '{role}' für Gruppenzuweisung.")
            return False

        # 1. Prüfen, ob Mitglied bereits in irgendeiner Gruppe für irgendeine Rolle ist
        #    (Dies wird eigentlich vom Controller durch clear_user_from_all_categories erledigt,
        #     aber eine zusätzliche Sicherheit schadet nicht)
        for group_idx, group in enumerate(self.groups):
            for r, members in group.items():
                if member_id in members:
                    print(f"WARNUNG: Mitglied {member_id} ist bereits in Gruppe {group_idx+1} als {r}. Wird nicht erneut hinzugefügt.")
                    # Optional: Hier könnte man den User erst entfernen, wenn das gewünscht ist.
                    return False # Verhindert doppelte Einträge

        # 2. Finde eine passende Gruppe oder erstelle eine neue
        added = False
        for group_idx, group in enumerate(self.groups):
            if role == "Tank":
                if len(group.get("Tank", [])) < MAX_TANK_PER_GROUP:
                    group.setdefault("Tank", []).append(member_id)
                    print(f"Mitglied {member_id} zu Rolle 'Tank' in Gruppe {group_idx+1} hinzugefügt.")
                    added = True
                    break # Mitglied wurde platziert
            elif role == "Healer":
                if len(group.get("Healer", [])) < MAX_HEALER_PER_GROUP:
                    group.setdefault("Healer", []).append(member_id)
                    print(f"Mitglied {member_id} zu Rolle 'Healer' in Gruppe {group_idx+1} hinzugefügt.")
                    added = True
                    break # Mitglied wurde platziert
            elif role in ["Melee DD", "Range DD"]:
                current_dd_count = len(group.get("Melee DD", [])) + len(group.get("Range DD", []))
                if current_dd_count < MAX_DD_PER_GROUP:
                    group.setdefault(role, []).append(member_id)
                    print(f"Mitglied {member_id} zu Rolle '{role}' in Gruppe {group_idx+1} hinzugefügt.")
                    added = True
                    break # Mitglied wurde platziert

        # 3. Wenn in keiner vorhandenen Gruppe Platz war, erstelle eine neue Gruppe
        if not added:
            print(f"Kein Platz für Rolle '{role}' in vorhandenen Gruppen. Erstelle Gruppe {len(self.groups) + 1}.")
            new_group = {"Tank": [], "Healer": [], "Melee DD": [], "Range DD": []}
            new_group[role].append(member_id)
            self.groups.append(new_group)
            print(f"Mitglied {member_id} zu Rolle '{role}' in NEUER Gruppe {len(self.groups)} hinzugefügt.")
            added = True

        return added
    # --- ENDE ÜBERARBEITETE GRUPPENLOGIK ---

    def add_member_to_optional(self, category, member_id):
        """Fügt ein Mitglied zu einer optionalen Kategorie hinzu."""
        # Sicherstellen, dass der User nicht schon in einer Hauptgruppe ist
        # (Wird vom Controller gehandhabt, aber zur Sicherheit)
        for group in self.groups:
            for role_list in group.values():
                if member_id in role_list:
                     print(f"WARNUNG: {member_id} ist bereits in einer Hauptgruppe. Kann nicht zu '{category}' hinzugefügt werden.")
                     return False # Verhindert Hinzufügen zu Optional, wenn schon in Gruppe

        if category in self.members:
            if member_id not in self.members[category]:
                self.members[category].append(member_id)
                print(f"Added {member_id} to optional category {category}")
                return True
            else:
                print(f"Could not add {member_id} to {category} (already exists)")
                return False
        else:
             # Optional: Nur erlaubte Kategorien zulassen?
             # if category in ["Verspätet", "Warscheinlich Ja", "Keine Zeit"]:
             self.members[category] = [member_id] # Falls Kategorie neu ist (sollte nicht passieren mit Buttons)
             print(f"Created category {category} and added {member_id}")
             return True
             # else:
             #     print(f"FEHLER: Ungültige optionale Kategorie '{category}'")
             #     return False

    def remove_member_from_optional(self, category, member_id):
         if category in self.members and member_id in self.members[category]:
              self.members[category].remove(member_id)
              print(f"Removed {member_id} from optional category {category}")
              return True # Erfolgreich entfernt
         return False # War nicht in der Kategorie

# --- EventManager Klasse (unverändert, außer Laden/Speichern) ---
class EventManager:
    def __init__(self, filename="events.json"):
        self.events = {}  # Dictionary: message_id -> Event object
        self.filename = filename
        self.load_events() # Lade Events beim Initialisieren

    def create_event(self, title, date, description, message_id):
        if message_id in self.events:
            print(f"WARNUNG: Event mit Message ID {message_id} existiert bereits.")
            return self.events[message_id]
        # Startet jetzt mit der Logik der Event-Klasse (eine Gruppe initial)
        event = Event(title, date, description, message_id)
        self.events[message_id] = event
        print(f"Event '{title}' (Msg ID: {message_id}) erstellt und im Manager hinzugefügt.")
        # Speichern wird jetzt im Controller aufgerufen, nachdem alles (inkl. Discord Event ID) gesetzt ist
        return event

    def get_event(self, message_id):
        return self.events.get(message_id)

    def get_all_events(self):
        return list(self.events.values()) # Gibt eine Kopie der Liste zurück

    def remove_event(self, message_id):
        if message_id in self.events:
            del self.events[message_id]
            print(f"Event mit Message ID {message_id} entfernt.")
            # Speichern wird jetzt im Controller aufgerufen
            return True
        return False

    def save_events(self):
        """Speichert alle aktuellen Events in die JSON-Datei."""
        try:
            # Konvertiere Event-Objekte in Dictionaries für JSON
            data_to_save = {str(msg_id): event.to_dict() for msg_id, event in self.events.items()}
            with open(self.filename, 'w', encoding='utf-8') as f:
                json.dump(data_to_save, f, indent=4, ensure_ascii=False)
            # print(f"Events erfolgreich in '{self.filename}' gespeichert.") # Weniger verbose
        except IOError as e:
            print(f"FEHLER beim Speichern der Events in '{self.filename}': {e}")
        except Exception as e:
            print(f"Unerwarteter FEHLER beim Speichern der Events: {e}")
            traceback.print_exc()

    def load_events(self):
        """Lädt Events aus der JSON-Datei beim Start."""
        try:
            with open(self.filename, 'r', encoding='utf-8') as f:
                loaded_data = json.load(f)
                self.events = {} # Leere aktuelle Events, um Duplikate zu vermeiden
                for msg_id_str, event_data in loaded_data.items():
                    try:
                        msg_id = int(msg_id_str)
                        event = Event.from_dict(event_data)
                        # Stelle sicher, dass message_id im Event-Objekt korrekt ist
                        if event.message_id != msg_id:
                             print(f"WARNUNG: Message ID Diskrepanz beim Laden für {msg_id}. Überschreibe mit Key.")
                             event.message_id = msg_id
                        self.events[msg_id] = event
                    except (ValueError, KeyError, TypeError, AttributeError) as e: # AttributeError hinzugefügt
                         print(f"FEHLER beim Verarbeiten eines Events aus der Datei (ID: {msg_id_str}): {e}. Überspringe Eintrag.")
                         traceback.print_exc() # Zeige den Traceback für Debugging
                         continue # Überspringe fehlerhafte Einträge
                print(f"{len(self.events)} Events erfolgreich aus '{self.filename}' geladen.")
        except FileNotFoundError:
            print(f"Event-Datei '{self.filename}' nicht gefunden. Starte mit leerer Event-Liste.")
            self.events = {}
        except json.JSONDecodeError as e:
            print(f"FEHLER beim Lesen der JSON-Datei '{self.filename}': {e}. Starte mit leerer Event-Liste.")
            self.events = {} # Bei fehlerhafter JSON-Datei leer starten
        except Exception as e:
            print(f"Unerwarteter FEHLER beim Laden der Events: {e}")
            traceback.print_exc()
            self.events = {} # Sicherer Fallback
