import discord

class TicketModel:
    def __init__(self, user, title, description, guild, support_roles):
        self.user = user
        self.title = title
        self.description = description
        self.guild = guild
        self.support_roles = support_roles

    def get_ticket_channel_name(self):
        return f"ticket-{self.user.name}-{self.user.discriminator}"

    def get_overwrites(self):
        overwrites = {
            self.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            self.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        }
        for role in self.support_roles:
            overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
        return overwrites

    async def create_ticket_channel(self):
        channel_name = self.get_ticket_channel_name()
        overwrites = self.get_overwrites()
        return await self.guild.create_text_channel(channel_name, overwrites=overwrites)
