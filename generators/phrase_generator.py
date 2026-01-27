"""
Générateur d'images pour les posts de type "Phrase"
Layout: Fond dégradé corail/rose, carte blanche arrondie avec texte
"""
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
from generators.base_generator import BaseGenerator
from config.settings import (
    FONTS,
    FONT_SIZES,
    COLORS,
    PHRASE_BG_GRADIENT,
    hex_to_rgb,
    LOGO_DIR,
)


class PhraseGenerator(BaseGenerator):
    """Génère les visuels pour les posts de type 'Phrase'."""

    def __init__(self):
        super().__init__()
        self.gradient_colors = [hex_to_rgb(c) for c in PHRASE_BG_GRADIENT]
        self.card_color = hex_to_rgb(COLORS["white"])
        self.text_color = hex_to_rgb(COLORS["black"])
        self.tagline_color = hex_to_rgb(COLORS["white"])
        
        # Dimensions de la carte (ajustées pour correspondre à l'exemple)
        self.card_padding_h = 40  # Padding horizontal
        self.card_padding_v = 30  # Padding vertical
        self.card_width = int(self.width * 0.80)  # Légèrement plus étroite
        self.card_radius = 20  # Coins légèrement moins arrondis

    def create_gradient_background(self) -> Image.Image:
        """Crée le fond dégradé corail vers rose (diagonal du coin supérieur gauche)."""
        img = Image.new("RGB", (self.width, self.height))
        
        color_start = self.gradient_colors[0]
        color_end = self.gradient_colors[1]
        
        # Dégradé diagonal (du coin supérieur gauche vers le bas droite)
        for y in range(self.height):
            for x in range(self.width):
                # Ratio basé sur la diagonale
                ratio = (x / self.width * 0.3 + y / self.height * 0.7)
                ratio = min(1.0, max(0.0, ratio))
                
                r = int(color_start[0] + (color_end[0] - color_start[0]) * ratio)
                g = int(color_start[1] + (color_end[1] - color_start[1]) * ratio)
                b = int(color_start[2] + (color_end[2] - color_start[2]) * ratio)
                
                img.putpixel((x, y), (r, g, b))
        
        return img

    def create_rounded_rectangle_mask(
        self, width: int, height: int, radius: int
    ) -> Image.Image:
        """Crée un masque pour un rectangle arrondi."""
        mask = Image.new("L", (width, height), 0)
        draw = ImageDraw.Draw(mask)
        draw.rounded_rectangle(
            [(0, 0), (width - 1, height - 1)],
            radius=radius,
            fill=255
        )
        return mask

    def draw_white_card(
        self, img: Image.Image, x: int, y: int, width: int, height: int
    ) -> None:
        """Dessine la carte blanche avec coins arrondis."""
        # Créer une carte blanche
        card = Image.new("RGBA", (width, height), (*self.card_color, 255))
        
        # Créer le masque arrondi
        mask = self.create_rounded_rectangle_mask(width, height, self.card_radius)
        
        # Appliquer le masque
        card.putalpha(mask)
        
        # Coller sur l'image principale
        img.paste(card, (x, y), card)

    def calculate_text_height(
        self, text: str, font: ImageFont.FreeTypeFont, max_width: int, draw: ImageDraw.ImageDraw
    ) -> tuple[list[str], int]:
        """
        Calcule la hauteur totale du texte wrappé.
        Retourne (lignes, hauteur_totale).
        """
        lines = self.wrap_text(text, font, max_width, draw)
        bbox = draw.textbbox((0, 0), "Ay", font=font)
        line_height = int((bbox[3] - bbox[1]) * 1.35)
        total_height = line_height * len(lines)
        return lines, total_height, line_height

    def draw_card_header(
        self, draw: ImageDraw.ImageDraw, card_x: int, card_y: int, card_width: int
    ) -> int:
        """
        Dessine le header de la carte (logo + lemiddle.app + ...).
        Retourne la hauteur du header.
        """
        header_padding_top = 30
        logo_size = 38
        
        # Texte "lemiddle.app" (Satoshi Bold)
        font_header = self.load_font("Satoshi-Bold.otf", FONT_SIZES["phrase"]["header"])
        
        # Les trois points horizontaux (menu)
        dots_x = card_x + card_width - self.card_padding_h - 25
        dots_y = card_y + header_padding_top + 8
        draw.text((dots_x, dots_y), "•••", font=font_header, fill=self.text_color)
        
        return header_padding_top + logo_size + 25  # Hauteur totale du header

    def generate(self, content: dict) -> Image.Image:
        """
        Génère l'image pour un post de type "Phrase".
        
        Args:
            content: Dictionnaire avec les clés:
                - text: Le texte de la phrase
        """
        # Créer le fond dégradé
        img = self.create_gradient_background()
        img = img.convert("RGBA")
        draw = ImageDraw.Draw(img)
        
        # Texte principal de la phrase (Satoshi Regular - sans-serif)
        phrase_text = content.get("text", "")
        font_text = self.load_font("Satoshi-Regular.otf", FONT_SIZES["phrase"]["text"])
        
        # Calculer la taille du texte pour adapter la carte
        text_max_width = self.card_width - (self.card_padding_h * 2)
        lines, text_total_height, line_height = self.calculate_text_height(
            phrase_text, font_text, text_max_width, draw
        )
        
        # Calculer la hauteur de la carte (s'adapte au contenu)
        header_height = 80  # Espace pour logo + lemiddle.app (réduit)
        text_area_padding = 40  # Padding autour du texte
        card_height = header_height + text_total_height + text_area_padding + self.card_padding_v
        
        # Position de la carte (centrée horizontalement et verticalement)
        card_x = (self.width - self.card_width) // 2
        # Position verticale : centrée dans l'espace au-dessus de la tagline
        # Laisser de l'espace pour la tagline en bas (environ 150px)
        available_height = self.height - 150  # Espace au-dessus de la tagline
        card_y = (available_height - card_height) // 2
        
        # Dessiner la carte blanche
        self.draw_white_card(img, card_x, card_y, self.card_width, card_height)
        
        # Redessiner le draw après modification de l'image
        draw = ImageDraw.Draw(img)
        
        # Ajouter le logo sur la carte
        logo_path = LOGO_DIR / "logo_black.png"
        logo_size = 34  # Légèrement plus petit
        header_top_padding = 25
        if logo_path.exists():
            logo = Image.open(logo_path).convert("RGBA")
            logo = logo.resize((logo_size, logo_size), Image.Resampling.LANCZOS)
            logo_x = card_x + self.card_padding_h
            logo_y = card_y + header_top_padding
            img.paste(logo, (logo_x, logo_y), logo)
        else:
            logo_x = card_x + self.card_padding_h
            logo_y = card_y + header_top_padding
        
        # Texte "lemiddle.app" à côté du logo (Satoshi Bold)
        font_header = self.load_font("Satoshi-Bold.otf", FONT_SIZES["phrase"]["header"])
        text_header_x = logo_x + logo_size + 10
        text_header_y = card_y + header_top_padding + 6  # Centré verticalement avec le logo
        draw = ImageDraw.Draw(img)
        draw.text((text_header_x, text_header_y), "lemiddle.app", font=font_header, fill=self.text_color)
        
        # Les trois points horizontaux (espacés comme dans l'exemple de référence)
        dot_size = 5
        dot_spacing = 8  # Espacement entre les centres des points
        dots_total_width = dot_size * 3 + dot_spacing * 2
        dots_x = card_x + self.card_width - self.card_padding_h - dots_total_width
        dot_y = card_y + header_top_padding + 12  # Aligné avec le texte header
        for i in range(3):
            x = dots_x + i * (dot_size + dot_spacing)
            draw.ellipse(
                [(x, dot_y), (x + dot_size, dot_y + dot_size)],
                fill=self.text_color
            )
        
        # Zone de texte dans la carte
        text_area_top = card_y + header_height
        text_area_bottom = card_y + card_height - self.card_padding_v
        text_area_height = text_area_bottom - text_area_top
        
        # Le texte est aligné en haut de la zone de texte (pas centré)
        text_start_y = text_area_top
        text_x = card_x + self.card_padding_h
        
        # Dessiner le texte sur plusieurs lignes (aligné à gauche)
        current_y = text_start_y
        for line in lines:
            draw.text((text_x, current_y), line, font=font_text, fill=self.text_color)
            current_y += line_height
        
        # Tagline en bas (Libre Baskerville Italic - signature élégante)
        font_tagline = self.load_font("LibreBaskerville-Italic.ttf", FONT_SIZES["phrase"]["tagline"])
        self.add_tagline(draw, font_tagline, self.tagline_color, y_offset=100)
        
        return img.convert("RGB")


# Test rapide
if __name__ == "__main__":
    generator = PhraseGenerator()
    
    test_content = {
        "text": "\"On se retrouve au milieu ?\" La phrase qui a sauvé 1000 amitiés."
    }
    
    image = generator.generate(test_content)
    output_path = generator.save(image, "test_phrase.png")
    print(f"Image saved to: {output_path}")
    generator.preview(image)
