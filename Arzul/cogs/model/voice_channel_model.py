class VoiceChannelModel:
    def __init__(self , channel_3_id  , channel_5_id , channel_6_id, channel_12_id, channel_Raid_id):
        self.channel_3_id = channel_3_id  # ID für 3-Personen-Kanal
        self.channel_5_id = channel_5_id  # ID für 5-Personen-Kanal
        self.channel_6_id = channel_6_id  # ID für 6-Personen-Kanal
        self.channel_12_id = channel_12_id  # ID für 12-Personen-Kanal
        self.channel_Raid_id = channel_Raid_id  # ID für Raid-Personen-Kanal
        self.group_channels = []  # Dynamisch erstellte Gruppenkanäle
        self.onleave_channels = []  # Kanäle, die gelöscht werden, wenn sie leer sind

    def add_group_channel(self, channel_id):
        """Fügt einen Kanal zur Gruppenliste hinzu."""
        self.group_channels.append(channel_id)
        self.onleave_channels.append(channel_id)

    def remove_group_channel(self, channel_id):
        """Entfernt einen Kanal aus der Gruppenliste."""
        if channel_id in self.group_channels:
            self.group_channels.remove(channel_id)
        if channel_id in self.onleave_channels:
            self.onleave_channels.remove(channel_id)

    def is_group_channel(self, channel_id):
        """Prüft, ob ein Kanal ein Gruppenkanal ist."""
        return channel_id in self.group_channels

    def is_onleave_channel(self, channel_id):
        """Prüft, ob ein Kanal in der Liste der zu löschenden Kanäle ist."""
        return channel_id in self.onleave_channels
