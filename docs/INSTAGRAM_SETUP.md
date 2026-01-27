# Configuration Instagram Graph API

Ce guide explique comment configurer l'API Instagram Graph pour publier automatiquement des posts.

## Prérequis

1. Un compte Instagram **Business** ou **Creator**
2. Une **Page Facebook** connectée au compte Instagram
3. Un compte **Facebook Developer**

## Étapes de configuration

### 1. Convertir en compte Instagram Business

1. Aller dans les paramètres Instagram
2. Compte > Passer à un compte professionnel
3. Choisir "Business" ou "Créateur"
4. Connecter à une Page Facebook (créer une si nécessaire)

### 2. Créer une App Facebook Developer

1. Aller sur [developers.facebook.com](https://developers.facebook.com/)
2. Créer un compte développeur si nécessaire
3. "Mes Apps" > "Créer une app"
4. Choisir "Business" comme type d'app
5. Nommer l'app (ex: "Le Middle Instagram Automation")

### 3. Configurer les permissions

Dans votre app Facebook:

1. Ajouter le produit "Instagram Graph API"
2. Dans "Paramètres" > "Autorisations et fonctionnalités", activer:
   - `instagram_basic`
   - `instagram_content_publish`
   - `pages_show_list`
   - `pages_read_engagement`

### 4. Obtenir l'Access Token

#### Option A: Token de test (développement)

1. Aller dans "Outils" > "Explorateur de l'API Graph"
2. Sélectionner votre app
3. Générer un token avec les permissions:
   - `instagram_basic`
   - `instagram_content_publish`
   - `pages_show_list`
4. Ce token expire après ~1h

#### Option B: Token longue durée (production)

1. Obtenir un token courte durée via l'explorateur
2. Échanger contre un token longue durée:

```bash
curl -X GET "https://graph.facebook.com/v18.0/oauth/access_token?grant_type=fb_exchange_token&client_id={APP_ID}&client_secret={APP_SECRET}&fb_exchange_token={SHORT_LIVED_TOKEN}"
```

3. Obtenir le token de page (qui n'expire jamais):

```bash
curl -X GET "https://graph.facebook.com/v18.0/me/accounts?access_token={LONG_LIVED_TOKEN}"
```

### 5. Obtenir l'Instagram Business Account ID

```bash
curl -X GET "https://graph.facebook.com/v18.0/{PAGE_ID}?fields=instagram_business_account&access_token={PAGE_ACCESS_TOKEN}"
```

### 6. Configurer le fichier .env

```env
INSTAGRAM_BUSINESS_ACCOUNT_ID=17841400000000000
FACEBOOK_PAGE_ACCESS_TOKEN=EAAG...très-long-token...
```

## Test de la configuration

```python
from services.instagram_service import InstagramService

service = InstagramService()

# Vérifier la connexion
info = service.get_account_info()
print(f"Connecté en tant que: {info['username']}")
```

## Limites de l'API

- **25 publications par jour** par compte
- Les images doivent être hébergées sur une URL publique (utiliser Cloudinary)
- Format supporté: JPEG, PNG
- Taille max: 8MB
- Ratio d'aspect: entre 4:5 et 1.91:1

## Cloudinary (hébergement d'images)

Pour publier sur Instagram, les images doivent être accessibles via URL publique.

1. Créer un compte sur [cloudinary.com](https://cloudinary.com/)
2. Récupérer les credentials dans le Dashboard
3. Ajouter au `.env`:

```env
CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=your_api_key
CLOUDINARY_API_SECRET=your_api_secret
```

## Dépannage

### "Invalid OAuth access token"
- Le token a expiré, régénérez-le

### "The user has not authorized application"
- Vérifiez les permissions de l'app

### "(#100) param image_url must be a valid URL"
- L'image n'est pas accessible publiquement
- Utilisez Cloudinary ou un autre CDN

### "(#36003) Cannot create post"
- Vérifiez que le compte est bien Business/Creator
- Vérifiez que la Page Facebook est bien connectée
