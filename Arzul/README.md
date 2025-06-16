# DiscordBotArzul
DiscordBot

Der Bot verfügt über ein Kalenderscript, welches den aktuellen Monat,den aktuellen Tag und die anstehenden Events im Monat anzeigt.
Hierbei generiert er ein Bild und postet dieses als eingebettete Nachricht in einen Channel. Desweiteren wird ein Droppdown Menü erstellt
über das die Events ausgewählt werden können, dabei wird das gewählte Event per PN an den User geschickt.
[ Evtl Überarbeitete Darstellung mit REACT oder Node.js]
Kalender schickt 1h vor event und 10 minuten vorher eine Benachrichtigung und meldet wenn ein neues event erstellt wurde. Wir benötigen DotEnv da wir die Daten ausgelagert haben.
Der Bot meldet bei Events wenn sie erschaffen werden und abgebrochen werden in den Channel.
Wenn an dem aktuellen Tag ein Event ist wird dies in rot dargestellt.
Kalender wird in zwei Monate angezeigt.

[pip install python-dotenv
pip install matplotlib 
pip install discord.py 
pip install pytz
pip install requests
pip install aiomysql
pip install os]

Erweiterungen:
1a)Kalender sollte zwei Monate anzeigen, 
2a)Eventreihen sollten mehr anzeigen
1b)TicketSystem (falls Probleme oder sonstwas an Admins/Offis),
1c)Temporäre Voice channels (https://github.com/Androz2091/discord-temp-channels/tree/master) Über anderen Code korrigiert
Verwendung von PyV8 oder PyExecJS:


Bibliotheken wie PyV8 oder PyExecJS erlauben es, JavaScript direkt in Python auszuführen.


Issues : 
    a)Daten sind verschoben um einen Tag
    1b) Kalender des Folgemonats zeigt aktuellen Tag an obwohl noch nicht im Kalender
    1c)Es werden zwei Dropdown Menüs gepostet
Lösung :
    a)Anordnung der Tage ist geändert
    1b) Im Folgemonat wird kein aktueller Tag mehr angezeigt


Implementierung der Greetings.py zwecks Zufälliger Begrüssung
Es soll eine zufällige Ausgabe verschiedener Begrüßungen in Form einer eingebetteten Nachricht 
geschehen welche bei Beitritt ins Discord gesendet wird. Als Cog deklariert und abgeändert 
Hierzu ist eine Verknüpfung mit Maria DB Notwendig. 
Erste Tests mit Ausgabe der Datensätze in Konsole funktionieren,nach Anpassungen(die Funktionalität der Konsolenausgabe von der conn_db in die greettest ausgelagert) 
Issues :
a) die Ausgabe erfolgt nicht
b) keine Verbindung zur DB

Lösung : 
a) Umändern des Codes, auslagern der Datenbank verbindung in die conn_db
b) Umgebungsvariablen angepasst 

Raspberry Installationsprogramme
Python3
bestehende PiPs

(LeveL System Befehle)
/level ephermal Message
/rangliste

Tickets
/bewerbung ephermal Message
/ticket     ephermal Message

/post_calendar_now

(RAID)
!addraid
!listraids
!nextraid


Für Installation der pips falls Raspberry streikt:
sudo apt install python3-name der anwendung