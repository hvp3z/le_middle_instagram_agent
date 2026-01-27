"""
Classe abstraite de base pour tous les générateurs d'images
"""
from abc import ABC, abstractmethod
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from config.settings import (
    FONTS_DIR,
    GENERATED_DIR,
    IMAGE_SIZE,
    COLORS,
    TAGLINE,
    hex_to_rgb,
)


class BaseGenerator(ABC):
    """Classe de base pour la génération d'images Instagram."""

    def __init__(self):
        self.width, self.height = IMAGE_SIZE
        self.fonts_cache: dict[str, ImageFont.FreeTypeFont] = {}
        GENERATED_DIR.mkdir(exist_ok=True)

    def load_font(self, font_name: str, size: int) -> ImageFont.FreeTypeFont:
        """Charge une police avec mise en cache."""
        cache_key = f"{font_name}_{size}"
        if cache_key not in self.fonts_cache:
            font_path = FONTS_DIR / font_name
            if font_path.exists():
                self.fonts_cache[cache_key] = ImageFont.truetype(str(font_path), size)
            else:
                # Fallback sur une police système
                print(f"Warning: Font {font_name} not found, using default")
                self.fonts_cache[cache_key] = ImageFont.load_default()
        return self.fonts_cache[cache_key]

    def create_gradient(
        self,
        width: int,
        height: int,
        color_start: str,
        color_end: str,
        direction: str = "vertical",
    ) -> Image.Image:
        """Crée une image avec un dégradé."""
        gradient = Image.new("RGB", (width, height))
        
        r1, g1, b1 = hex_to_rgb(color_start)
        r2, g2, b2 = hex_to_rgb(color_end)
        
        for i in range(height if direction == "vertical" else width):
            ratio = i / (height if direction == "vertical" else width)
            r = int(r1 + (r2 - r1) * ratio)
            g = int(g1 + (g2 - g1) * ratio)
            b = int(b1 + (b2 - b1) * ratio)
            
            if direction == "vertical":
                for j in range(width):
                    gradient.putpixel((j, i), (r, g, b))
            else:
                for j in range(height):
                    gradient.putpixel((i, j), (r, g, b))
        
        return gradient

    def center_text(
        self,
        draw: ImageDraw.ImageDraw,
        text: str,
        font: ImageFont.FreeTypeFont,
        y: int,
        color: tuple[int, int, int],
    ) -> None:
        """Centre un texte horizontalement."""
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        x = (self.width - text_width) // 2
        draw.text((x, y), text, font=font, fill=color)

    def wrap_text(
        self,
        text: str,
        font: ImageFont.FreeTypeFont,
        max_width: int,
        draw: ImageDraw.ImageDraw,
    ) -> list[str]:
        """Découpe le texte en lignes pour tenir dans une largeur max."""
        words = text.split()
        lines = []
        current_line = ""

        for word in words:
            test_line = f"{current_line} {word}".strip()
            bbox = draw.textbbox((0, 0), test_line, font=font)
            if bbox[2] - bbox[0] <= max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word

        if current_line:
            lines.append(current_line)

        return lines

    def add_tagline(
        self,
        draw: ImageDraw.ImageDraw,
        font: ImageFont.FreeTypeFont,
        color: tuple[int, int, int],
        y_offset: int = 100,
    ) -> None:
        """Ajoute la tagline en bas de l'image."""
        self.center_text(draw, TAGLINE, font, self.height - y_offset, color)

    @abstractmethod
    def generate(self, content: dict) -> Image.Image:
        """Génère l'image à partir du contenu."""
        pass

    def save(self, image: Image.Image, filename: str) -> Path:
        """Sauvegarde l'image générée."""
        output_path = GENERATED_DIR / filename
        image.save(output_path, "PNG", quality=95)
        return output_path

    def preview(self, image: Image.Image) -> None:
        """Affiche un aperçu de l'image."""
        image.show()
