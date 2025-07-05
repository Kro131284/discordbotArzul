import discord
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageFilter
from io import BytesIO
import os
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class LevelCardView:
    def __init__(self, font_path="arial.ttf", background_path=None):
        def load_font(path, size):
            try:
                return ImageFont.truetype(str(path), size)
            except OSError:
                logger.warning(f"Font '{path}' nicht gefunden. Nutze Standard-Font.")
                return ImageFont.load_default()

        base_dir = Path(__file__).parent
        self.font_path_actual = base_dir / font_path if not Path(font_path).is_absolute() else Path(font_path)

        self.font_large = load_font(self.font_path_actual, 36)
        self.font_medium = load_font(self.font_path_actual, 28)
        self.font_small = load_font(self.font_path_actual, 22)
        self.font_leaderboard_large = load_font(self.font_path_actual, 48)
        self.font_leaderboard_small = load_font(self.font_path_actual, 28)
        self.font_leaderboard_username_tag = load_font(self.font_path_actual, 20)

        self.background_path = Path(background_path) if background_path else Path("/home/kro/Arzul/assets/img/rat.png")
        self.avatar_cache = {}
        self.output_dir = Path("output")
        self.output_dir.mkdir(exist_ok=True)

        default = Image.new("RGBA", (64, 64), (255, 255, 255, 0))
        mask = Image.new("L", (64, 64), 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0, 64, 64), fill=255)
        self.default_avatar_template = ImageOps.fit(default, mask.size, centering=(0.5, 0.5))
        self.default_avatar_template.putalpha(mask)

    async def create_profile_picture(self, avatar_asset: discord.Asset, size=180) -> Image.Image:
        if avatar_asset is None:
            logger.debug("Avatar Asset is None. Returning default avatar.")
            return self.default_avatar_template.resize((size, size), Image.LANCZOS)

        key = getattr(avatar_asset, 'url', None)
        if key in self.avatar_cache:
            return self.avatar_cache[key]

        try:
            data = await avatar_asset.read()
            img = Image.open(BytesIO(data)).convert("RGBA").resize((size, size), Image.LANCZOS)

            mask = Image.new('L', (size, size), 0)
            draw = ImageDraw.Draw(mask)
            draw.ellipse((0, 0, size, size), fill=255)
            img = ImageOps.fit(img, mask.size, centering=(0.5, 0.5))
            img.putalpha(mask)

            self.avatar_cache[key] = img
            return img
        except Exception as e:
            logger.warning(f"Fehler beim Laden des Avatars von '{key}': {e}")
            return self.default_avatar_template.resize((size, size), Image.LANCZOS)

    async def generate_level_card(self, member: discord.Member, level: int, xp: int) -> discord.File:
        try:
            bg = Image.open(self.background_path).convert("RGBA")
        except Exception as e:
            logger.error(f"Fehler beim Laden des Hintergrunds '{self.background_path}': {e}")
            bg = Image.new("RGBA", (800, 400), (40, 40, 40, 255))

        img = ImageOps.fit(bg, (800, 400), centering=(0.5, 0.5))
        draw = ImageDraw.Draw(img)

        avatar_size = 180
        avatar = await self.create_profile_picture(member.display_avatar, size=avatar_size)
        avatar_x, avatar_y = 50, 110

        border_thickness = 8
        border_size = avatar_size + 2 * border_thickness
        border_img = Image.new("RGBA", (border_size, border_size), (128, 0, 128, 255))
        inner_circle = Image.new("L", (avatar_size, avatar_size), 0)
        ImageDraw.Draw(inner_circle).ellipse((0, 0, avatar_size, avatar_size), fill=255)
        mask = Image.new("L", (border_size, border_size), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, border_size, border_size), fill=255)
        border_img.putalpha(mask)
        img.paste(border_img, (avatar_x - border_thickness, avatar_y - border_thickness), border_img)
        img.paste(avatar, (avatar_x, avatar_y), avatar)

        text_x = 250
        y_offset = 20
        neon_green = (57, 255, 20, 255)

        draw.text((text_x, avatar_y + y_offset), member.display_name, font=self.font_large, fill=neon_green)
        y_offset += self.font_large.getbbox(member.display_name)[3] + 10
        draw.text((text_x, avatar_y + y_offset), f"@{member.name}", font=self.font_small, fill=(200, 200, 200))
        y_offset += self.font_small.getbbox(f"@{member.name}")[3] + 15
        draw.text((text_x, avatar_y + y_offset), f"Level {level}", font=self.font_medium, fill=(255, 255, 255))

        needed_xp = max(1, 100 * level * level)
        progress_ratio = min(1.0, xp / needed_xp)
        filled_width = int(450 * progress_ratio)

        bar_y = avatar_y + y_offset + 40
        bar_x = text_x
        bar_width = 450
        bar_height = 40

        draw.rectangle([bar_x, bar_y, bar_x + bar_width, bar_y + bar_height], fill=(40, 40, 40), outline=(100, 100, 100), width=2)
        draw.rectangle([bar_x + 2, bar_y + 2, bar_x + filled_width - 2, bar_y + bar_height - 2], fill=(128, 0, 128))

        xp_text = f"{xp} / {needed_xp} XP"
        percent_text = f"{int(progress_ratio * 100)}%"

        draw.text((bar_x + 10, bar_y + 8), xp_text, font=self.font_small, fill=neon_green)
        percent_text_width = self.font_small.getbbox(percent_text)[2]
        draw.text((bar_x + bar_width - percent_text_width - 10, bar_y + 8), percent_text, font=self.font_small, fill=neon_green)

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
        image_height = 120 + row_height * len(top_users)
        board = Image.new("RGBA", (image_width, image_height), (40, 40, 40, 255))

        try:
            bg = Image.open(self.background_path).convert("RGBA")
            bg = bg.resize((image_width, image_height), Image.LANCZOS)
            board.paste(bg, (0, 0))
        except Exception as e:
            logger.warning(f"Kein gültiger Hintergrund für Leaderboard: {e}")

        draw = ImageDraw.Draw(board)
        title = "Top 10 Benutzer nach Level und XP"
        title_width = self.font_leaderboard_large.getbbox(title)[2]
        draw.text(((image_width - title_width) // 2, 20), title, font=self.font_leaderboard_large, fill=(255, 255, 255))

        y = 100
        for idx, (user_id, xp, level) in enumerate(top_users, start=1):
            member = interaction.guild.get_member(user_id)
            display_name = member.display_name if member else f"Unbekannt ({user_id})"
            username = member.name if member else ""
            avatar_asset = member.display_avatar if member else None

            if not member and user_data:
                stored_name, avatar_url = await user_data.get_user_name_and_avatar(user_id)
                display_name = stored_name or display_name
                if avatar_url:
                    try:
                        avatar_asset = discord.Asset._from_uri(interaction.client._connection, avatar_url)
                    except Exception as e:
                        logger.warning(f"Asset-Erstellung fehlgeschlagen für {avatar_url}: {e}")

            avatar_img = await self.create_profile_picture(avatar_asset, size=70)
            board.paste(avatar_img, (80, y + 10), avatar_img)

            draw.text((160, y), display_name, font=self.font_leaderboard_small, fill=(57, 255, 20))
            if username:
                draw.text((160, y + 30), f"@{username}", font=self.font_leaderboard_username_tag, fill=(200, 200, 200))
            draw.text((160, y + 55), f"Level {level} – {xp} XP", font=self.font_small, fill=(255, 255, 255))

            draw.text((20, y + 25), f"{idx}.", font=self.font_leaderboard_large, fill=(255, 215, 0))
            y += row_height

        buf = BytesIO()
        board.save(buf, format="PNG")
        buf.seek(0)

        embed = discord.Embed(
            title="Top 10 Benutzer nach Level und XP",
            color=discord.Color.gold()
        )
        embed.set_image(url="attachment://leaderboard.png")
        embed.set_footer(text="Rangliste")
        return embed, discord.File(fp=buf, filename="leaderboard.png")
