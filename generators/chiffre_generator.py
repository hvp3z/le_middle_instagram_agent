"""
Générateur d'images pour les posts de type "Chiffre"
Layout: Fond crème, chiffre géant avec dégradé, texte contextuel
"""
from PIL import Image, ImageDraw, ImageFont
import numpy as np
from generators.base_generator import BaseGenerator
from config.settings import (
    FONTS,
    FONT_SIZES,
    COLORS,
    CHIFFRE_GRADIENT,
    hex_to_rgb,
    get_color_rgb,
    FONTS_DIR,
)


class ChiffreGenerator(BaseGenerator):
    """Génère les visuels pour les posts de type 'Chiffre'."""

    def __init__(self):
        super().__init__()
        self.bg_color = hex_to_rgb(COLORS["cream_bg"])
        self.text_color = hex_to_rgb(COLORS["black"])
        self.tagline_color = hex_to_rgb(COLORS["coral_dark"])
        self.gradient_colors = [hex_to_rgb(c) for c in CHIFFRE_GRADIENT]

    def _find_optimal_font_size(
        self,
        text: str,
        font_name: str,
        target_height_ratio: float = 0.30,
        target_width_ratio: float = 0.28,
    ) -> ImageFont.FreeTypeFont:
        """
        Trouve la taille de police optimale pour que le texte occupe
        environ target_height_ratio de la hauteur et target_width_ratio de la largeur.
        
        Retourne la police avec la taille optimale.
        """
        target_height = int(self.height * target_height_ratio)
        target_width = int(self.width * target_width_ratio)
        
        # Créer une image temporaire pour mesurer
        temp_img = Image.new("RGBA", (1, 1), (0, 0, 0, 0))
        temp_draw = ImageDraw.Draw(temp_img)
        
        # Recherche binaire pour trouver la taille optimale
        min_size = 50
        max_size = 1000
        best_font = None
        best_score = float('inf')
        
        # On cherche la taille qui minimise l'écart par rapport aux deux cibles
        for size in range(min_size, max_size + 1, 5):
            font = self.load_font(font_name, size)
            bbox = temp_draw.textbbox((0, 0), text, font=font)
            text_height = bbox[3] - bbox[1]
            text_width = bbox[2] - bbox[0]
            
            # Calculer l'écart relatif par rapport aux cibles
            height_diff = abs(text_height - target_height) / target_height
            width_diff = abs(text_width - target_width) / target_width
            
            # Score combiné (on peut pondérer différemment si besoin)
            score = height_diff + width_diff
            
            # On garde la taille qui minimise l'écart total
            # Mais on s'arrête si on dépasse trop les limites (plus de 5% d'écart)
            if height_diff > 0.05 or width_diff > 0.05:
                if best_font is None:
                    # Si on n'a pas encore trouvé de bonne taille, on continue
                    continue
                else:
                    # Sinon, on s'arrête car on a dépassé les limites
                    break
            
            if score < best_score:
                best_score = score
                best_font = font
        
        # Si on n'a pas trouvé de taille parfaite, on prend la plus grande qui respecte les limites
        if best_font is None:
            for size in range(min_size, max_size + 1, 10):
                font = self.load_font(font_name, size)
                bbox = temp_draw.textbbox((0, 0), text, font=font)
                text_height = bbox[3] - bbox[1]
                text_width = bbox[2] - bbox[0]
                
                if text_height <= target_height and text_width <= target_width:
                    best_font = font
                else:
                    break
        
        return best_font if best_font is not None else self.load_font(font_name, 350)

    def create_gradient_text(
        self,
        text: str,
        font: ImageFont.FreeTypeFont,
        gradient_start: tuple[int, int, int],
        gradient_end: tuple[int, int, int],
    ) -> Image.Image:
        """
        Crée un texte avec un dégradé vertical.
        
        Technique:
        1. Créer une image du texte en blanc sur fond transparent
        2. Créer une image dégradé de la même taille
        3. Utiliser le texte comme masque pour le dégradé
        """
        # Créer une image temporaire pour mesurer le texte
        temp_img = Image.new("RGBA", (1, 1), (0, 0, 0, 0))
        temp_draw = ImageDraw.Draw(temp_img)
        bbox = temp_draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        # Ajouter du padding
        padding = 20
        img_width = text_width + padding * 2
        img_height = text_height + padding * 2
        
        # Créer l'image du texte (masque alpha)
        text_img = Image.new("L", (img_width, img_height), 0)
        text_draw = ImageDraw.Draw(text_img)
        # Ajuster la position pour compenser le bbox offset
        text_x = padding - bbox[0]
        text_y = padding - bbox[1]
        text_draw.text((text_x, text_y), text, font=font, fill=255)
        
        # Créer le dégradé
        gradient = self._create_vertical_gradient(
            img_width, img_height, gradient_start, gradient_end
        )
        
        # Appliquer le masque
        result = Image.new("RGBA", (img_width, img_height), (0, 0, 0, 0))
        result.paste(gradient, mask=text_img)
        
        return result

    def _create_vertical_gradient(
        self,
        width: int,
        height: int,
        color_start: tuple[int, int, int],
        color_end: tuple[int, int, int],
    ) -> Image.Image:
        """Crée un dégradé vertical optimisé."""
        # Utiliser numpy pour la performance
        gradient = np.zeros((height, width, 3), dtype=np.uint8)
        
        for i in range(height):
            ratio = i / max(height - 1, 1)
            r = int(color_start[0] + (color_end[0] - color_start[0]) * ratio)
            g = int(color_start[1] + (color_end[1] - color_start[1]) * ratio)
            b = int(color_start[2] + (color_end[2] - color_start[2]) * ratio)
            gradient[i, :] = [r, g, b]
        
        return Image.fromarray(gradient, "RGB")

    def generate(self, content: dict) -> Image.Image:
        """
        Génère l'image pour un post de type "Chiffre".
        
        Args:
            content: Dictionnaire avec les clés:
                - context_text: Texte contextuel en haut
                - number: Le chiffre à afficher
                - unit_text: Unité/texte en bas du chiffre
        """
        # Créer l'image de fond
        img = Image.new("RGB", (self.width, self.height), self.bg_color)
        draw = ImageDraw.Draw(img)
        
        # Extraire le contenu d'abord
        context_text = content.get("context_text", "")
        number = content.get("number", "0")
        unit_text = content.get("unit_text", "")
        
        # Charger les fonts - Satoshi (sans-serif) + Libre Baskerville (serif)
        font_context = self.load_font("Satoshi-Regular.otf", FONT_SIZES["chiffre"]["context"])  # Texte haut
        
        # Calculer dynamiquement la taille de police du nombre pour respecter les proportions
        # 60% de la hauteur et 56% de la largeur (2x plus gros)
        font_number = self._find_optimal_font_size(
            number,
            "LibreBaskerville-Regular.ttf",
            target_height_ratio=0.60,
            target_width_ratio=0.56,
        )
        
        font_unit = self.load_font("Satoshi-Regular.otf", FONT_SIZES["chiffre"]["unit"])  # "minutes d'attente"
        font_tagline = self.load_font("LibreBaskerville-Regular.ttf", FONT_SIZES["chiffre"]["tagline"])  # Slogan
        
        # === LAYOUT BASÉ SUR L'IMAGE DE RÉFÉRENCE ===
        # L'image de référence a une structure très précise :
        # - Texte contextuel commence à environ 12% du haut
        # - Le chiffre est centré verticalement dans l'espace principal
        # - L'unité est juste en dessous du chiffre
        # - La tagline est à environ 165px du bas
        
        # === TEXTE CONTEXTUEL EN HAUT (centré) ===
        context_y = int(self.height * 0.12)
        context_end_y = self._draw_centered_multiline(
            draw, context_text, font_context, self.text_color, 
            context_y, max_width=int(self.width * 0.85)
        )
        
        # === CHIFFRE AVEC DÉGRADÉ AU CENTRE ===
        gradient_text_img = self.create_gradient_text(
            number,
            font_number,
            self.gradient_colors[0],
            self.gradient_colors[1],
        )
        
        # Utiliser un espace fixe pour équilibrer les marges autour du chiffre
        spacing = 50  # Espace égal au-dessus et en-dessous du chiffre
        
        # Positionner le chiffre avec l'espace calculé
        number_y = context_end_y + spacing
        
        # Centrer le chiffre horizontalement
        number_x = (self.width - gradient_text_img.width) // 2
        img.paste(gradient_text_img, (number_x, number_y), gradient_text_img)
        
        # === TEXTE UNITÉ EN BAS DU CHIFFRE (retour à la ligne si trop long) ===
        unit_y = number_y + gradient_text_img.height + spacing
        self._draw_centered_multiline(
            draw, unit_text, font_unit, self.text_color,
            unit_y, max_width=int(self.width * 0.85)
        )
        
        # === TAGLINE EN BAS ===
        self.add_tagline(draw, font_tagline, self.tagline_color, y_offset=165)
        
        return img

    def _draw_centered_multiline(
        self,
        draw: ImageDraw.ImageDraw,
        text: str,
        font: ImageFont.FreeTypeFont,
        color: tuple[int, int, int],
        start_y: int,
        max_width: int,
        line_spacing: float = 1.3,
    ) -> int:
        """
        Dessine du texte centré sur plusieurs lignes.
        Retourne la position Y après le dernier texte.
        """
        lines = self.wrap_text(text, font, max_width, draw)
        
        # Calculer la hauteur d'une ligne
        bbox = draw.textbbox((0, 0), "Ay", font=font)
        line_height = int((bbox[3] - bbox[1]) * line_spacing)
        
        current_y = start_y
        for line in lines:
            self.center_text(draw, line, font, current_y, color)
            current_y += line_height
        
        return current_y


# Test rapide
if __name__ == "__main__":
    generator = ChiffreGenerator()
    
    test_content = {
        "context_text": "On finit tous par envoyer le message \"T'es où ?\"... après",
        "number": "19",
        "unit_text": "minutes d'attente.",
    }
    
    image = generator.generate(test_content)
    output_path = generator.save(image, "test_chiffre.png")
    print(f"Image saved to: {output_path}")
    generator.preview(image)
