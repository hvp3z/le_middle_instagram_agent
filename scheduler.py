"""
Script d'orchestration pour l'automatisation Instagram Le Middle.

Commandes:
    python scheduler.py generate-content --count 6   # Générer un batch de contenu
    python scheduler.py publish-next                  # Publier le prochain post
    python scheduler.py grid-preview                  # Aperçu de la grille Instagram
    python scheduler.py queue-status                  # État de la file d'attente
"""
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import click

# Ajouter le répertoire courant au path
sys.path.insert(0, str(Path(__file__).parent))

from config.settings import DATA_DIR, GENERATED_DIR
from generators import ChiffreGenerator, PhraseGenerator, PhotoGenerator
from services.instagram_service import InstagramService, check_instagram_availability
from services.claude_service import ClaudeService, check_claude_availability
from services.unsplash_service import UnsplashService, check_unsplash_availability


# Ordre strict de publication : Phrase -> Chiffre -> Photo (cyclique)
PUBLISH_ORDER = ["phrase", "chiffre", "photo"]


def load_content() -> dict:
    """Charge le fichier content.json."""
    content_path = DATA_DIR / "content.json"
    if not content_path.exists():
        return {"posts": []}
    
    with open(content_path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_content(data: dict) -> None:
    """Sauvegarde le fichier content.json."""
    content_path = DATA_DIR / "content.json"
    with open(content_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def get_next_id(post_type: str, data: dict) -> str:
    """Génère le prochain ID pour un type de post."""
    prefix_map = {
        "phrase": "phrase_",
        "chiffre": "chiffre_",
        "photo": "ambiance_"
    }
    prefix = prefix_map.get(post_type, f"{post_type}_")
    
    existing_ids = [p["id"] for p in data.get("posts", []) if p["id"].startswith(prefix)]
    
    if not existing_ids:
        return f"{prefix}001"
    
    # Extraire les numéros et trouver le max
    numbers = []
    for id_ in existing_ids:
        try:
            num = int(id_.replace(prefix, ""))
            numbers.append(num)
        except ValueError:
            continue
    
    next_num = max(numbers) + 1 if numbers else 1
    return f"{prefix}{next_num:03d}"


def count_posts_by_status(status: str) -> int:
    """Compte le nombre de posts avec un statut donné."""
    data = load_content()
    return len([p for p in data.get("posts", []) if p.get("status") == status])


def get_posted_count() -> int:
    """Retourne le nombre total de posts publiés."""
    return count_posts_by_status("posted")


def get_next_post_type() -> str:
    """Détermine le type du prochain post à publier selon l'ordre strict."""
    posted_count = get_posted_count()
    return PUBLISH_ORDER[posted_count % 3]


def get_next_post_to_publish() -> Optional[dict]:
    """
    Récupère le prochain post à publier selon l'ordre strict.
    
    Returns:
        Le post à publier ou None si aucun n'est disponible
    """
    data = load_content()
    next_type = get_next_post_type()
    
    # Chercher le premier post "ready" du bon type
    for post in data.get("posts", []):
        if post.get("type") == next_type and post.get("status") == "ready":
            return post
    
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
    """Orchestration automatique Instagram Le Middle."""
    pass


@cli.command()
@click.option("--count", default=6, help="Nombre total de posts à générer (répartis entre les types)")
@click.option("--dry-run", is_flag=True, help="Afficher sans générer")
def generate_content(count: int, dry_run: bool):
    """Génère un batch de contenu (phrases, chiffres, photos)."""
    
    # Vérifier les services
    claude_status = check_claude_availability()
    unsplash_status = check_unsplash_availability()
    
    if not claude_status["ready"]:
        click.echo("Claude non configuré. Ajoutez ANTHROPIC_API_KEY à .env", err=True)
        click.echo("pip install anthropic", err=True)
        return
    
    if not unsplash_status["ready"]:
        click.echo("Warning: Unsplash non configuré. Les photos ne seront pas générées.", err=True)
    
    # Répartir le count entre les types (ratio 2:2:2 pour 6 posts)
    # Ou ajuster selon le count
    phrases_count = count // 3
    chiffres_count = count // 3
    photos_count = count - phrases_count - chiffres_count
    
    click.echo(f"\n=== Génération de contenu ===")
    click.echo(f"Phrases à générer: {phrases_count}")
    click.echo(f"Chiffres à générer: {chiffres_count}")
    click.echo(f"Photos à générer: {photos_count}")
    
    if dry_run:
        click.echo("\n[DRY RUN] Aucune génération effectuée.")
        return
    
    data = load_content()
    claude_service = ClaudeService()
    
    generated_posts = []
    
    # Générer les phrases
    click.echo(f"\n--- Génération de {phrases_count} phrases ---")
    for i in range(phrases_count):
        try:
            click.echo(f"  Génération phrase {i+1}/{phrases_count}...")
            result = claude_service.generate_phrase()
            
            post_id = get_next_id("phrase", data)
            new_post = {
                "id": post_id,
                "type": "phrase",
                "status": "draft",
                "category": result.get("category", "mois1_injustices"),
                "content": {
                    "text": result.get("text", "")
                },
                "caption": result.get("caption", {}),
                "created_at": datetime.utcnow().isoformat() + "Z"
            }
            
            data["posts"].append(new_post)
            generated_posts.append(new_post)
            click.echo(f"    Créé: {post_id}")
            
        except Exception as e:
            click.echo(f"    Erreur: {e}", err=True)
    
    # Générer les chiffres
    click.echo(f"\n--- Génération de {chiffres_count} chiffres ---")
    for i in range(chiffres_count):
        try:
            click.echo(f"  Génération chiffre {i+1}/{chiffres_count}...")
            result = claude_service.generate_chiffre()
            
            post_id = get_next_id("chiffre", data)
            new_post = {
                "id": post_id,
                "type": "chiffre",
                "status": "draft",
                "category": result.get("category", "statistiques"),
                "content": result.get("content", {}),
                "caption": result.get("caption", {}),
                "created_at": datetime.utcnow().isoformat() + "Z"
            }
            
            data["posts"].append(new_post)
            generated_posts.append(new_post)
            click.echo(f"    Créé: {post_id}")
            
        except Exception as e:
            click.echo(f"    Erreur: {e}", err=True)
    
    # Générer les photos
    if photos_count > 0 and unsplash_status["ready"]:
        click.echo(f"\n--- Génération de {photos_count} photos ---")
        unsplash_service = UnsplashService()
        photo_generator = PhotoGenerator()
        
        for i in range(photos_count):
            try:
                click.echo(f"  Génération photo {i+1}/{photos_count}...")
                
                # Obtenir un preset aléatoire
                preset_key, preset_query = unsplash_service.get_random_preset()
                photo = unsplash_service.get_random_photo(preset_key, orientation="portrait")
                
                if not photo:
                    click.echo(f"    Aucune photo trouvée pour '{preset_key}'", err=True)
                    continue
                
                # Générer la caption
                caption_result = claude_service.generate_photo_caption(
                    f"Photo de {preset_key}: {photo.get('description', 'amis ensemble')}"
                )
                
                post_id = get_next_id("photo", data)
                new_post = {
                    "id": post_id,
                    "type": "photo",
                    "status": "draft",
                    "category": "ambiance",
                    "content": {
                        "unsplash_photo_id": photo["id"],
                        "unsplash_user": f"{photo['user']['name']} (@{photo['user']['username']})",
                        "unsplash_query_used": preset_key,
                        "light_overlay": True,
                        "light_overlay_intensity": 0.35,
                        "overlay_logo": True,
                        "logo_color": "black",
                        "apply_filter": False,
                        "trademark_verified": False
                    },
                    "caption": caption_result.get("caption", {}),
                    "created_at": datetime.utcnow().isoformat() + "Z"
                }
                
                data["posts"].append(new_post)
                generated_posts.append(new_post)
                click.echo(f"    Créé: {post_id} (photo: {photo['id']})")
                
            except Exception as e:
                click.echo(f"    Erreur: {e}", err=True)
    
    # Sauvegarder
    save_content(data)
    
    # Générer les images pour les nouveaux posts
    click.echo(f"\n--- Génération des images ---")
    GENERATED_DIR.mkdir(exist_ok=True)
    
    for post in generated_posts:
        try:
            click.echo(f"  Génération image pour {post['id']}...")
            
            if post["type"] == "phrase":
                generator = PhraseGenerator()
                image = generator.generate(post["content"])
            elif post["type"] == "chiffre":
                generator = ChiffreGenerator()
                image = generator.generate(post["content"])
            elif post["type"] == "photo":
                generator = PhotoGenerator()
                image = generator.generate(post["content"])
            else:
                continue
            
            filename = f"{post['id']}.png"
            output_path = generator.save(image, filename)
            
            # Mettre à jour le post avec le chemin de l'image
            for p in data["posts"]:
                if p["id"] == post["id"]:
                    p["generated_image"] = str(output_path)
                    p["status"] = "ready"
                    break
            
            click.echo(f"    Sauvegardé: {output_path}")
            
        except Exception as e:
            click.echo(f"    Erreur génération image: {e}", err=True)
    
    # Sauvegarder les mises à jour
    save_content(data)
    
    click.echo(f"\n=== Génération terminée ===")
    click.echo(f"Posts créés: {len(generated_posts)}")


@cli.command()
@click.option("--dry-run", is_flag=True, help="Afficher sans publier")
@click.option("--force-type", type=click.Choice(["phrase", "chiffre", "photo"]), 
              help="Forcer un type spécifique (ignore l'ordre)")
def publish_next(dry_run: bool, force_type: Optional[str]):
    """Publie le prochain post selon l'ordre strict (Phrase → Chiffre → Photo)."""
    
    # Vérifier la configuration Instagram
    ig_status = check_instagram_availability()
    if not ig_status["ready"] and not dry_run:
        click.echo("Instagram non configuré. Voir docs/INSTAGRAM_SETUP.md", err=True)
        return
    
    data = load_content()
    
    # Déterminer le type à publier
    if force_type:
        next_type = force_type
        click.echo(f"Type forcé: {next_type}")
    else:
        next_type = get_next_post_type()
    
    click.echo(f"\n=== Publication du prochain post ===")
    click.echo(f"Type attendu: {next_type}")
    click.echo(f"Posts déjà publiés: {get_posted_count()}")
    
    # Trouver le post à publier
    post_to_publish = None
    post_index = None
    
    for i, post in enumerate(data.get("posts", [])):
        if post.get("type") == next_type and post.get("status") == "ready":
            post_to_publish = post
            post_index = i
            break
    
    if not post_to_publish:
        click.echo(f"\nAucun post '{next_type}' avec status 'ready' trouvé.", err=True)
        click.echo("Générez du contenu avec: python scheduler.py generate-content")
        return
    
    click.echo(f"\nPost sélectionné: {post_to_publish['id']}")
    click.echo(f"Image: {post_to_publish.get('generated_image', 'N/A')}")
    
    # Vérifier que l'image existe
    image_path = post_to_publish.get("generated_image")
    if not image_path or not Path(image_path).exists():
        click.echo(f"Image non trouvée: {image_path}", err=True)
        return
    
    # Formater la caption
    caption = format_caption(post_to_publish)
    # Afficher un apercu de la caption (sans emojis pour eviter les erreurs Windows)
    caption_preview = caption[:200].encode('ascii', 'replace').decode('ascii')
    click.echo(f"\nCaption preview:\n{caption_preview}...")
    
    if dry_run:
        click.echo("\n[DRY RUN] Publication simulée.")
        return
    
    # Publier
    try:
        click.echo("\nPublication en cours...")
        service = InstagramService()
        result = service.publish_image(Path(image_path), caption)
        
        if result["status"] == "published":
            click.echo(f"\nPublié avec succès! Media ID: {result['media_id']}")
            
            # Mettre à jour le post
            data["posts"][post_index]["status"] = "posted"
            data["posts"][post_index]["published_at"] = datetime.utcnow().isoformat() + "Z"
            data["posts"][post_index]["instagram_media_id"] = result["media_id"]
            data["posts"][post_index]["publish_order"] = get_posted_count() + 1
            
            save_content(data)
            click.echo("Statut mis à jour dans content.json")
        else:
            click.echo(f"\nÉchec de publication: {result['status']}", err=True)
            
    except Exception as e:
        click.echo(f"\nErreur de publication: {e}", err=True)


@cli.command()
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
    
    # Calculer le prochain type
    next_type = get_next_post_type()
    posted_count = get_posted_count()
    
    click.echo(f"\nProchain type à publier: {next_type.upper()}")
    click.echo(f"Position dans le cycle: {(posted_count % 3) + 1}/3 (P-C-Ph)")
    click.echo(f"Total publiés: {posted_count}")
    
    # Afficher la file d'attente
    click.echo("\n--- File d'attente (prochains posts) ---")
    click.echo(f"{'Col 1':<20} {'Col 2':<20} {'Col 3':<20}")
    click.echo("-" * 60)
    
    # Construire la grille des prochains posts selon l'ordre
    queue = []
    type_queues = {
        "phrase": [p for p in ready if p.get("type") == "phrase"],
        "chiffre": [p for p in ready if p.get("type") == "chiffre"],
        "photo": [p for p in ready if p.get("type") == "photo"]
    }
    
    # Simuler les prochains posts
    for i in range(rows * 3):
        type_needed = PUBLISH_ORDER[(posted_count + i) % 3]
        if type_queues[type_needed]:
            post = type_queues[type_needed].pop(0)
            queue.append(post)
        else:
            queue.append({"id": f"[MANQUANT:{type_needed}]", "status": "missing", "type": type_needed})
    
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


@cli.command()
def queue_status():
    """Affiche l'état détaillé de la file d'attente."""
    
    data = load_content()
    posts = data.get("posts", [])
    
    click.echo("\n=== État de la file d'attente ===\n")
    
    # Stats par type et statut
    stats = {}
    for post in posts:
        post_type = post.get("type", "unknown")
        status = post.get("status", "unknown")
        
        if post_type not in stats:
            stats[post_type] = {"ready": 0, "draft": 0, "posted": 0}
        
        if status in stats[post_type]:
            stats[post_type][status] += 1
    
    click.echo(f"{'Type':<12} {'Ready':<8} {'Draft':<8} {'Posted':<8}")
    click.echo("-" * 40)
    
    for post_type in PUBLISH_ORDER:
        if post_type in stats:
            s = stats[post_type]
            click.echo(f"{post_type:<12} {s['ready']:<8} {s['draft']:<8} {s['posted']:<8}")
    
    # Prochains posts
    click.echo(f"\n--- Ordre de publication ---")
    next_type = get_next_post_type()
    posted_count = get_posted_count()
    
    click.echo(f"Posts publiés: {posted_count}")
    click.echo(f"Prochain type: {next_type}")
    click.echo(f"Cycle actuel: {PUBLISH_ORDER}")
    
    # Liste des prochains posts
    click.echo(f"\n--- Prochains posts à publier ---")
    
    for i, post_type in enumerate(PUBLISH_ORDER):
        ready_posts = [p for p in posts if p.get("type") == post_type and p.get("status") == "ready"]
        
        if ready_posts:
            next_post = ready_posts[0]
            indicator = ">" if post_type == next_type else " "
            click.echo(f"{indicator} {post_type.upper()}: {next_post['id']}")
        else:
            indicator = ">" if post_type == next_type else " "
            click.echo(f"{indicator} {post_type.upper()}: [AUCUN POST READY]")
    
    # Services status
    click.echo(f"\n--- État des services ---")
    
    ig_status = check_instagram_availability()
    claude_status = check_claude_availability()
    unsplash_status = check_unsplash_availability()
    
    click.echo(f"Instagram: {'OK' if ig_status['ready'] else 'NON CONFIGURÉ'}")
    click.echo(f"Claude:    {'OK' if claude_status['ready'] else 'NON CONFIGURÉ'}")
    click.echo(f"Unsplash:  {'OK' if unsplash_status['ready'] else 'NON CONFIGURÉ'}")


@cli.command()
@click.option("--status", "filter_status", help="Filtrer par statut (ready, draft, posted)")
@click.option("--type", "filter_type", help="Filtrer par type (phrase, chiffre, photo)")
def list_posts(filter_status: Optional[str], filter_type: Optional[str]):
    """Liste tous les posts avec filtres optionnels."""
    
    data = load_content()
    posts = data.get("posts", [])
    
    if filter_status:
        posts = [p for p in posts if p.get("status") == filter_status]
    if filter_type:
        posts = [p for p in posts if p.get("type") == filter_type]
    
    if not posts:
        click.echo("Aucun post trouvé.")
        return
    
    click.echo(f"\n{'ID':<18} {'Type':<10} {'Status':<10} {'Category':<20}")
    click.echo("-" * 60)
    
    for post in posts:
        click.echo(
            f"{post['id']:<18} {post['type']:<10} {post['status']:<10} "
            f"{post.get('category', 'N/A'):<20}"
        )
    
    click.echo(f"\nTotal: {len(posts)} posts")


if __name__ == "__main__":
    cli()
