"""
Service pour générer du contenu textuel avec Claude 3.5 Sonnet (Anthropic).
Génère des phrases "La Galère" et des chiffres pour Le Middle.
"""
import os
import json
import random
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

# Importer anthropic seulement si disponible
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False


# Configuration
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
MODEL = "claude-sonnet-4-20250514"

# Prompt système pour la génération de contenu Le Middle
SYSTEM_PROMPT = """Tu es un créateur de contenu pour Le Middle, une application web parisienne qui aide les groupes d'amis (2 à 6 personnes) à trouver un lieu de rendez-vous équidistant en temps de trajet via les transports en commun.

IDENTITÉ:
- Nom: Le Middle
- Handle Instagram: @lemiddleapp
- Promesse: "Moins de temps de trajet, plus de temps ensemble." / "Coupez la poire en deux, pas l'amitié."

TON & STYLE:
- Moderne, urbain, légèrement sarcastique
- Humour de plainte typiquement parisien (on râle, mais avec élégance)
- Efficace et punchy
- Jamais méchant, toujours relatable
- On parle de LA galère des transports comme obstacle à la vie sociale

THÉMATIQUES CENTRALES:
- La ligne 13 bondée
- Les "J'arrive" mensongers
- Les trajets plus longs que le temps passé ensemble
- Les amis qui proposent toujours le bar en bas de chez eux
- Les correspondances interminables à Châtelet
- Le dernier métro qui force à partir tôt
- Les zones Navigo qui séparent les amis
- Les groupes WhatsApp qui n'arrivent jamais à décider du lieu

RÈGLES IMPORTANTES:
- Chaque texte doit être autonome et compréhensible sans contexte
- Éviter les références trop datées ou trop spécifiques
- Le contenu doit inciter au partage ("C'est trop nous !")
- Toujours garder une pointe d'humour, même dans la plainte
- Ne jamais mentionner de marques concurrentes
"""


class ClaudeService:
    """Service pour générer du contenu avec Claude 3.5 Sonnet."""

    def __init__(self):
        """Initialise le service Claude."""
        if not ANTHROPIC_AVAILABLE:
            raise ImportError("Le package 'anthropic' n'est pas installé. Exécutez: pip install anthropic")
        
        if not ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY n'est pas configuré dans .env")
        
        self.client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        self.model = MODEL

    def _load_examples(self, post_type: str, count: int = 5) -> list[dict]:
        """
        Charge des exemples de posts existants pour le few-shot learning.
        
        Args:
            post_type: Type de post ('phrase' ou 'chiffre')
            count: Nombre d'exemples à charger
            
        Returns:
            Liste d'exemples de posts
        """
        content_path = Path(__file__).parent.parent / "data" / "content.json"
        
        if not content_path.exists():
            return []
        
        with open(content_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        posts = [p for p in data.get("posts", []) if p.get("type") == post_type]
        
        # Sélectionner des exemples aléatoires
        if len(posts) > count:
            posts = random.sample(posts, count)
        
        return posts

    def _format_phrase_examples(self, examples: list[dict]) -> str:
        """Formate les exemples de phrases pour le prompt."""
        if not examples:
            return "Pas d'exemples disponibles."
        
        formatted = []
        for ex in examples:
            text = ex.get("content", {}).get("text", "")
            caption = ex.get("caption", {}).get("main", "")
            formatted.append(f"PHRASE: {text}\nCAPTION: {caption}")
        
        return "\n\n".join(formatted)

    def _format_chiffre_examples(self, examples: list[dict]) -> str:
        """Formate les exemples de chiffres pour le prompt."""
        if not examples:
            return "Pas d'exemples disponibles."
        
        formatted = []
        for ex in examples:
            content = ex.get("content", {})
            caption = ex.get("caption", {})
            formatted.append(
                f"CONTEXTE: {content.get('context_text', '')}\n"
                f"CHIFFRE: {content.get('number', '')}\n"
                f"UNITÉ: {content.get('unit_text', '')}\n"
                f"CAPTION: {caption.get('main', '')}"
            )
        
        return "\n\n".join(formatted)

    def generate_phrase(self, category: Optional[str] = None) -> dict:
        """
        Génère une nouvelle phrase "La Galère".
        
        Args:
            category: Catégorie optionnelle (mois1_injustices, mois2_mythes, mois3_redemption)
            
        Returns:
            Dictionnaire avec le contenu généré
        """
        examples = self._load_examples("phrase", count=5)
        examples_text = self._format_phrase_examples(examples)
        
        category_guidance = ""
        if category == "mois1_injustices":
            category_guidance = "Catégorie: Injustices du quotidien - Focus sur les situations injustes dans les transports parisiens."
        elif category == "mois2_mythes":
            category_guidance = "Catégorie: Mythes et légendes urbaines - Focus sur les mensonges classiques et comportements typiques."
        elif category == "mois3_redemption":
            category_guidance = "Catégorie: Rédemption - Focus sur les solutions et moments positifs grâce à Le Middle."
        
        prompt = f"""Génère UNE SEULE nouvelle phrase pour la série "La Galère" de Le Middle.

FORMAT ATTENDU:
- Une phrase punchy de 2-3 lignes maximum
- Sur les réalités des trajets parisiens
- Doit générer de l'identification ("C'est trop nous !")

{category_guidance}

EXEMPLES DE PHRASES EXISTANTES (à utiliser comme inspiration, NE PAS COPIER):
{examples_text}

Réponds UNIQUEMENT avec un JSON valide au format suivant (sans markdown, sans backticks):
{{
    "text": "La phrase générée ici",
    "caption": {{
        "main": "Le texte de caption Instagram (2-3 phrases max, peut inclure un emoji)",
        "hashtags": ["lemiddle", "hashtag2", "hashtag3", "hashtag4", "hashtag5"]
    }},
    "category": "mois1_injustices ou mois2_mythes ou mois3_redemption"
}}"""

        message = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        response_text = message.content[0].text.strip()
        
        # Parser le JSON
        try:
            result = json.loads(response_text)
        except json.JSONDecodeError:
            # Essayer d'extraire le JSON si entouré de texte
            import re
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if json_match:
                result = json.loads(json_match.group())
            else:
                raise ValueError(f"Impossible de parser la réponse JSON: {response_text}")
        
        # S'assurer que lemiddle est dans les hashtags
        if "lemiddle" not in result.get("caption", {}).get("hashtags", []):
            result["caption"]["hashtags"].insert(0, "lemiddle")
        
        return result

    def generate_chiffre(self, category: Optional[str] = None) -> dict:
        """
        Génère un nouveau chiffre avec contexte.
        
        Args:
            category: Catégorie optionnelle (temps_trajet, metro_rer, cout_eloignement, 
                     interactions_sociales, statistiques)
            
        Returns:
            Dictionnaire avec le contenu généré
        """
        examples = self._load_examples("chiffre", count=5)
        examples_text = self._format_chiffre_examples(examples)
        
        category_guidance = ""
        categories_possibles = ["temps_trajet", "metro_rer", "cout_eloignement", 
                               "interactions_sociales", "statistiques"]
        
        if category in categories_possibles:
            category_guidance = f"Catégorie imposée: {category}"
        else:
            category_guidance = f"Choisis une catégorie parmi: {', '.join(categories_possibles)}"
        
        prompt = f"""Génère UN SEUL nouveau chiffre pour la série "Le Chiffre" de Le Middle.

FORMAT ATTENDU:
- Un chiffre central (peut être 01, 02, ... 99, 100, etc.)
- Un texte de contexte en haut (la mise en situation)
- Un texte d'unité en bas (l'unité avec une pointe d'humour)
- Le chiffre peut être réel ou légèrement absurde

{category_guidance}

EXEMPLES DE CHIFFRES EXISTANTS (à utiliser comme inspiration, NE PAS COPIER):
{examples_text}

Réponds UNIQUEMENT avec un JSON valide au format suivant (sans markdown, sans backticks):
{{
    "content": {{
        "context_text": "Le texte de contexte en haut",
        "number": "42",
        "unit_text": "l'unité avec commentaire sarcastique"
    }},
    "caption": {{
        "main": "Le texte de caption Instagram (2-3 phrases, développe l'idée)",
        "hashtags": ["lemiddle", "hashtag2", "hashtag3", "hashtag4", "hashtag5"],
        "cta": "Un call-to-action (ex: Retrouvez-vous simplement. / On se capte au Middle.)"
    }},
    "category": "la_categorie_choisie"
}}"""

        message = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        response_text = message.content[0].text.strip()
        
        # Parser le JSON
        try:
            result = json.loads(response_text)
        except json.JSONDecodeError:
            # Essayer d'extraire le JSON si entouré de texte
            import re
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if json_match:
                result = json.loads(json_match.group())
            else:
                raise ValueError(f"Impossible de parser la réponse JSON: {response_text}")
        
        # S'assurer que lemiddle est dans les hashtags
        if "lemiddle" not in result.get("caption", {}).get("hashtags", []):
            result["caption"]["hashtags"].insert(0, "lemiddle")
        
        return result

    def generate_photo_caption(self, photo_context: Optional[str] = None) -> dict:
        """
        Génère une caption pour un post photo ambiance.
        
        Args:
            photo_context: Description optionnelle de la photo
            
        Returns:
            Dictionnaire avec la caption générée
        """
        context_text = photo_context or "Une photo montrant des amis qui passent un bon moment ensemble (terrasse, bar, café)."
        
        prompt = f"""Génère une caption Instagram pour un post photo "ambiance" de Le Middle.

CONTEXTE DE LA PHOTO:
{context_text}

L'objectif est de montrer la "récompense" - le moment passé ensemble après avoir trouvé le bon lieu de rendez-vous.

Réponds UNIQUEMENT avec un JSON valide au format suivant (sans markdown, sans backticks):
{{
    "caption": {{
        "main": "Le texte de caption (2-3 lignes, évoque le moment partagé, peut inclure un emoji)",
        "hashtags": ["lemiddle", "paris", "hashtag3", "hashtag4", "hashtag5"]
    }}
}}"""

        message = self.client.messages.create(
            model=self.model,
            max_tokens=512,
            system=SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        response_text = message.content[0].text.strip()
        
        # Parser le JSON
        try:
            result = json.loads(response_text)
        except json.JSONDecodeError:
            import re
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if json_match:
                result = json.loads(json_match.group())
            else:
                raise ValueError(f"Impossible de parser la réponse JSON: {response_text}")
        
        return result


def check_claude_availability() -> dict:
    """Vérifie si le service Claude est disponible et configuré."""
    return {
        "package_installed": ANTHROPIC_AVAILABLE,
        "api_key_configured": bool(ANTHROPIC_API_KEY),
        "ready": ANTHROPIC_AVAILABLE and bool(ANTHROPIC_API_KEY),
    }


# Test rapide
if __name__ == "__main__":
    status = check_claude_availability()
    print(f"Claude service status: {status}")
    
    if status["ready"]:
        service = ClaudeService()
        
        print("\n=== Test génération phrase ===")
        try:
            phrase = service.generate_phrase()
            print(json.dumps(phrase, indent=2, ensure_ascii=False))
        except Exception as e:
            print(f"Erreur: {e}")
        
        print("\n=== Test génération chiffre ===")
        try:
            chiffre = service.generate_chiffre()
            print(json.dumps(chiffre, indent=2, ensure_ascii=False))
        except Exception as e:
            print(f"Erreur: {e}")
    else:
        print("\nPour configurer Claude:")
        print("1. pip install anthropic")
        print("2. Ajouter ANTHROPIC_API_KEY dans .env")
