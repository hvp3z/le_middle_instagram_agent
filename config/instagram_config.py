"""
Configuration Instagram Graph API et Cloudinary
"""
import os
from dotenv import load_dotenv

load_dotenv()

# Instagram Graph API
INSTAGRAM_BUSINESS_ACCOUNT_ID = os.getenv("INSTAGRAM_BUSINESS_ACCOUNT_ID", "")
FACEBOOK_PAGE_ACCESS_TOKEN = os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN", "")

# Cloudinary (pour héberger les images avant publication Instagram)
CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME", "")
CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY", "")
CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET", "")

# Replicate (pour génération AI de photos)
REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN", "")

# Unsplash (pour photos libres de droit)
UNSPLASH_ACCESS_KEY = os.getenv("UNSPLASH_ACCESS_KEY", "")

# Instagram API URLs
INSTAGRAM_API_BASE = "https://graph.facebook.com/v18.0"


def get_instagram_media_url() -> str:
    """Retourne l'URL pour créer un media container."""
    return f"{INSTAGRAM_API_BASE}/{INSTAGRAM_BUSINESS_ACCOUNT_ID}/media"


def get_instagram_publish_url() -> str:
    """Retourne l'URL pour publier un media."""
    return f"{INSTAGRAM_API_BASE}/{INSTAGRAM_BUSINESS_ACCOUNT_ID}/media_publish"


def validate_config() -> dict[str, bool]:
    """Vérifie que toutes les configurations sont présentes."""
    return {
        "instagram": bool(INSTAGRAM_BUSINESS_ACCOUNT_ID and FACEBOOK_PAGE_ACCESS_TOKEN),
        "cloudinary": bool(CLOUDINARY_CLOUD_NAME and CLOUDINARY_API_KEY and CLOUDINARY_API_SECRET),
        "replicate": bool(REPLICATE_API_TOKEN),
        "unsplash": bool(UNSPLASH_ACCESS_KEY),
    }
