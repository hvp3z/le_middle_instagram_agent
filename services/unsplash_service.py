"""
Service pour récupérer des images libres de droit depuis l'API Unsplash.
"""
import os
import random
from typing import Optional
import requests
from config.instagram_config import UNSPLASH_ACCESS_KEY

# URL de base de l'API Unsplash
UNSPLASH_API_BASE = "https://api.unsplash.com"


class UnsplashService:
    """Service pour rechercher et télécharger des images depuis Unsplash."""
    
    # Queries prédéfinies pour Le Middle (simples pour maximiser les résultats)
    PRESET_QUERIES = {
        # Terrasses et cafés
        "cafe_terrace": "cafe terrace people",
        "coffee_shop": "coffee shop friends",
        "bistro_paris": "bistro paris terrace",
        # Bars
        "wine_bar": "wine bar friends",
        "rooftop_bar": "rooftop bar",
        "bar_night": "bar people night",
        "happy_hour": "happy hour drinks friends",
        # Restaurants
        "restaurant_friends": "restaurant friends dinner",
        "outdoor_dining": "outdoor dining people",
        "brunch": "brunch friends",
        # Ambiance générale
        "friends_drinking": "friends drinks",
        "aperitif": "aperitif outdoor",
    }

    def __init__(self):
        """Initialise le service Unsplash."""
        if not UNSPLASH_ACCESS_KEY:
            raise ValueError(
                "UNSPLASH_ACCESS_KEY non configuré. Ajoutez-le dans le fichier .env"
            )
        
        self.headers = {
            "Authorization": f"Client-ID {UNSPLASH_ACCESS_KEY}",
            "Accept-Version": "v1",
        }

    def get_random_preset(self) -> tuple[str, str]:
        """
        Retourne un preset aléatoire (clé, query).
        
        Returns:
            Tuple (preset_key, search_query)
        """
        key = random.choice(list(self.PRESET_QUERIES.keys()))
        return key, self.PRESET_QUERIES[key]

    def search_photos(
        self,
        query: str,
        orientation: str = "portrait",
        per_page: int = 10,
        page: int = 1,
    ) -> list[dict]:
        """
        Recherche des photos sur Unsplash.
        
        Args:
            query: Termes de recherche ou clé de preset (cafe_terrace, wine_bar, etc.)
            orientation: "portrait", "landscape" ou "squarish"
            per_page: Nombre de résultats par page (max 30)
            page: Numéro de page
            
        Returns:
            Liste de dictionnaires avec les infos des photos
        """
        # Utiliser le preset si disponible
        search_query = self.PRESET_QUERIES.get(query, query)
        
        url = f"{UNSPLASH_API_BASE}/search/photos"
        params = {
            "query": search_query,
            "orientation": orientation,
            "per_page": min(per_page, 30),
            "page": page,
        }
        
        response = requests.get(url, headers=self.headers, params=params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        results = []
        
        for photo in data.get("results", []):
            results.append({
                "id": photo["id"],
                "description": photo.get("description") or photo.get("alt_description", ""),
                "urls": {
                    "thumb": photo["urls"]["thumb"],
                    "small": photo["urls"]["small"],
                    "regular": photo["urls"]["regular"],
                    "full": photo["urls"]["full"],
                    "raw": photo["urls"]["raw"],
                },
                "user": {
                    "name": photo["user"]["name"],
                    "username": photo["user"]["username"],
                    "link": photo["user"]["links"]["html"],
                },
                "download_location": photo["links"]["download_location"],
                "width": photo["width"],
                "height": photo["height"],
            })
        
        return results

    def get_random_photo(
        self,
        query: str,
        orientation: str = "portrait",
    ) -> Optional[dict]:
        """
        Récupère une photo aléatoire correspondant à la recherche.
        
        Args:
            query: Termes de recherche ou clé de preset
            orientation: "portrait", "landscape" ou "squarish"
            
        Returns:
            Dictionnaire avec les infos de la photo, ou None si aucun résultat
        """
        # Utiliser le preset si disponible
        search_query = self.PRESET_QUERIES.get(query, query)
        
        url = f"{UNSPLASH_API_BASE}/photos/random"
        params = {
            "query": search_query,
            "orientation": orientation,
        }
        
        response = requests.get(url, headers=self.headers, params=params, timeout=30)
        
        if response.status_code == 404:
            return None
            
        response.raise_for_status()
        photo = response.json()
        
        return {
            "id": photo["id"],
            "description": photo.get("description") or photo.get("alt_description", ""),
            "urls": {
                "thumb": photo["urls"]["thumb"],
                "small": photo["urls"]["small"],
                "regular": photo["urls"]["regular"],
                "full": photo["urls"]["full"],
                "raw": photo["urls"]["raw"],
            },
            "user": {
                "name": photo["user"]["name"],
                "username": photo["user"]["username"],
                "link": photo["user"]["links"]["html"],
            },
            "download_location": photo["links"]["download_location"],
            "width": photo["width"],
            "height": photo["height"],
        }

    def get_photo_by_id(self, photo_id: str) -> Optional[dict]:
        """
        Récupère les infos d'une photo par son ID.
        
        Args:
            photo_id: ID Unsplash de la photo
            
        Returns:
            Dictionnaire avec les infos de la photo
        """
        url = f"{UNSPLASH_API_BASE}/photos/{photo_id}"
        
        response = requests.get(url, headers=self.headers, timeout=30)
        
        if response.status_code == 404:
            return None
            
        response.raise_for_status()
        photo = response.json()
        
        return {
            "id": photo["id"],
            "description": photo.get("description") or photo.get("alt_description", ""),
            "urls": {
                "thumb": photo["urls"]["thumb"],
                "small": photo["urls"]["small"],
                "regular": photo["urls"]["regular"],
                "full": photo["urls"]["full"],
                "raw": photo["urls"]["raw"],
            },
            "user": {
                "name": photo["user"]["name"],
                "username": photo["user"]["username"],
                "link": photo["user"]["links"]["html"],
            },
            "download_location": photo["links"]["download_location"],
            "width": photo["width"],
            "height": photo["height"],
        }

    def trigger_download(self, photo_id: str) -> str:
        """
        Signale un téléchargement à Unsplash (requis par leurs guidelines).
        Retourne l'URL de téléchargement.
        
        Args:
            photo_id: ID de la photo
            
        Returns:
            URL de téléchargement
        """
        photo = self.get_photo_by_id(photo_id)
        if not photo:
            raise ValueError(f"Photo non trouvée: {photo_id}")
        
        # Déclencher le download tracking
        download_location = photo["download_location"]
        requests.get(download_location, headers=self.headers, timeout=30)
        
        # Retourner l'URL haute qualité
        return photo["urls"]["full"]

    def get_download_url(self, photo_id: str, quality: str = "regular") -> str:
        """
        Récupère l'URL de téléchargement d'une photo.
        
        Args:
            photo_id: ID de la photo
            quality: "thumb", "small", "regular", "full" ou "raw"
            
        Returns:
            URL de l'image
        """
        photo = self.get_photo_by_id(photo_id)
        if not photo:
            raise ValueError(f"Photo non trouvée: {photo_id}")
        
        return photo["urls"].get(quality, photo["urls"]["regular"])


def check_unsplash_availability() -> dict:
    """Vérifie si le service Unsplash est disponible et configuré."""
    return {
        "api_key_configured": bool(UNSPLASH_ACCESS_KEY),
        "ready": bool(UNSPLASH_ACCESS_KEY),
    }


# Test rapide
if __name__ == "__main__":
    status = check_unsplash_availability()
    print(f"Unsplash status: {status}")
    
    if status["ready"]:
        service = UnsplashService()
        
        print("\nRecherche 'cafe terrace'...")
        try:
            results = service.search_photos("cafe_terrace", per_page=3)
            for i, photo in enumerate(results, 1):
                print(f"\n{i}. {photo['description'][:50] if photo['description'] else 'No description'}...")
                print(f"   ID: {photo['id']}")
                print(f"   Preview: {photo['urls']['small']}")
                print(f"   By: {photo['user']['name']}")
        except Exception as e:
            print(f"Erreur: {e}")
    else:
        print("Unsplash non configuré. Ajoutez UNSPLASH_ACCESS_KEY au fichier .env")
