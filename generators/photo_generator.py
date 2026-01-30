"""
Générateur d'images pour les posts de type "Photo"
Utilise l'API Replicate pour générer des photos AI et ajoute un overlay du logo
"""
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance
from pathlib import Path
import requests
from io import BytesIO
from generators.base_generator import BaseGenerator
from config.settings import (
    LOGO_DIR,
    hex_to_rgb,
    COLORS,
    FONT_SIZES,
)


class PhotoGenerator(BaseGenerator):
    """Génère les visuels pour les posts de type 'Photo' avec IA."""

    def __init__(self):
        super().__init__()
        self.logo_size = 800  # Taille du logo au centre
        
        # Couleur de filtre optionnel (teinte chaude)
        self.warm_filter_color = hex_to_rgb(COLORS["peach"])
        
        # Couleur de la tagline (blanc pour contraster avec les photos)
        self.tagline_color = hex_to_rgb(COLORS["white"])

    def load_image_from_url(self, url: str) -> Image.Image:
        """Charge une image depuis une URL."""
        response = requests.get(url, timeout=60)
        response.raise_for_status()
        return Image.open(BytesIO(response.content))

    def load_image_from_path(self, path: Path) -> Image.Image:
        """Charge une image depuis un chemin local."""
        return Image.open(path)

    def apply_warm_filter(
        self, img: Image.Image, intensity: float = 0.15
    ) -> Image.Image:
        """
        Applique un filtre chaud subtil à l'image.
        
        Args:
            img: Image source
            intensity: Intensité du filtre (0.0 à 1.0)
        """
        # Créer une couche de couleur chaude
        warm_overlay = Image.new("RGB", img.size, self.warm_filter_color)
        
        # Fusionner avec l'image originale
        result = Image.blend(img.convert("RGB"), warm_overlay, intensity)
        
        # Légère augmentation de la saturation
        enhancer = ImageEnhance.Color(result)
        result = enhancer.enhance(1.1)
        
        return result

    def apply_light_overlay(
        self, img: Image.Image, intensity: float = 0.35
    ) -> Image.Image:
        """
        Applique un voile clair/lumineux sur toute l'image.
        Donne un effet "faded" élégant parfait pour les posts ambiance.
        
        Args:
            img: Image source
            intensity: Intensité du voile (0.0 à 1.0), 0.35 par défaut
        """
        # Convertir en RGBA si nécessaire
        img_rgba = img.convert("RGBA")
        
        # Créer une couche blanche semi-transparente
        light_layer = Image.new("RGBA", img.size, (255, 255, 255, int(255 * intensity)))
        
        # Fusionner avec l'image
        result = Image.alpha_composite(img_rgba, light_layer)
        
        return result

    def resize_and_crop_to_fit(self, img: Image.Image) -> Image.Image:
        """
        Redimensionne et recadre l'image pour correspondre aux dimensions Instagram.
        Utilise un crop centré.
        """
        target_ratio = self.width / self.height
        img_ratio = img.width / img.height
        
        if img_ratio > target_ratio:
            # Image plus large que la cible, crop sur les côtés
            new_width = int(img.height * target_ratio)
            left = (img.width - new_width) // 2
            img = img.crop((left, 0, left + new_width, img.height))
        else:
            # Image plus haute que la cible, crop en haut/bas
            new_height = int(img.width / target_ratio)
            top = (img.height - new_height) // 2
            img = img.crop((0, top, img.width, top + new_height))
        
        # Redimensionner à la taille finale
        return img.resize((self.width, self.height), Image.Resampling.LANCZOS)

    def add_logo_overlay(
        self, img: Image.Image, logo_color: str = "black"
    ) -> Image.Image:
        """
        Ajoute le logo au centre de l'image.
        
        Args:
            img: Image de fond
            logo_color: "black" ou "white"
        """
        # Charger le logo
        logo_filename = f"logo_{logo_color}.png"
        logo_path = LOGO_DIR / logo_filename
        
        if not logo_path.exists():
            print(f"Warning: Logo not found at {logo_path}")
            return img
        
        logo = Image.open(logo_path).convert("RGBA")
        
        # Redimensionner le logo
        logo = logo.resize(
            (self.logo_size, self.logo_size), 
            Image.Resampling.LANCZOS
        )
        
        # Position centrée
        logo_x = (self.width - self.logo_size) // 2
        logo_y = (self.height - self.logo_size) // 2
        
        # Convertir en RGBA si nécessaire
        if img.mode != "RGBA":
            img = img.convert("RGBA")
        
        # Coller le logo
        img.paste(logo, (logo_x, logo_y), logo)
        
        return img

    def generate(self, content: dict) -> Image.Image:
        """
        Génère l'image pour un post de type "Photo".
        
        Args:
            content: Dictionnaire avec les clés:
                - image_url: URL de l'image (AI générée ou autre)
                - image_path: Chemin local vers une image
                - unsplash_photo_id: ID d'une photo Unsplash
                - overlay_logo: bool, ajouter le logo au centre (défaut: True)
                - apply_filter: bool, appliquer le filtre chaud (défaut: True pour AI, False pour Unsplash)
                - light_overlay: bool, appliquer le voile clair (défaut: False)
                - light_overlay_intensity: float, intensité du voile (défaut: 0.35)
                - logo_color: "black" ou "white" (défaut: "black")
        """
        # Charger l'image source
        image_url = content.get("image_url")
        image_path = content.get("image_path")
        unsplash_photo_id = content.get("unsplash_photo_id")
        
        # Si on a un ID Unsplash, récupérer l'URL
        if unsplash_photo_id and not image_url:
            try:
                from services.unsplash_service import UnsplashService, check_unsplash_availability
                if check_unsplash_availability()["ready"]:
                    service = UnsplashService()
                    # Déclencher le download (requis par Unsplash) et récupérer l'URL
                    image_url = service.trigger_download(unsplash_photo_id)
            except Exception as e:
                print(f"Warning: Could not fetch Unsplash photo: {e}")
        
        if image_url:
            img = self.load_image_from_url(image_url)
        elif image_path:
            img = self.load_image_from_path(Path(image_path))
        else:
            # Créer une image placeholder grise
            print("Warning: No image source provided, using placeholder")
            img = Image.new("RGB", (self.width, self.height), (200, 200, 200))
        
        # Redimensionner et recadrer
        img = self.resize_and_crop_to_fit(img)
        
        # Appliquer le voile clair si demandé (pour les posts ambiance Unsplash)
        if content.get("light_overlay", False):
            intensity = content.get("light_overlay_intensity", 0.35)
            img = self.apply_light_overlay(img, intensity=intensity)
        # Sinon, appliquer le filtre chaud si demandé (pour les photos AI)
        elif content.get("apply_filter", True):
            img = self.apply_warm_filter(img, intensity=0.12)
        
        # Ajouter le logo si demandé
        if content.get("overlay_logo", True):
            logo_color = content.get("logo_color", "black")
            img = self.add_logo_overlay(img, logo_color)
        
        # Ajouter la tagline en bas (en REGULAR)
        img = img.convert("RGBA")
        draw = ImageDraw.Draw(img)
        font_tagline = self.load_font("LibreBaskerville-Regular.ttf", FONT_SIZES["phrase"]["tagline"])
        self.add_tagline(draw, font_tagline, self.tagline_color, y_offset=250)
        
        return img.convert("RGB")

    def generate_with_placeholder(self, content: dict) -> Image.Image:
        """
        Génère une image placeholder quand l'API Replicate n'est pas disponible.
        Utile pour les tests et previews.
        """
        # Créer un fond avec un dégradé gris
        img = self.create_gradient(
            self.width, self.height,
            "#8B8B8B", "#5A5A5A",
            direction="vertical"
        )
        
        draw = ImageDraw.Draw(img)
        
        # Ajouter un texte indicatif
        font = self.load_font("PlayfairDisplay-Regular.ttf", 32)
        text = "Photo AI - Preview"
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        x = (self.width - text_width) // 2
        draw.text((x, 100), text, font=font, fill=(255, 255, 255))
        
        # Afficher le prompt AI
        ai_prompt = content.get("ai_prompt", "No prompt provided")
        prompt_font = self.load_font("PlayfairDisplay-Italic.ttf", 24)
        lines = self.wrap_text(ai_prompt, prompt_font, self.width - 100, draw)
        
        y = 160
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=prompt_font)
            text_width = bbox[2] - bbox[0]
            x = (self.width - text_width) // 2
            draw.text((x, y), line, font=prompt_font, fill=(220, 220, 220))
            y += 35
        
        # Ajouter le logo
        if content.get("overlay_logo", True):
            logo_color = content.get("logo_color", "black")
            img = self.add_logo_overlay(img.convert("RGBA"), logo_color)
        
        # Ajouter la tagline en bas (en italique)
        img = img.convert("RGBA")
        draw = ImageDraw.Draw(img)
        font_tagline = self.load_font("LibreBaskerville-Italic.ttf", FONT_SIZES["phrase"]["tagline"])
        self.add_tagline(draw, font_tagline, self.tagline_color, y_offset=100)
        
        return img.convert("RGB")


# Test rapide
if __name__ == "__main__":
    generator = PhotoGenerator()
    
    test_content = {
        "ai_prompt": "Friends meeting at a Parisian cafe terrace, warm afternoon light",
        "overlay_logo": True,
        "apply_filter": True,
    }
    
    # Test avec placeholder
    image = generator.generate_with_placeholder(test_content)
    output_path = generator.save(image, "test_photo_placeholder.png")
    print(f"Placeholder image saved to: {output_path}")
