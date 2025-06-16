# welcome_view.py
import discord

class WelcomeView:
    @staticmethod
    def create_welcome_embed(member, greeting):
        """Erstellt das Embed mit der Begrüßungsnachricht."""
        embed = discord.Embed(
            description=f"Willkommen, {member.name}!",
            color=0x00ff00
        )
        embed.set_thumbnail(url=member.avatar.url)

        # Sicherstellen, dass {name} enthalten ist
        if "{name}" not in greeting:
            greeting += " {name}"

        formatted_greeting = f"**{greeting.format(name=member.name)}**"
        embed.set_footer(text=formatted_greeting)
        return embed

class WelcomeModal(discord.ui.Modal, title="Gebe einen individuellen Gruss ein"):
    def __init__(self, bot, pool_initialized_event):
        super().__init__()
        self.bot = bot
        self.pool_initialized = pool_initialized_event

        self.message = discord.ui.TextInput(
            label="Willkommensnachricht",
            style=discord.TextStyle.long,
            placeholder="Gebe hier deine Begrüßung ein... z.B. 'Willkommen auf dem Server, {name}!'",
            max_length=200
        )
        self.add_item(self.message)

    async def on_submit(self, interaction: discord.Interaction):
        """Verarbeitet die übermittelte Begrüßungsnachricht und speichert sie in der Datenbank."""
        await self.pool_initialized.wait()

        if not hasattr(self.bot, 'pool'):
            await interaction.response.send_message(
                "Datenbankverbindung ist noch nicht bereit. Versuche es später erneut.",
                ephemeral=True
            )
            return

        message_content = self.message.value

        # Eingabe validieren: {name} muss enthalten sein
        if "{name}" not in message_content:
            await interaction.response.send_message(
                "Deine Nachricht muss den Platzhalter `{name}` enthalten, damit der Name des neuen Mitglieds angezeigt wird.",
                ephemeral=True
            )
            return

        async with self.bot.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                user_name = interaction.user.name
                query = 'INSERT INTO greetings (message, author_username) VALUES (%s, %s)'
                await cursor.execute(query, (message_content, user_name))

        await interaction.response.send_message(
            "Deine Begrüßungsnachricht wurde erfolgreich gespeichert!",
            ephemeral=True
        )