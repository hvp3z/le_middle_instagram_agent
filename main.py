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


if __name__ == "__main__":
    cli()
