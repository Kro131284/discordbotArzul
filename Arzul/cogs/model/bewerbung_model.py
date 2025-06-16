import discord

class Application:
    def __init__(self, user, hopes, values, role):
        self.user = user
        self.hopes = hopes
        self.values = values
        self.role = role

    def generate_embed(self):
        embed = discord.Embed(
            title=f"Bewerbung von {self.user}",
            color=discord.Color.blue()
        )
        embed.add_field(name="Hoffnungen", value=self.hopes, inline=False)
        embed.add_field(name="Werte", value=self.values, inline=False)
        embed.add_field(name="Rolle", value=self.role, inline=False)
        embed.set_footer(
            text=f"Eingereicht von {self.user}",
            icon_url=self.user.avatar.url if self.user.avatar else discord.Embed.Empty
        )
        return embed
