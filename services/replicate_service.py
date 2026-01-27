"""
Service pour générer des images avec l'API Replicate (Flux.1 / SDXL)
"""
import os
import time
from typing import Optional
from config.instagram_config import REPLICATE_API_TOKEN

# Vérifier si replicate est installé
try:
    import replicate
    REPLICATE_AVAILABLE = True
except ImportError:
    REPLICATE_AVAILABLE = False


class ReplicateService:
    """Service pour générer des images via Replicate API."""
    
    # Modèles disponibles
    MODELS = {
        "flux_schnell": "black-forest-labs/flux-schnell",  # Rapide, bonne qualité
        "flux_dev": "black-forest-labs/flux-dev",  # Plus lent, meilleure qualité
        "sdxl": "stability-ai/sdxl:39ed52f2a78e934b3ba6e2a89f5b1c712de7dfea535525255b1aa35c5565e08b",
    }
    
    # Prompts de style pour Le Middle
    STYLE_PROMPTS = {
        "cafe_terrace": "Parisian cafe terrace, warm afternoon golden hour light, candid moment, film photography aesthetic, shallow depth of field, vintage color grading, 35mm film grain",
        "wine_bar": "Cozy Parisian wine bar interior, soft ambient lighting, intimate atmosphere, editorial style photography, warm tones",
        "bistro": "Classic French bistro scene, romantic evening lighting, authentic Parisian vibe, documentary photography style",
    }

    def __init__(self, model: str = "flux_schnell"):
        """
        Initialise le service Replicate.
        
        Args:
            model: Nom du modèle à utiliser (flux_schnell, flux_dev, sdxl)
        """
        if not REPLICATE_AVAILABLE:
            raise ImportError("Le package 'replicate' n'est pas installé. Exécutez: pip install replicate")
        
        if not REPLICATE_API_TOKEN:
            raise ValueError("REPLICATE_API_TOKEN non configuré. Ajoutez-le dans le fichier .env")
        
        os.environ["REPLICATE_API_TOKEN"] = REPLICATE_API_TOKEN
        self.model_name = self.MODELS.get(model, self.MODELS["flux_schnell"])
        self.client = replicate

    def enhance_prompt(self, base_prompt: str, style: Optional[str] = None) -> str:
        """
        Améliore le prompt avec des détails de style.
        
        Args:
            base_prompt: Prompt de base décrivant la scène
            style: Style prédéfini à ajouter (cafe_terrace, wine_bar, bistro)
        """
        enhanced = base_prompt
        
        if style and style in self.STYLE_PROMPTS:
            enhanced = f"{base_prompt}, {self.STYLE_PROMPTS[style]}"
        else:
            # Ajouter des détails par défaut pour le style Le Middle
            enhanced = f"{base_prompt}, warm natural lighting, candid authentic moment, film photography style, editorial quality, 35mm aesthetic"
        
        # Ajouter des négatifs implicites via le prompt positif
        enhanced += ", high quality, professional photography, well-lit"
        
        return enhanced

    def generate_image(
        self,
        prompt: str,
        style: Optional[str] = None,
        width: int = 1080,
        height: int = 1350,
        num_inference_steps: int = 4,  # Pour Flux Schnell
    ) -> str:
        """
        Génère une image avec Replicate.
        
        Args:
            prompt: Description de l'image à générer
            style: Style prédéfini optionnel
            width: Largeur de l'image
            height: Hauteur de l'image
            num_inference_steps: Nombre d'étapes d'inférence
            
        Returns:
            URL de l'image générée
        """
        enhanced_prompt = self.enhance_prompt(prompt, style)
        
        print(f"Generating image with prompt: {enhanced_prompt[:100]}...")
        
        # Paramètres selon le modèle
        if "flux" in self.model_name:
            input_params = {
                "prompt": enhanced_prompt,
                "go_fast": True,
                "megapixels": "1",
                "num_outputs": 1,
                "aspect_ratio": "4:5" if height > width else "1:1",
                "output_format": "png",
                "output_quality": 90,
                "num_inference_steps": num_inference_steps,
            }
        else:
            # SDXL
            input_params = {
                "prompt": enhanced_prompt,
                "width": width,
                "height": height,
                "num_outputs": 1,
                "scheduler": "K_EULER",
                "num_inference_steps": 30,
                "guidance_scale": 7.5,
                "negative_prompt": "blurry, low quality, distorted faces, bad anatomy, watermark, text",
            }
        
        # Appel à l'API
        output = self.client.run(self.model_name, input=input_params)
        
        # Le résultat est une liste d'URLs
        if isinstance(output, list) and len(output) > 0:
            image_url = str(output[0])
        else:
            image_url = str(output)
        
        print(f"Image generated: {image_url}")
        return image_url

    def generate_batch(
        self,
        prompts: list[str],
        style: Optional[str] = None,
        delay_between: float = 1.0,
    ) -> list[str]:
        """
        Génère plusieurs images en batch.
        
        Args:
            prompts: Liste de prompts
            style: Style à appliquer à toutes les images
            delay_between: Délai entre chaque génération (en secondes)
            
        Returns:
            Liste d'URLs des images générées
        """
        urls = []
        for i, prompt in enumerate(prompts):
            print(f"Generating image {i+1}/{len(prompts)}...")
            try:
                url = self.generate_image(prompt, style)
                urls.append(url)
            except Exception as e:
                print(f"Error generating image {i+1}: {e}")
                urls.append(None)
            
            if i < len(prompts) - 1:
                time.sleep(delay_between)
        
        return urls


def check_replicate_availability() -> dict:
    """Vérifie si le service Replicate est disponible et configuré."""
    return {
        "package_installed": REPLICATE_AVAILABLE,
        "api_token_configured": bool(REPLICATE_API_TOKEN),
        "ready": REPLICATE_AVAILABLE and bool(REPLICATE_API_TOKEN),
    }


# Test rapide
if __name__ == "__main__":
    status = check_replicate_availability()
    print(f"Replicate status: {status}")
    
    if status["ready"]:
        service = ReplicateService()
        
        test_prompt = "Two friends laughing at a Parisian cafe terrace"
        try:
            url = service.generate_image(test_prompt, style="cafe_terrace")
            print(f"Generated image URL: {url}")
        except Exception as e:
            print(f"Error: {e}")
    else:
        print("Replicate not configured. Add REPLICATE_API_TOKEN to .env file.")
