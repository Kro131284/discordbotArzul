import discord
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageFilter
from io import BytesIO
import os
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class LevelCardView:
    def __init__(self, font_path="arial.ttf", background_path=None):
        def load_font(path, size):
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                logger.warning(f"Font {path} nicht gefunden, nutze Default.")
                return ImageFont.load_default()

        self.font_large = load_font(font_path, 36)
        self.font_medium = load_font(font_path, 28)
        self.font_small = load_font(font_path, 22)
        self.font_leaderboard_large = load_font(font_path, 48)
        self.font_leaderboard_small = load_font(font_path, 28)

        self.background_path = background_path or "/home/kro/Arzul/assets/img/rat.png"
        self.avatar_cache = {}
        self.output_dir = Path("output")
        self.output_dir.mkdir(exist_ok=True)

        # Default Avatar vorbereiten
        default = Image.new("RGBA", (64, 64), (255, 255, 255, 0))
        mask = Image.new("L", (64, 64), 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0, 64, 64), fill=255)
        self.default_avatar_round = ImageOps.fit(default, mask.size, centering=(0.5, 0.5))
        self.default_avatar_round.putalpha(mask)

    async def create_profile_picture(self, avatar_asset: discord.Asset, size=180) -> Image.Image:
        key = getattr(avatar_asset, 'url', None)
        if key in self.avatar_cache:
            return self.avatar_cache[key]

        try:
            data = await avatar_asset.read()
            img = Image.open(BytesIO(data)).convert("RGBA")
            img = img.resize((size, size), Image.LANCZOS)

            mask = Image.new('L', (size, size), 0)
            draw = ImageDraw.Draw(mask)
            draw.ellipse((0, 0, size, size), fill=255)
            img = ImageOps.fit(img, mask.size, centering=(0.5, 0.5))
            img.putalpha(mask)

            self.avatar_cache[key] = img
            return img

        except Exception as e:
            logger.warning(f"Avatar konnte nicht geladen werden ({key}): {e}")
            return self.default_avatar_round

    async def generate_level_card(self, member: discord.Member, level: int, xp: int) -> discord.File:
        try:
            bg = Image.open(self.background_path).convert("RGBA")
        except FileNotFoundError:
            logger.error(f"Hintergrund nicht gefunden: {self.background_path}")
            bg = Image.new("RGBA", (800, 400), (40, 40, 40, 255))

        base_card = ImageOps.fit(bg, (800, 400), centering=(0.5, 0.5))

        # Schattenhintergrund erzeugen
        shadow_offset = 10
        shadow = Image.new("RGBA", (base_card.width + shadow_offset * 2, base_card.height + shadow_offset * 2), (0, 0, 0, 0))
        shadow_draw = ImageDraw.Draw(shadow)
        shadow_box = [shadow_offset, shadow_offset, shadow_offset + base_card.width, shadow_offset + base_card.height]
        shadow_draw.rectangle(shadow_box, fill=(0, 0, 0, 180))
        shadow.paste(base_card, (shadow_offset, shadow_offset), base_card)
        img = shadow
        draw = ImageDraw.Draw(img)

        # Avatar mit Glow
        avatar_size = 180
        av = await self.create_profile_picture(member.display_avatar, size=avatar_size)
        avatar_pos = (40, (img.height - av.height) // 2)

        # Glow erzeugen
        glow = Image.new("RGBA", (avatar_size, avatar_size), (255, 215, 0, 0))
        glow_draw = ImageDraw.Draw(glow)
        glow_draw.ellipse((0, 0, avatar_size, avatar_size), fill=(255, 215, 0, 70))
        glow = glow.filter(ImageFilter.GaussianBlur(10))
        glow_pos = (avatar_pos[0] - 6, avatar_pos[1] - 6)

        img.paste(glow, glow_pos, glow)
        img.paste(av, avatar_pos, av)

        # Textbereich
        x = 250
        y = 100
        draw.text((x, y), f"{member.display_name}", font=self.font_large, fill=(255, 215, 0))
        y += 40
        draw.text((x, y), f"@{member.name}", font=self.font_small, fill=(200, 200, 200))
        y += 35
        draw.text((x, y), f"Level {level}", font=self.font_medium, fill=(255, 255, 255))
        y += 40
        draw.text((x, y), f"{xp} XP", font=self.font_small, fill=(255, 255, 255))

        # Fortschrittsbalken
        needed_xp = 100 * level * level
        filled = int((xp / needed_xp) * 450)
        bar_y = y + 35
        draw.rectangle([x, bar_y, x + 450, bar_y + 30], fill=(60, 60, 60))
        draw.rectangle([x, bar_y, x + filled, bar_y + 30], fill=(255, 215, 0))
        draw.text((x, bar_y + 35), f"{xp} / {needed_xp} XP", font=self.font_small, fill=(255, 255, 255))

        buf = BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return discord.File(fp=buf, filename="level_card.png")

    async def generate_leaderboard(self, top_users: list, interaction: discord.Interaction, user_data) -> tuple:
        if not top_users:
            embed = discord.Embed(
                title="Top 10 Benutzer nach Level und XP",
                description="Noch keine Benutzer in der Rangliste.",
                color=discord.Color.gold()
            )
            return embed, None

        image_width = 900
        row_height = 90
        image_height = 120 + len(top_users) * row_height
        board = Image.new("RGBA", (image_width, image_height), (40, 40, 40))
        draw = ImageDraw.Draw(board)

        title = "Top 10 Benutzer nach Level und XP"
        tw, th = draw.textsize(title, font=self.font_leaderboard_large)
        draw.text(((image_width - tw) // 2, 20), title, font=self.font_leaderboard_large, fill=(255, 255, 255))

        y = 100
        for idx, (user_id, xp, level) in enumerate(top_users, start=1):
            member = interaction.guild.get_member(user_id)
            if member:
                display_name = member.display_name
                username = member.name
                asset = member.display_avatar
            else:
                display_name, asset_url = await user_data.get_user_name_and_avatar(user_id)
                username = ''
                asset = None

            draw.text((20, y + 25), f"{idx}.", font=self.font_leaderboard_large, fill=(255, 215, 0))
            avatar_img = await self.create_profile_picture(asset) if asset else self.default_avatar_round
            board.paste(avatar_img, (80, y), avatar_img)

            name_x = 160
            draw.text((name_x, y), display_name, font=self.font_leaderboard_small, fill=(255, 215, 0))
            if username:
                draw.text((name_x, y + 30), f"@{username}", font=self.font_small, fill=(200, 200, 200))
            draw.text((name_x, y + 55), f"Level {level} – {xp} XP", font=self.font_small, fill=(255, 255, 255))

            y += row_height

        buf = BytesIO()
        board.save(buf, format="PNG")
        buf.seek(0)

        local_path = self.output_dir / "leaderboard.png"
        board.save(local_path)

        embed = discord.Embed(
            title="Top 10 Benutzer nach Level und XP",
            color=discord.Color.gold()
        )
        embed.set_image(url="attachment://leaderboard.png")
        embed.set_footer(text="Rangliste")
        return embed, discord.File(fp=buf, filename="leaderboard.png")
