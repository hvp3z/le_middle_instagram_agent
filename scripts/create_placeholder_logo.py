"""
Script pour créer des logos placeholder pour les tests.
À remplacer par les vrais logos Le Middle.
"""
from PIL import Image, ImageDraw
from pathlib import Path

def create_pin_logo(color: str, size: int = 400) -> Image.Image:
    """Crée un logo en forme de pin/marqueur style Le Middle."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Couleur du pin
    fill_color = color
    
    # Dessiner le pin (forme simplifiée)
    # Corps du pin (ellipse + triangle)
    center_x = size // 2
    pin_width = int(size * 0.7)
    pin_height = int(size * 0.85)
    
    # Cercle supérieur
    circle_radius = pin_width // 2
    circle_top = int(size * 0.05)
    circle_bottom = circle_top + pin_width
    
    draw.ellipse(
        [center_x - circle_radius, circle_top, 
         center_x + circle_radius, circle_bottom],
        fill=fill_color
    )
    
    # Triangle inférieur (pointe du pin)
    triangle_top = circle_bottom - circle_radius // 2
    triangle_bottom = int(size * 0.95)
    triangle_width = circle_radius
    
    draw.polygon(
        [
            (center_x - triangle_width, triangle_top),
            (center_x + triangle_width, triangle_top),
            (center_x, triangle_bottom)
        ],
        fill=fill_color
    )
    
    # Cercle intérieur (trou)
    inner_color = (255, 255, 255, 255) if color == (0, 0, 0, 255) else (0, 0, 0, 255)
    inner_radius = int(circle_radius * 0.35)
    inner_center_y = circle_top + circle_radius
    
    draw.ellipse(
        [center_x - inner_radius, inner_center_y - inner_radius,
         center_x + inner_radius, inner_center_y + inner_radius],
        fill=inner_color
    )
    
    return img


def main():
    logo_dir = Path(__file__).parent.parent / "assets" / "logo"
    logo_dir.mkdir(parents=True, exist_ok=True)
    
    # Logo noir
    black_logo = create_pin_logo((0, 0, 0, 255), 400)
    black_logo.save(logo_dir / "logo_black.png", "PNG")
    print(f"Created: {logo_dir / 'logo_black.png'}")
    
    # Logo blanc
    white_logo = create_pin_logo((255, 255, 255, 255), 400)
    white_logo.save(logo_dir / "logo_white.png", "PNG")
    print(f"Created: {logo_dir / 'logo_white.png'}")
    
    print("\nPlaceholder logos created. Replace with actual Le Middle logos.")


if __name__ == "__main__":
    main()
