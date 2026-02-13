"""
CLI principal pour le pipeline Instagram Le Middle.

Commandes:
    python main.py generate --status draft     # Générer toutes les images en attente
    python main.py generate --id chiffre_001   # Générer un post spécifique
    python main.py preview --id phrase_001     # Aperçu d'un post
    python main.py publish --id chiffre_001    # Publier un post
    python main.py list                        # Lister tous les posts
    python main.py status                      # Vérifier la configuration
"""
import json
import random
import sys
from pathlib import Path
from typing import Optional

import click

# Ajouter le répertoire courant au path
sys.path.insert(0, str(Path(__file__).parent))

from config.settings import DATA_DIR, GENERATED_DIR
from generators import ChiffreGenerator, PhraseGenerator, PhotoGenerator
from services.instagram_service import InstagramService, check_instagram_availability
from services.replicate_service import ReplicateService, check_replicate_availability
from services.unsplash_service import UnsplashService, check_unsplash_availability


def load_content() -> dict:
    """Charge le fichier content.json."""
    content_path = DATA_DIR / "content.json"
    if not content_path.exists():
        click.echo(f"Erreur: {content_path} n'existe pas.", err=True)
        sys.exit(1)
    
    with open(content_path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_content(data: dict) -> None:
    """Sauvegarde le fichier content.json."""
    content_path = DATA_DIR / "content.json"
    with open(content_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def get_post_by_id(post_id: str) -> Optional[dict]:
    """Récupère un post par son ID."""
    data = load_content()
    for post in data.get("posts", []):
        if post.get("id") == post_id:
            return post
    return None


def get_generator(post_type: str):
    """Retourne le générateur approprié selon le type de post."""
    generators = {
        "chiffre": ChiffreGenerator,
        "phrase": PhraseGenerator,
        "photo": PhotoGenerator,
    }
    
    generator_class = generators.get(post_type)
    if generator_class:
        return generator_class()
    return None


def format_caption(post: dict) -> str:
    """Formate la caption Instagram à partir des données du post."""
    caption_data = post.get("caption", {})
    
    parts = []
    
    # Texte principal
    main_text = caption_data.get("main", "")
    if main_text:
        parts.append(main_text)
    
    # CTA (call-to-action)
    cta = caption_data.get("cta")
    if cta:
        parts.append(cta)
    
    # Hashtags
    hashtags = caption_data.get("hashtags", [])
    if hashtags:
        parts.append("")  # Ligne vide
        parts.append(" ".join([f"#{tag}" for tag in hashtags]))
    
    return "\n".join(parts)


@click.group()
def cli():
    """Pipeline Instagram Le Middle - Génération et publication automatisée."""
    pass


@cli.command()
@click.option("--id", "post_id", help="ID du post à générer")
@click.option("--status", help="Générer tous les posts avec ce statut (draft, ready)")
@click.option("--type", "post_type", help="Filtrer par type (chiffre, phrase, photo)")
@click.option("--dry-run", is_flag=True, help="Afficher sans générer")
def generate(post_id: Optional[str], status: Optional[str], post_type: Optional[str], dry_run: bool):
    """Génère les images pour les posts."""
    data = load_content()
    posts_to_generate = []
    
    if post_id:
        # Générer un seul post
        post = get_post_by_id(post_id)
        if not post:
            click.echo(f"Post non trouvé: {post_id}", err=True)
            return
        posts_to_generate.append(post)
    else:
        # Filtrer les posts
        for post in data.get("posts", []):
            if status and post.get("status") != status:
                continue
            if post_type and post.get("type") != post_type:
                continue
            posts_to_generate.append(post)
    
    if not posts_to_generate:
        click.echo("Aucun post à générer.")
        return
    
    click.echo(f"Posts à générer: {len(posts_to_generate)}")
    
    if dry_run:
        for post in posts_to_generate:
            click.echo(f"  - {post['id']} ({post['type']})")
        return
    
    # Générer les images
    GENERATED_DIR.mkdir(exist_ok=True)
    
    for post in posts_to_generate:
        click.echo(f"\nGénération de {post['id']}...")
        
        generator = get_generator(post["type"])
        if not generator:
            click.echo(f"  Type non supporté: {post['type']}", err=True)
            continue
        
        try:
            content = post.get("content", {})
            
            # Pour les photos, utiliser le placeholder si pas d'URL
            if post["type"] == "photo" and not content.get("image_url"):
                image = generator.generate_with_placeholder(content)
            else:
                image = generator.generate(content)
            
            filename = f"{post['id']}.png"
            output_path = generator.save(image, filename)
            
            click.echo(f"  Sauvegardé: {output_path}")
            
            # Mettre à jour le statut
            post["status"] = "ready"
            post["generated_image"] = str(output_path)
            
        except Exception as e:
            click.echo(f"  Erreur: {e}", err=True)
    
    # Sauvegarder les changements
    save_content(data)
    click.echo("\nGénération terminée!")


@cli.command()
@click.option("--id", "post_id", required=True, help="ID du post à prévisualiser")
def preview(post_id: str):
    """Affiche un aperçu d'un post."""
    post = get_post_by_id(post_id)
    if not post:
        click.echo(f"Post non trouvé: {post_id}", err=True)
        return
    
    click.echo(f"\n=== Aperçu: {post_id} ===")
    click.echo(f"Type: {post.get('type')}")
    click.echo(f"Status: {post.get('status')}")
    click.echo(f"Date prévue: {post.get('scheduled_date')}")
    
    click.echo(f"\nContenu:")
    content = post.get("content", {})
    for key, value in content.items():
        click.echo(f"  {key}: {value}")
    
    click.echo(f"\nCaption Instagram:")
    click.echo("-" * 40)
    click.echo(format_caption(post))
    click.echo("-" * 40)
    
    # Vérifier si l'image existe
    generated_path = post.get("generated_image")
    if generated_path and Path(generated_path).exists():
        click.echo(f"\nImage générée: {generated_path}")
        
        if click.confirm("Ouvrir l'image?"):
            generator = get_generator(post["type"])
            if generator:
                from PIL import Image
                img = Image.open(generated_path)
                img.show()
    else:
        click.echo("\nImage non générée. Utilisez 'generate --id' d'abord.")


@cli.command()
@click.option("--id", "post_id", required=True, help="ID du post à publier")
@click.option("--force", is_flag=True, help="Publier même si déjà publié")
def publish(post_id: str, force: bool):
    """Publie un post sur Instagram."""
    # Vérifier la configuration
    ig_status = check_instagram_availability()
    if not ig_status["ready"]:
        click.echo("Instagram non configuré. Voir docs/INSTAGRAM_SETUP.md", err=True)
        return
    
    post = get_post_by_id(post_id)
    if not post:
        click.echo(f"Post non trouvé: {post_id}", err=True)
        return
    
    if post.get("status") == "published" and not force:
        click.echo(f"Post déjà publié. Utilisez --force pour republier.", err=True)
        return
    
    # Vérifier que l'image existe
    generated_path = post.get("generated_image")
    if not generated_path or not Path(generated_path).exists():
        click.echo("Image non générée. Utilisez 'generate --id' d'abord.", err=True)
        return
    
    # Formater la caption
    caption = format_caption(post)
    
    click.echo(f"\nPublication de {post_id}...")
    click.echo(f"Image: {generated_path}")
    click.echo(f"\nCaption:\n{caption[:200]}...")
    
    if not click.confirm("\nPublier maintenant?"):
        click.echo("Publication annulée.")
        return
    
    try:
        service = InstagramService()
        result = service.publish_image(Path(generated_path), caption)
        
        if result["status"] == "published":
            click.echo(f"\nPublié avec succès! Media ID: {result['media_id']}")
            
            # Mettre à jour le statut
            data = load_content()
            for p in data["posts"]:
                if p["id"] == post_id:
                    p["status"] = "published"
                    p["instagram_media_id"] = result["media_id"]
                    break
            save_content(data)
        else:
            click.echo(f"\nÉchec de publication: {result['status']}", err=True)
            
    except Exception as e:
        click.echo(f"\nErreur: {e}", err=True)


@cli.command("list")
@click.option("--status", help="Filtrer par statut")
@click.option("--type", "post_type", help="Filtrer par type")
def list_posts(status: Optional[str], post_type: Optional[str]):
    """Liste tous les posts."""
    data = load_content()
    posts = data.get("posts", [])
    
    if status:
        posts = [p for p in posts if p.get("status") == status]
    if post_type:
        posts = [p for p in posts if p.get("type") == post_type]
    
    if not posts:
        click.echo("Aucun post trouvé.")
        return
    
    click.echo(f"\n{'ID':<20} {'Type':<10} {'Status':<12} {'Date':<12}")
    click.echo("-" * 60)
    
    for post in posts:
        click.echo(
            f"{post['id']:<20} {post['type']:<10} {post['status']:<12} "
            f"{post.get('scheduled_date', 'N/A'):<12}"
        )
    
    click.echo(f"\nTotal: {len(posts)} posts")


@cli.command()
def status():
    """Vérifie la configuration du système."""
    click.echo("\n=== Configuration Le Middle Instagram ===\n")
    
    # Vérifier Instagram
    ig_status = check_instagram_availability()
    click.echo("Instagram API:")
    click.echo(f"  - Credentials: {'OK' if ig_status['instagram_configured'] else 'MANQUANT'}")
    click.echo(f"  - Cloudinary: {'OK' if ig_status['cloudinary_configured'] else 'MANQUANT'}")
    
    # Vérifier Replicate
    rep_status = check_replicate_availability()
    click.echo("\nReplicate (photos AI):")
    click.echo(f"  - Package: {'OK' if rep_status['package_installed'] else 'MANQUANT'}")
    click.echo(f"  - API Token: {'OK' if rep_status['api_token_configured'] else 'MANQUANT'}")
    
    # Vérifier Unsplash
    unsplash_status = check_unsplash_availability()
    click.echo("\nUnsplash (photos libres de droit):")
    click.echo(f"  - API Key: {'OK' if unsplash_status['api_key_configured'] else 'MANQUANT'}")
    
    # Vérifier les assets
    from config.settings import FONTS_DIR, LOGO_DIR
    
    click.echo("\nAssets:")
    fonts_ok = (FONTS_DIR / "PlayfairDisplay-Bold.ttf").exists()
    click.echo(f"  - Fonts: {'OK' if fonts_ok else 'MANQUANT'}")
    
    logo_ok = (LOGO_DIR / "logo_black.png").exists()
    click.echo(f"  - Logos: {'OK' if logo_ok else 'MANQUANT'}")
    
    # Compter les posts
    data = load_content()
    posts = data.get("posts", [])
    
    click.echo("\nContenu:")
    click.echo(f"  - Total posts: {len(posts)}")
    
    status_counts = {}
    for post in posts:
        s = post.get("status", "unknown")
        status_counts[s] = status_counts.get(s, 0) + 1
    
    for s, count in status_counts.items():
        click.echo(f"  - {s}: {count}")
    
    click.echo("\n" + "=" * 40)
    
    if ig_status["ready"]:
        click.echo("Prêt pour la publication!")
    else:
        click.echo("Configuration incomplète. Voir docs/INSTAGRAM_SETUP.md")


@cli.command()
@click.option("--id", "post_id", required=True, help="ID du post")
@click.option("--style", default="cafe_terrace", help="Style de photo (cafe_terrace, wine_bar, bistro)")
def generate_ai_photo(post_id: str, style: str):
    """Génère une photo AI pour un post de type 'photo'."""
    rep_status = check_replicate_availability()
    if not rep_status["ready"]:
        click.echo("Replicate non configuré. Ajoutez REPLICATE_API_TOKEN à .env", err=True)
        return
    
    post = get_post_by_id(post_id)
    if not post:
        click.echo(f"Post non trouvé: {post_id}", err=True)
        return
    
    if post.get("type") != "photo":
        click.echo(f"Ce n'est pas un post de type 'photo'", err=True)
        return
    
    prompt = post.get("content", {}).get("ai_prompt", "")
    if not prompt:
        click.echo("Pas de prompt AI défini pour ce post", err=True)
        return
    
    click.echo(f"\nGénération AI pour {post_id}...")
    click.echo(f"Prompt: {prompt}")
    click.echo(f"Style: {style}")
    
    try:
        service = ReplicateService()
        image_url = service.generate_image(prompt, style=style)
        
        click.echo(f"\nImage générée: {image_url}")
        
        # Mettre à jour le post avec l'URL
        data = load_content()
        for p in data["posts"]:
            if p["id"] == post_id:
                p["content"]["image_url"] = image_url
                break
        save_content(data)
        
        click.echo("URL sauvegardée dans content.json")
        click.echo("Utilisez 'generate --id' pour créer l'image finale avec le logo.")
        
    except Exception as e:
        click.echo(f"\nErreur: {e}", err=True)


@cli.command()
@click.option("--id", "post_id", help="ID du post à lier à la photo")
@click.option("--query", default="cafe_terrace", help="Recherche ou preset (cafe_terrace, wine_bar, friends_drinking, rooftop_bar, brunch, aperitif)")
@click.option("--count", default=5, help="Nombre de résultats à afficher")
def fetch_unsplash(post_id: Optional[str], query: str, count: int):
    """Recherche et sélectionne une photo Unsplash pour un post ambiance."""
    unsplash_status = check_unsplash_availability()
    if not unsplash_status["ready"]:
        click.echo("Unsplash non configuré. Ajoutez UNSPLASH_ACCESS_KEY à .env", err=True)
        return
    
    click.echo(f"\nRecherche Unsplash: '{query}'...")
    
    try:
        service = UnsplashService()
        results = service.search_photos(query, orientation="portrait", per_page=count)
        
        if not results:
            click.echo("Aucun résultat trouvé.", err=True)
            return
        
        click.echo(f"\n{len(results)} photos trouvées:\n")
        click.echo("-" * 60)
        
        for i, photo in enumerate(results, 1):
            desc = photo['description'][:50] + "..." if photo['description'] and len(photo['description']) > 50 else (photo['description'] or "Sans description")
            click.echo(f"{i}. {desc}")
            click.echo(f"   ID: {photo['id']}")
            click.echo(f"   Preview: {photo['urls']['small']}")
            click.echo(f"   Par: {photo['user']['name']} (@{photo['user']['username']})")
            click.echo("")
        
        click.echo("-" * 60)
        click.echo("\nOuvre les URLs de preview dans ton navigateur pour voir les images.")
        click.echo("IMPORTANT: Vérifie qu'il n'y a pas de marque/trademark visible!")
        
        if post_id:
            # Vérifier que le post existe
            post = get_post_by_id(post_id)
            if not post:
                click.echo(f"\nPost non trouvé: {post_id}", err=True)
                return
            
            if post.get("type") != "photo":
                click.echo(f"\nCe n'est pas un post de type 'photo'", err=True)
                return
            
            # Demander quelle photo choisir
            choice = click.prompt(
                "\nNuméro de la photo à utiliser (ou 'q' pour quitter)",
                type=str,
                default="q"
            )
            
            if choice.lower() == 'q':
                click.echo("Annulé.")
                return
            
            try:
                idx = int(choice) - 1
                if idx < 0 or idx >= len(results):
                    click.echo("Numéro invalide.", err=True)
                    return
                
                selected_photo = results[idx]
                photo_id = selected_photo['id']
                
                # Mettre à jour le post
                data = load_content()
                for p in data["posts"]:
                    if p["id"] == post_id:
                        p["content"]["unsplash_photo_id"] = photo_id
                        p["content"]["unsplash_user"] = f"{selected_photo['user']['name']} (@{selected_photo['user']['username']})"
                        p["content"]["light_overlay"] = True
                        p["content"]["light_overlay_intensity"] = 0.35
                        p["content"]["apply_filter"] = False
                        # Ne pas définir trademark_verified, l'utilisateur doit le faire manuellement
                        break
                save_content(data)
                
                click.echo(f"\nPhoto sélectionnée: {photo_id}")
                click.echo(f"Crédit: {selected_photo['user']['name']}")
                click.echo("\nMis à jour dans content.json avec light_overlay activé.")
                click.echo("\nProchaines étapes:")
                click.echo(f"  1. Vérifie l'image pour les trademarks")
                click.echo(f"  2. Dans content.json, ajoute: \"trademark_verified\": true")
                click.echo(f"  3. Génère l'image finale: python main.py generate --id {post_id}")
                
            except ValueError:
                click.echo("Entrée invalide.", err=True)
                return
        else:
            click.echo("\nPour lier une photo à un post, utilisez:")
            click.echo(f"  python main.py fetch-unsplash --id <post_id> --query \"{query}\"")
        
    except Exception as e:
        click.echo(f"\nErreur: {e}", err=True)


@cli.command()
@click.option("--query", default="cafe_terrace", help="Recherche ou preset")
def unsplash_random(query: str):
    """Récupère une photo aléatoire depuis Unsplash (pour inspiration)."""
    unsplash_status = check_unsplash_availability()
    if not unsplash_status["ready"]:
        click.echo("Unsplash non configuré. Ajoutez UNSPLASH_ACCESS_KEY à .env", err=True)
        return
    
    click.echo(f"\nRecherche aléatoire: '{query}'...")
    
    try:
        service = UnsplashService()
        photo = service.get_random_photo(query, orientation="portrait")
        
        if not photo:
            click.echo("Aucun résultat trouvé.", err=True)
            return
        
        desc = photo['description'] or "Sans description"
        click.echo(f"\nPhoto trouvée:")
        click.echo(f"  Description: {desc}")
        click.echo(f"  ID: {photo['id']}")
        click.echo(f"  Preview: {photo['urls']['regular']}")
        click.echo(f"  Par: {photo['user']['name']} (@{photo['user']['username']})")
        
    except Exception as e:
        click.echo(f"\nErreur: {e}", err=True)


@cli.command()
@click.option("--id", "post_id", required=True, help="ID du post photo")
def auto_photo(post_id: str):
    """Génère automatiquement une photo ambiance (recherche aléatoire + génération)."""
    # Vérifier Unsplash
    unsplash_status = check_unsplash_availability()
    if not unsplash_status["ready"]:
        click.echo("Unsplash non configuré. Ajoutez UNSPLASH_ACCESS_KEY à .env", err=True)
        return
    
    # Vérifier que le post existe et est de type photo
    data = load_content()
    post = None
    post_index = None
    for i, p in enumerate(data.get("posts", [])):
        if p.get("id") == post_id:
            post = p
            post_index = i
            break
    
    if not post:
        click.echo(f"Post non trouvé: {post_id}", err=True)
        return
    
    if post.get("type") != "photo":
        click.echo(f"Ce n'est pas un post de type 'photo' (type actuel: {post.get('type')})", err=True)
        return
    
    try:
        service = UnsplashService()
        
        # Pour les posts ambiance, utiliser uniquement les presets urbains
        ambiance_only = post.get("category") == "ambiance"
        preset_key, preset_query = service.get_random_preset(ambiance_only=ambiance_only)
        click.echo(f"\nPreset aléatoire: {preset_key}" + (" (urbain)" if ambiance_only else ""))
        click.echo(f"Recherche: '{preset_query}'")
        
        # Récupérer une photo aléatoire
        photo = service.get_random_photo(preset_key, orientation="portrait")
        
        if not photo:
            click.echo("Aucune photo trouvée. Réessayez.", err=True)
            return
        
        photo_id = photo['id']
        user_name = photo['user']['name']
        user_username = photo['user']['username']
        desc = photo['description'] or "Sans description"
        
        click.echo(f"\nPhoto trouvée: {photo_id}")
        click.echo(f"  Description: {desc[:60]}..." if len(desc) > 60 else f"  Description: {desc}")
        click.echo(f"  Par: {user_name} (@{user_username})")
        click.echo(f"  Preview: {photo['urls']['small']}")
        
        # Mettre à jour content.json avec les infos de la photo
        post["content"]["unsplash_photo_id"] = photo_id
        post["content"]["unsplash_user"] = f"{user_name} (@{user_username})"
        post["content"]["unsplash_query_used"] = preset_key
        post["content"]["light_overlay"] = True
        post["content"]["light_overlay_intensity"] = 0.35
        post["content"]["apply_filter"] = False
        post["content"]["overlay_logo"] = True
        post["content"]["logo_color"] = "black"
        
        # Sauvegarder les changements
        data["posts"][post_index] = post
        save_content(data)
        click.echo("\nContent.json mis à jour.")
        
        # Générer l'image finale
        click.echo("\nGénération de l'image finale...")
        
        generator = PhotoGenerator()
        GENERATED_DIR.mkdir(exist_ok=True)
        
        image = generator.generate(post["content"])
        filename = f"{post_id}.png"
        output_path = generator.save(image, filename)
        
        # Mettre à jour le statut du post
        data = load_content()
        for p in data["posts"]:
            if p["id"] == post_id:
                p["status"] = "ready"
                p["generated_image"] = str(output_path)
                break
        save_content(data)
        
        click.echo(f"\nSauvegardé: {output_path}")
        click.echo(f"Crédit photo: {user_name} (@{user_username}) via Unsplash")
        click.echo("\nTerminé! L'image est prête.")
        
    except Exception as e:
        click.echo(f"\nErreur: {e}", err=True)


# Types de posts (ordre utilisé pour affichage des stats)
PUBLISH_ORDER = ["phrase", "chiffre", "photo"]


@cli.command("grid-preview")
@click.option("--rows", default=4, help="Nombre de lignes à afficher")
def grid_preview(rows: int):
    """Affiche un aperçu de la grille Instagram (colonnes de 3)."""
    
    data = load_content()
    posts = data.get("posts", [])
    
    # Séparer les posts publiés et à publier
    posted = [p for p in posts if p.get("status") == "posted"]
    ready = [p for p in posts if p.get("status") == "ready"]
    draft = [p for p in posts if p.get("status") == "draft"]
    
    # Trier les posts publiés par publish_order
    posted.sort(key=lambda x: x.get("publish_order", 0), reverse=True)
    
    click.echo("\n" + "=" * 60)
    click.echo("           GRILLE INSTAGRAM - LE MIDDLE")
    click.echo("=" * 60)
    
    posted_count = len(posted)
    
    click.echo(f"\nMode: aléatoire")
    click.echo(f"Total publiés: {posted_count}")
    
    # Afficher la file d'attente (ordre aléatoire simulé)
    click.echo("\n--- File d'attente (ordre aléatoire simulé) ---")
    click.echo(f"{'Col 1':<20} {'Col 2':<20} {'Col 3':<20}")
    click.echo("-" * 60)
    
    # Mélanger les posts ready et prendre les N premiers
    queue = list(ready)
    random.shuffle(queue)
    queue = queue[: rows * 3]
    # Compléter avec des placeholders si nécessaire
    while len(queue) < rows * 3:
        queue.append({"id": "[MANQUANT]", "status": "missing", "type": "?"})
    
    # Afficher en lignes de 3
    for row in range(rows):
        col1 = queue[row * 3] if row * 3 < len(queue) else None
        col2 = queue[row * 3 + 1] if row * 3 + 1 < len(queue) else None
        col3 = queue[row * 3 + 2] if row * 3 + 2 < len(queue) else None
        
        def format_cell(post):
            if not post:
                return " " * 18
            post_id = post["id"][:14]
            status = post.get("status", "?")
            type_map = {"phrase": "P", "chiffre": "C", "photo": "Ph"}
            type_indicator = type_map.get(post.get("type", "?"), "?")
            if status == "ready":
                return f"[{type_indicator}] {post_id}"
            else:
                return f"[!] {post_id}"
        
        click.echo(f"{format_cell(col1):<20} {format_cell(col2):<20} {format_cell(col3):<20}")
    
    click.echo("-" * 60)
    click.echo("Légende: [P]=Phrase, [C]=Chiffre, [Ph]=Photo, [!]=Manquant")
    
    # Stats
    click.echo(f"\n--- Statistiques ---")
    click.echo(f"Posts 'ready':  {len(ready)} (P:{len([p for p in ready if p['type']=='phrase'])}, "
               f"C:{len([p for p in ready if p['type']=='chiffre'])}, "
               f"Ph:{len([p for p in ready if p['type']=='photo'])})")
    click.echo(f"Posts 'draft':  {len(draft)}")
    click.echo(f"Posts 'posted': {len(posted)}")
    
    # Alertes
    if len(ready) < 6:
        click.echo(f"\n[!] ALERTE: Moins de 6 posts prets! Generez du contenu.")
    
    # Vérifier l'équilibre des types
    for type_name in PUBLISH_ORDER:
        type_ready = len([p for p in ready if p.get("type") == type_name])
        if type_ready < 2:
            click.echo(f"[!] ALERTE: Seulement {type_ready} post(s) '{type_name}' ready!")


if __name__ == "__main__":
    cli()
