"""
Service pour publier des images sur Instagram via l'API Graph
"""
import os
import time
from pathlib import Path
from typing import Optional
import requests
import cloudinary
import cloudinary.uploader

from config.instagram_config import (
    INSTAGRAM_BUSINESS_ACCOUNT_ID,
    FACEBOOK_PAGE_ACCESS_TOKEN,
    CLOUDINARY_CLOUD_NAME,
    CLOUDINARY_API_KEY,
    CLOUDINARY_API_SECRET,
    INSTAGRAM_API_BASE,
    get_instagram_media_url,
    get_instagram_publish_url,
    validate_config,
)


class InstagramService:
    """Service pour publier sur Instagram via l'API Graph."""

    def __init__(self):
        """Initialise le service Instagram."""
        self.account_id = INSTAGRAM_BUSINESS_ACCOUNT_ID
        self.access_token = FACEBOOK_PAGE_ACCESS_TOKEN
        
        # Configurer Cloudinary si disponible
        self._setup_cloudinary()

    def _setup_cloudinary(self) -> None:
        """Configure Cloudinary pour l'hébergement d'images."""
        if all([CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET]):
            cloudinary.config(
                cloud_name=CLOUDINARY_CLOUD_NAME,
                api_key=CLOUDINARY_API_KEY,
                api_secret=CLOUDINARY_API_SECRET,
                secure=True
            )
            self.cloudinary_configured = True
        else:
            self.cloudinary_configured = False

    def check_configuration(self) -> dict:
        """Vérifie la configuration du service."""
        config_status = validate_config()
        return {
            "instagram_api": config_status["instagram"],
            "cloudinary": config_status["cloudinary"],
            "ready": config_status["instagram"] and config_status["cloudinary"],
        }

    def upload_to_cloudinary(self, image_path: Path, public_id: Optional[str] = None) -> str:
        """
        Upload une image sur Cloudinary.
        
        Args:
            image_path: Chemin vers l'image locale
            public_id: ID public optionnel pour l'image
            
        Returns:
            URL publique de l'image
        """
        if not self.cloudinary_configured:
            raise ValueError("Cloudinary n'est pas configuré. Ajoutez les credentials dans .env")
        
        upload_options = {
            "folder": "lemiddle-instagram",
            "resource_type": "image",
        }
        
        if public_id:
            upload_options["public_id"] = public_id
        
        result = cloudinary.uploader.upload(str(image_path), **upload_options)
        return result["secure_url"]

    def get_account_info(self) -> dict:
        """Récupère les informations du compte Instagram."""
        url = f"{INSTAGRAM_API_BASE}/{self.account_id}"
        params = {
            "fields": "username,name,profile_picture_url,followers_count,media_count",
            "access_token": self.access_token,
        }
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()

    def create_media_container(
        self,
        image_url: str,
        caption: str,
    ) -> str:
        """
        Crée un container média (étape 1 de la publication).
        
        Args:
            image_url: URL publique de l'image
            caption: Légende du post
            
        Returns:
            ID du container créé
        """
        url = get_instagram_media_url()
        
        payload = {
            "image_url": image_url,
            "caption": caption,
            "access_token": self.access_token,
        }
        
        # #region agent log
        import json as _json
        _log_path = r"c:\Users\matdi\Documents\myApps\Automatisations\LeMiddleInstagram\.cursor\debug.log"
        with open(_log_path, "a", encoding="utf-8") as _f: _f.write(_json.dumps({"hypothesisId": "A,B,E", "location": "instagram_service.py:create_media_container:entry", "message": "API call params", "data": {"url": url, "image_url": image_url, "caption_length": len(caption), "caption_preview": caption[:100], "has_special_chars": any(ord(c) > 127 for c in caption), "token_prefix": self.access_token[:20] + "..." if self.access_token else "EMPTY", "account_id": self.account_id}, "timestamp": __import__("time").time()}, ensure_ascii=False) + "\n")
        # #endregion
        
        response = requests.post(url, data=payload)
        
        # #region agent log
        with open(_log_path, "a", encoding="utf-8") as _f: _f.write(_json.dumps({"hypothesisId": "A,B,C,D,E", "location": "instagram_service.py:create_media_container:response", "message": "API response", "data": {"status_code": response.status_code, "response_text": response.text[:500] if response.text else "EMPTY", "response_headers": dict(response.headers)}, "timestamp": __import__("time").time()}, ensure_ascii=False) + "\n")
        # #endregion
        
        if not response.ok:
            _err_msg = response.reason
            try:
                _err_body = response.json()
                if isinstance(_err_body.get("error"), dict):
                    _api_msg = _err_body["error"].get("message", "")
                    _code = _err_body["error"].get("code")
                    if _api_msg:
                        _err_msg = _api_msg
                    if _code == 190:
                        _err_msg = f"Token Instagram/Facebook expiré ou invalide. {_err_msg} Mettez à jour FACEBOOK_PAGE_ACCESS_TOKEN dans .env (Meta Developer Console)."
            except Exception:
                pass
            raise requests.HTTPError(_err_msg, response=response)
        
        result = response.json()
        return result["id"]

    def check_container_status(self, container_id: str) -> dict:
        """
        Vérifie le statut d'un container média.
        
        Args:
            container_id: ID du container
            
        Returns:
            Dictionnaire avec le statut
        """
        url = f"{INSTAGRAM_API_BASE}/{container_id}"
        params = {
            "fields": "status_code,status",
            "access_token": self.access_token,
        }
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()

    def publish_media(self, container_id: str) -> str:
        """
        Publie le média (étape 2 de la publication).
        
        Args:
            container_id: ID du container à publier
            
        Returns:
            ID du média publié
        """
        url = get_instagram_publish_url()
        
        payload = {
            "creation_id": container_id,
            "access_token": self.access_token,
        }
        
        response = requests.post(url, data=payload)
        response.raise_for_status()
        
        result = response.json()
        return result["id"]

    def wait_for_container_ready(
        self,
        container_id: str,
        max_wait: int = 60,
        check_interval: int = 5,
    ) -> bool:
        """
        Attend que le container soit prêt pour publication.
        
        Args:
            container_id: ID du container
            max_wait: Temps max d'attente en secondes
            check_interval: Intervalle entre les vérifications
            
        Returns:
            True si prêt, False sinon
        """
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            status = self.check_container_status(container_id)
            status_code = status.get("status_code")
            
            if status_code == "FINISHED":
                return True
            elif status_code == "ERROR":
                raise Exception(f"Erreur lors du traitement: {status.get('status')}")
            
            print(f"Container status: {status_code}, waiting...")
            time.sleep(check_interval)
        
        return False

    def publish_image(
        self,
        image_path: Path,
        caption: str,
        wait_for_ready: bool = True,
    ) -> dict:
        """
        Publie une image sur Instagram (workflow complet).
        
        Args:
            image_path: Chemin vers l'image locale
            caption: Légende du post (avec hashtags)
            wait_for_ready: Attendre que le container soit prêt
            
        Returns:
            Dictionnaire avec les IDs et statuts
        """
        result = {
            "image_url": None,
            "container_id": None,
            "media_id": None,
            "status": "pending",
        }
        
        # Étape 1: Upload sur Cloudinary
        print("Uploading image to Cloudinary...")
        image_url = self.upload_to_cloudinary(image_path)
        result["image_url"] = image_url
        print(f"Image uploaded: {image_url}")
        
        # #region agent log
        import json as _json
        _log_path = r"c:\Users\matdi\Documents\myApps\Automatisations\LeMiddleInstagram\.cursor\debug.log"
        try:
            _head_resp = requests.head(image_url, timeout=10)
            with open(_log_path, "a", encoding="utf-8") as _f: _f.write(_json.dumps({"hypothesisId": "C,D", "location": "instagram_service.py:publish_image:image_check", "message": "Image URL accessibility check", "data": {"image_url": image_url, "head_status": _head_resp.status_code, "content_type": _head_resp.headers.get("Content-Type", "UNKNOWN"), "content_length": _head_resp.headers.get("Content-Length", "UNKNOWN")}, "timestamp": __import__("time").time()}, ensure_ascii=False) + "\n")
        except Exception as _e:
            with open(_log_path, "a", encoding="utf-8") as _f: _f.write(_json.dumps({"hypothesisId": "C,D", "location": "instagram_service.py:publish_image:image_check", "message": "Image URL check FAILED", "data": {"image_url": image_url, "error": str(_e)}, "timestamp": __import__("time").time()}, ensure_ascii=False) + "\n")
        # #endregion
        
        # Étape 2: Créer le container média
        print("Creating media container...")
        container_id = self.create_media_container(image_url, caption)
        result["container_id"] = container_id
        print(f"Container created: {container_id}")
        
        # Étape 3: Attendre que le container soit prêt
        if wait_for_ready:
            print("Waiting for container to be ready...")
            is_ready = self.wait_for_container_ready(container_id)
            if not is_ready:
                result["status"] = "timeout"
                return result
        
        # Étape 4: Publier
        print("Publishing media...")
        media_id = self.publish_media(container_id)
        result["media_id"] = media_id
        result["status"] = "published"
        print(f"Media published! ID: {media_id}")
        
        return result

    def format_caption(
        self,
        main_text: str,
        hashtags: list[str],
        cta: Optional[str] = None,
    ) -> str:
        """
        Formate une caption Instagram.
        
        Args:
            main_text: Texte principal
            hashtags: Liste de hashtags (sans #)
            cta: Call-to-action optionnel
        """
        parts = [main_text]
        
        if cta:
            parts.append(cta)
        
        # Ajouter une ligne vide avant les hashtags
        parts.append("")
        
        # Formater les hashtags
        formatted_hashtags = " ".join([f"#{tag}" for tag in hashtags])
        parts.append(formatted_hashtags)
        
        return "\n".join(parts)


def check_instagram_availability() -> dict:
    """Vérifie si le service Instagram est disponible et configuré."""
    config = validate_config()
    return {
        "instagram_configured": config["instagram"],
        "cloudinary_configured": config["cloudinary"],
        "ready": config["instagram"] and config["cloudinary"],
    }


# Test rapide
if __name__ == "__main__":
    status = check_instagram_availability()
    print(f"Instagram service status: {status}")
    
    if status["ready"]:
        service = InstagramService()
        try:
            info = service.get_account_info()
            print(f"Connected as: {info.get('username', 'Unknown')}")
        except Exception as e:
            print(f"Error: {e}")
    else:
        print("\nTo configure Instagram:")
        print("1. Follow the guide in docs/INSTAGRAM_SETUP.md")
        print("2. Add credentials to .env file")
