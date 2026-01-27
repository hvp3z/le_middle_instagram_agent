"""
Configuration des paramètres de design pour Le Middle Instagram
"""
from pathlib import Path

# Chemins
BASE_DIR = Path(__file__).parent.parent
ASSETS_DIR = BASE_DIR / "assets"
FONTS_DIR = ASSETS_DIR / "fonts"
LOGO_DIR = ASSETS_DIR / "logo"
DATA_DIR = BASE_DIR / "data"
GENERATED_DIR = BASE_DIR / "generated"

# Dimensions Instagram
IMAGE_SIZE = (1080, 1350)  # Format 4:5 recommandé
IMAGE_SIZE_SQUARE = (1080, 1080)  # Format carré alternatif

# Palette Le Middle
COLORS = {
    "cream_bg": "#FDF8F5",
    "coral_dark": "#E8725C",
    "coral_light": "#F4A98B",
    "peach": "#FCBF9A",
    "pink": "#F29B9B",
    "white": "#FFFFFF",
    "black": "#1A1A1A",
}

# Gradient pour les chiffres (du haut vers le bas)
CHIFFRE_GRADIENT = ["#E8725C", "#F4A98B"]

# Gradient pour le fond des phrases (du haut vers le bas)
PHRASE_BG_GRADIENT = ["#F4A98B", "#F29B9B"]

# Fonts - Satoshi (Sans-Serif) + Libre Baskerville (Serif)
FONTS = {
    # Satoshi - texte utilitaire/moderne
    "satoshi_regular": "Satoshi-Regular.otf",
    "satoshi_medium": "Satoshi-Medium.otf",
    "satoshi_bold": "Satoshi-Bold.otf",
    # Libre Baskerville - élégant/signature
    "baskerville_regular": "LibreBaskerville-Regular.ttf",
    "baskerville_bold": "LibreBaskerville-Bold.ttf",
    "baskerville_italic": "LibreBaskerville-Italic.ttf",
    # Legacy Playfair (kept for compatibility)
    "title": "PlayfairDisplay-Bold.ttf",
    "body": "PlayfairDisplay-Regular.ttf",
    "italic": "PlayfairDisplay-Italic.ttf",
}

# Tailles de police par type de post
FONT_SIZES = {
    "chiffre": {
        "number": 350,        # Libre Baskerville Bold - le grand chiffre
        "context": 38,        # Satoshi Regular - texte en haut
        "unit": 36,           # Satoshi Regular - "minutes d'attente"
        "tagline": 32,        # Libre Baskerville Italic - slogan
    },
    "phrase": {
        "header": 24,         # Satoshi Bold - "lemiddle.app"
        "text": 32,           # Satoshi Regular - texte dans le carré
        "tagline": 30,        # Libre Baskerville Italic - slogan
    },
}

# Tagline commune
TAGLINE = "Retrouvez-vous simplement."


def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """Convertit une couleur hexadécimale en tuple RGB."""
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))


def get_color_rgb(color_name: str) -> tuple[int, int, int]:
    """Récupère une couleur de la palette en RGB."""
    return hex_to_rgb(COLORS.get(color_name, COLORS["black"]))
