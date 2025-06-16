import discord
from discord.ext import commands
from ..model.level_model import UserData
from ..view.level_view import LevelCardView

class LevelController(commands.Cog):
    def __init__(self, bot, pool):
        self.bot = bot
        self.user_data = UserData(pool)
        self.level_view = LevelCardView()

    async def generate_level_card(self, interaction, user_id):
        xp, level = await self.user_data.get_or_create_user(
            user_id, interaction.user.name, interaction.guild.name
        )
        file = await self.level_view.generate_level_card(interaction.user, level, xp)
        return file

    async def generate_leaderboard(self, interaction):
        top_users = await self.user_data.get_top_users()
        embed, file = await self.level_view.generate_leaderboard(top_users, interaction, self.user_data)
        return embed, file

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        user_id = message.author.id
        discord_name = message.author.name
        server_name = message.guild.name
        level_up, level = await self.add_xp(user_id, 5, discord_name, server_name)
        if level_up:
            await message.channel.send(
                f"Glückwunsch {message.author.mention}, du bist jetzt Level {level}!"
            )

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        if user.bot:
            return

        print(f"Reaction added by {user.name} on message: {reaction.message.id}")

        user_id = user.id
        discord_name = user.name
        server_name = reaction.message.guild.name
        level_up, level = await self.add_xp(user_id, 3, discord_name, server_name)
        if level_up:
            await reaction.message.channel.send(
                f"Glückwunsch {user.mention}, du bist jetzt Level {level}!"
            )
        else:
            print(f"Added 3 XP to {user.name}, but no level up.")

    @discord.app_commands.command(name="level", description="Zeige deine Levelkarte an")
    async def level(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        user_id = interaction.user.id
        file = await self.generate_level_card(interaction, user_id)
        await interaction.followup.send(file=file, ephemeral=True)

    @discord.app_commands.command(name="rangliste", description="Zeige die Rangliste der Top 10 Benutzer")
    async def rangliste(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        embed, file = await self.generate_leaderboard(interaction)
        if file:
            await interaction.followup.send(embed=embed, file=file, ephemeral=True)
        else:
            await interaction.followup.send(embed=embed, ephemeral=True)

    async def add_xp(self, user_id, amount, discord_name, server_name):
        print(f"Adding {amount} XP to user {user_id}")

        xp, level = await self.user_data.get_or_create_user(user_id, discord_name, server_name)
        new_xp = xp + amount
        needed_xp = 100 * level * level

        if new_xp >= needed_xp:
            new_xp -= needed_xp
            level += 1
            await self.user_data.update_user_level(user_id, new_xp, level)
            print(f"User {user_id} leveled up to {level}")
            return True, level
        else:
            await self.user_data.update_user_xp(user_id, new_xp)
            print(f"Updated XP for user {user_id} to {new_xp}")
            return False, level

async def setup(bot):
    if not hasattr(bot, 'pool'):
        print("Error: Database pool not found in bot.")
        return

    controller = LevelController(bot, bot.pool)
    await controller.user_data.create_table()
    await bot.add_cog(controller)
    await bot.tree.sync()
