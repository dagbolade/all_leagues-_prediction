"""
Generate PWA Icons

Creates placeholder icons for the PWA manifest.
In production, replace with actual designed icons.
"""

from PIL import Image, ImageDraw, ImageFont
import os

def create_icon(size, output_path):
    """Create a simple icon with football emoji"""
    # Create image with gradient background
    img = Image.new('RGB', (size, size), color='#2E8B57')
    draw = ImageDraw.Draw(img)
    
    # Draw circle
    margin = size // 10
    draw.ellipse([margin, margin, size-margin, size-margin], fill='#32CD32', outline='white', width=size//20)
    
    # Try to add text
    try:
        font_size = size // 3
        font = ImageFont.truetype("arial.ttf", font_size)
    except:
        font = ImageFont.load_default()
    
    # Draw football emoji or text
    text = "⚽"
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    position = ((size - text_width) // 2, (size - text_height) // 2)
    
    draw.text(position, text, fill='white', font=font)
    
    # Save
    img.save(output_path, 'PNG')
    print(f"Created {output_path}")


def main():
    """Generate all required icon sizes"""
    # Create icons directory
    icons_dir = os.path.join(os.path.dirname(__file__), 'app', 'static', 'icons')
    os.makedirs(icons_dir, exist_ok=True)
    
    # Icon sizes for PWA
    sizes = [72, 96, 128, 144, 152, 192, 384, 512]
    
    for size in sizes:
        output_path = os.path.join(icons_dir, f'icon-{size}x{size}.png')
        create_icon(size, output_path)
    
    print(f"\n✅ Generated {len(sizes)} icons in {icons_dir}")
    print("\nNote: These are placeholder icons. For production, create professional icons with:")
    print("- Your app logo")
    print("- Proper branding colors")
    print("- High-quality graphics")
    print("\nRecommended tools:")
    print("- https://realfavicongenerator.net/")
    print("- https://www.pwabuilder.com/imageGenerator")


if __name__ == '__main__':
    main()
