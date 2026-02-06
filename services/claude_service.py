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
- Vérifier l'exactitude des faits (ex: prix du pass Navigo ~86€/mois, pas 5€)
"""

# Guide de style détaillé pour la génération de phrases
PHRASE_STYLE_GUIDE = """
GUIDE DE STYLE POUR LES PHRASES:

=== STRUCTURES GAGNANTES (à privilégier) ===
1. PUNCHLINE IRONIQUE : Une observation mordante qui retourne la situation.
   Ex: "Dire 'C'est plus simple chez moi', c'est juste déclarer officiellement la guerre à ceux qui n'habitent pas la même ligne."

2. TRADUCTION / REFORMULATION ABSURDE : Décoder le langage parisien.
   Ex: "Traduction de 'Je suis dans le métro' : Je suis sur le quai, il y a un colis suspect et je serai là dans 40 minutes."
   Ex: "'Je suis dans le métro' = Je viens de fermer ma porte d'entrée."

3. DÉTOURNEMENT RHÉTORIQUE : Prendre un concept noble et l'appliquer au quotidien transport.
   Ex: "Parce que l'amitié, c'est aussi diviser le temps de trajet par deux."
   Ex: "Le Middle : Parce que personne n'est le centre du monde, mais tout le monde peut être au centre du rendez-vous."

4. STATISTIQUE INVENTÉE / HYPERBOLE : Chiffres absurdes mais relatables.
   Ex: "Statistiquement, 80 % des 'j'arrive' sont envoyés depuis une salle de bain."
   Ex: "Le record du monde de vitesse : penser qu'on peut se doucher, se sécher et traverser Paris en 300 secondes."

5. OBSERVATION DU QUOTIDIEN avec chute : Décrire une situation que tout le monde connaît, puis twist final.
   Ex: "L'ami qui propose 'un bar sympa' juste en bas de chez lui pour la 4ème fois consécutive."
   Ex: "'J'habite à 15 minutes' mais oublie de préciser que c'est 15 minutes + 2 correspondances + une marche de 10 minutes."

=== CE QU'IL FAUT ABSOLUMENT ÉVITER ===
1. NARRATION PLATE DE TEMPS/STATIONS : "Ton pote fait X min depuis Station A, toi Y min depuis Station B" → trop robotique, pas d'humour
2. CHIFFRES BRUTS SANS PUNCHLINE : "1h30 de trajet pour rester 2h" → ennuyeux sans twist
3. FRAMING NÉGATIF DE LE MIDDLE : Ne JAMAIS présenter Le Middle comme une source de galère partagée. Le Middle est une SOLUTION, une récompense.
   MAUVAIS: "tout le monde galère autant"
   BON: "on partage l'effort (et la pinte)"
4. FAITS INCORRECTS : Vérifier les prix (Navigo ~86€/mois), les réalités du réseau
5. RÉFÉRENCES TROP SPÉCIFIQUES sans humour : "depuis République jusqu'à Opéra" → pas drôle en soi
6. PHRASES TROP DESCRIPTIVES : Préférer les phrases qui font RESSENTIR plutôt que celles qui DÉCRIVENT

=== REGISTRE DE LANGUE ===
- Parler AVEC le public, pas AU public
- Tutoiement naturel, comme entre potes
- Ironie et second degré constants
- Formulations qui donnent envie de taguer un ami
- Le lecteur doit se dire "C'est EXACTEMENT ça" ou rire en reconnaissant la situation
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
        Privilégie les posts bien notés (rating 3), puis 2, et exclut les rating 1.
        
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
        
        # Séparer par rating : exclure les posts notés 1 (mauvais)
        rated_3 = [p for p in posts if p.get("rating") == 3]
        rated_2 = [p for p in posts if p.get("rating") == 2]
        unrated = [p for p in posts if p.get("rating") is None]
        # rating == 1 : exclus des exemples
        
        # Construire la liste de candidats en priorisant les meilleurs
        candidates = []
        
        # D'abord les phrases notées 3
        if rated_3:
            random.shuffle(rated_3)
            candidates.extend(rated_3)
        
        # Puis les phrases notées 2
        if rated_2:
            random.shuffle(rated_2)
            candidates.extend(rated_2)
        
        # Puis les phrases non notées (anciennes, probablement OK)
        if unrated:
            random.shuffle(unrated)
            candidates.extend(unrated)
        
        return candidates[:count]

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

    def _load_bad_examples(self, post_type: str, count: int = 3) -> list[dict]:
        """
        Charge des paires BAD->GOOD depuis les posts corrigés (original_text + text actuel).
        Sélectionne des posts qui ont un original_text et un original_rating de 1 (les pires).
        
        Args:
            post_type: Type de post ('phrase' ou 'chiffre')
            count: Nombre de paires à charger
            
        Returns:
            Liste de posts ayant un original_text (paire bad->good)
        """
        content_path = Path(__file__).parent.parent / "data" / "content.json"
        
        if not content_path.exists():
            return []
        
        with open(content_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Chercher les posts corrigés (ceux qui ont un original_text)
        corrected = [
            p for p in data.get("posts", [])
            if p.get("type") == post_type and p.get("original_text")
        ]
        
        # Prioriser les pires originaux (rating 1)
        worst_first = sorted(corrected, key=lambda p: p.get("original_rating", 2))
        
        if len(worst_first) > count:
            # Prendre les count pires, avec un peu d'aléatoire parmi les ex-aequo
            rating_1 = [p for p in worst_first if p.get("original_rating") == 1]
            rating_2 = [p for p in worst_first if p.get("original_rating") == 2]
            random.shuffle(rating_1)
            random.shuffle(rating_2)
            pool = rating_1 + rating_2
            return pool[:count]
        
        return worst_first[:count]

    def _format_bad_examples(self, bad_examples: list[dict]) -> str:
        """Formate les paires BAD->GOOD pour le prompt."""
        if not bad_examples:
            return ""
        
        formatted = []
        for ex in bad_examples:
            bad_text = ex.get("original_text", "")
            good_text = ex.get("content", {}).get("text", "")
            formatted.append(f"MAUVAIS: \"{bad_text}\"\nCORRIGÉ: \"{good_text}\"")
        
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
        bad_examples = self._load_bad_examples("phrase", count=3)
        bad_examples_text = self._format_bad_examples(bad_examples)
        
        category_guidance = ""
        if category == "mois1_injustices":
            category_guidance = """Catégorie: INJUSTICES DU QUOTIDIEN
- Observation ironique d'une situation injuste dans les transports parisiens
- Utilise le détournement rhétorique, la question rhétorique, ou la reformulation sarcastique
- Le lecteur doit ressentir l'injustice ET en rire
- Structures efficaces: "Dire X, c'est en fait Y", "'Citation' : La phrase préférée de celui qui...", "Drôle de conception de X quand..."
- Exemples de ton: "Dire 'C'est plus simple chez moi', c'est juste déclarer officiellement la guerre à ceux qui n'habitent pas la même ligne."
"""
        elif category == "mois2_mythes":
            category_guidance = """Catégorie: MYTHES ET LÉGENDES URBAINES
- Décoder les mensonges classiques et comportements typiques des parisiens dans les transports
- Utilise la "Traduction de...", la reformulation absurde, les statistiques inventées hilarantes
- Structures efficaces: "Traduction de 'X' : Y", "'X' = Y (la vraie version)", "Le record du monde de..."
- Exemples de ton: "Traduction de 'Je suis dans le métro' : Je suis sur le quai, il y a un colis suspect et je serai là dans 40 minutes."
- Prendre en compte les vrais problèmes récurrents (colis suspects, retards, pannes) pour ancrer dans la réalité
"""
        elif category == "mois3_redemption":
            category_guidance = """Catégorie: RÉDEMPTION (Le Middle comme solution)
- Le Middle est présenté comme une SOLUTION POSITIVE, une récompense, jamais comme une galère partagée
- L'effort est partagé équitablement ET mène à un moment agréable (la pinte, la soirée, retrouver ses amis)
- INTERDIT: framing négatif ("tout le monde galère autant"), Le Middle ne doit JAMAIS être associé à la douleur
- Structures efficaces: "Le Middle : Parce que...", "Pour une fois, c'est toi qui...", "La fin de X. Le début de Y."
- Exemples de ton: "Le Middle : La fin du favoritisme géographique. Ici, on partage l'effort (et la pinte)."
"""
        
        prompt = f"""Génère UNE SEULE nouvelle phrase pour la série "La Galère" de Le Middle.

{PHRASE_STYLE_GUIDE}

FORMAT ATTENDU:
- Une phrase PUNCHLINE de 1-2 lignes, 3 max si nécessaire
- Ironique, mordante, ou qui retourne une situation absurde
- Le lecteur doit immédiatement se reconnaître ET sourire/rire
- Privilégier les reformulations, traductions, détournements plutôt que les descriptions plates
- JAMAIS de narration robotique type "X fait Y min, toi Z min"

{category_guidance}

EXEMPLES À NE PAS REPRODUIRE (et leur version corrigée):
{bad_examples_text if bad_examples_text else "Pas de mauvais exemples disponibles."}

EXEMPLES DE PHRASES BIEN NOTÉES (à utiliser comme inspiration stylistique, NE PAS COPIER):
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
