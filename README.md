# Le Middle - Instagram Content Pipeline

Pipeline d'automatisation pour générer et publier des posts Instagram pour [Le Middle](https://lemiddle.app).

## Installation

```bash
# Installer les dépendances
pip install -r requirements.txt
```

## Configuration

1. Copier le fichier d'exemple et le remplir avec vos credentials :

```bash
cp .env.example .env
```

2. Configurer les credentials (voir `docs/INSTAGRAM_SETUP.md` pour le guide complet) :

```env
# Instagram Graph API
INSTAGRAM_BUSINESS_ACCOUNT_ID=votre_id
FACEBOOK_PAGE_ACCESS_TOKEN=votre_token

# Cloudinary (hébergement images)
CLOUDINARY_CLOUD_NAME=votre_cloud
CLOUDINARY_API_KEY=votre_key
CLOUDINARY_API_SECRET=votre_secret

# Replicate (photos AI - optionnel)
REPLICATE_API_TOKEN=votre_token

# Unsplash (photos libres de droit - optionnel)
UNSPLASH_ACCESS_KEY=votre_clé
```

3. Remplacer les logos placeholder par les vrais logos Le Middle dans `assets/logo/`

## Utilisation

### Référence des commandes

| Commande | Description |
|----------|-------------|
| `python main.py status` | Vérifier la configuration |
| `python main.py list [--status] [--type]` | Lister les posts |
| `python main.py generate [--id] [--status] [--type]` | Générer les images |
| `python main.py preview --id <post_id>` | Aperçu d'un post |
| `python main.py publish --id <post_id>` | Publier sur Instagram |
| `python main.py generate-ai-photo --id <post_id> [--style]` | Générer une photo IA (Replicate) |
| `python main.py batch-ambiance --id <post_id> [--count] [--query]` | Générer plusieurs images ambiance et choisir |
| `python main.py auto-photo --id <post_id>` | Générer une image ambiance (une seule, aléatoire) |
| `python main.py fetch-unsplash [--id] [--query] [--count]` | Rechercher des photos Unsplash |
| `python main.py unsplash-random [--query]` | Photo Unsplash aléatoire (inspiration) |
| `python main.py grid-preview [--rows]` | Aperçu de la grille Instagram |

### Vérifier la configuration

```bash
python main.py status
```

### Lister les posts

```bash
python main.py list
python main.py list --status draft
python main.py list --type chiffre
```

### Générer les images

```bash
# Générer tous les posts en draft
python main.py generate --status draft

# Générer un post spécifique
python main.py generate --id chiffre_001

# Générer par type
python main.py generate --type phrase
```

### Prévisualiser un post

```bash
python main.py preview --id phrase_001
```

### Publier sur Instagram

```bash
python main.py publish --id chiffre_001
```

### Générer une photo AI (nécessite Replicate)

```bash
python main.py generate-ai-photo --id photo_001 --style cafe_terrace
```

### Photos ambiance (Unsplash)

```bash
# Générer plusieurs images et choisir la meilleure (recommandé)
python main.py batch-ambiance --id ambiance_004
python main.py batch-ambiance --id ambiance_004 --count 8 --query "cafe terrace paris"

# Générer une seule image ambiance (photo aléatoire)
python main.py auto-photo --id ambiance_004

# Rechercher des photos avec un preset
python main.py fetch-unsplash --query cafe_terrace

# Rechercher et lier à un post existant
python main.py fetch-unsplash --id ambiance_001 --query "friends drinking wine"

# Photo aléatoire pour inspiration
python main.py unsplash-random --query rooftop_bar
```

Presets disponibles: `cafe_terrace`, `wine_bar`, `friends_drinking`, `rooftop_bar`, `brunch`, `aperitif`

## Structure des Posts

Les posts sont définis dans `data/content.json`. Trois types sont supportés :

### Type "Chiffre"
Focus sur une donnée statistique avec un chiffre géant en dégradé.

```json
{
  "type": "chiffre",
  "content": {
    "context_text": "Texte au-dessus du chiffre",
    "number": "42",
    "unit_text": "minutes d'attente."
  }
}
```

### Type "Phrase"
Citation/phrase punchy sur fond dégradé avec carte blanche.

```json
{
  "type": "phrase",
  "content": {
    "text": "La phrase à afficher sur 4-5 lignes."
  }
}
```

### Type "Photo" (AI)
Photo générée par IA avec overlay du logo.

```json
{
  "type": "photo",
  "content": {
    "ai_prompt": "Description de la scène à générer",
    "overlay_logo": true
  }
}
```

### Type "Photo" (Unsplash - Ambiance)
Photo libre de droit depuis Unsplash avec overlay clair et logo centré.

```json
{
  "type": "photo",
  "content": {
    "unsplash_query": "friends cafe terrace paris",
    "unsplash_photo_id": "abc123",
    "light_overlay": true,
    "light_overlay_intensity": 0.35,
    "overlay_logo": true,
    "logo_color": "black",
    "trademark_verified": true
  }
}
```

## Architecture

```
le-middle-instagram/
├── config/               # Configuration (couleurs, API)
├── data/                 # Contenus (content.json)
├── assets/              
│   ├── fonts/           # Polices Playfair Display
│   └── logo/            # Logos PNG
├── generators/          # Générateurs d'images
│   ├── chiffre_generator.py
│   ├── phrase_generator.py
│   └── photo_generator.py
├── services/            # Services externes
│   ├── instagram_service.py
│   └── replicate_service.py
├── generated/           # Images générées
├── docs/                # Documentation
└── main.py              # CLI principal
```

## Workflow Recommandé

1. **Ajouter du contenu** dans `data/content.json`
2. **Générer les images** : `python main.py generate --status draft`
3. **Vérifier visuellement** les images dans `generated/`
4. **Prévisualiser** la caption : `python main.py preview --id xxx`
5. **Publier** : `python main.py publish --id xxx`

## Personnalisation

### Modifier les couleurs

Éditer `config/settings.py` :

```python
COLORS = {
    "cream_bg": "#FDF8F5",
    "coral_dark": "#E8725C",
    # ...
}
```

### Modifier les dimensions

```python
IMAGE_SIZE = (1080, 1350)  # Format 4:5
```

## Limites Instagram

- Maximum 25 publications par jour
- Images : JPEG ou PNG, max 8MB
- Ratio : entre 4:5 et 1.91:1
