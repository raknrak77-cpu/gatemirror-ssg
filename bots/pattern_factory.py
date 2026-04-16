import os
import random
import svgwrite
import math

# ================= KONFIGURASYON =================
OUTPUT_DIR = "assets/patterns"
CANVAS_WIDTH = 3840
CANVAS_HEIGHT = 2160

# Renk paletleri (Pastel tonlar - her kategoriye özel)
COLORS = {
    'tech': ['#a8e6cf', '#d4f1f9', '#b8e1d4', '#c5e8d1', '#e0f7e8', '#b2dfdb', '#c8e6e0'],
    'wellness': ['#b3e5fc', '#81d4fa', '#e1f5fe', '#b8e1f9', '#a6d9f7', '#d4f1f9', '#ccecf8'],
    'eco': ['#c8e6d9', '#a5d6a7', '#d5e8cf', '#c1e0c5', '#e0f2e9', '#b9dfbe', '#d0ecd8'],
    'future-economy': ['#fff3e0', '#ffe0b2', '#ffecb3', '#ffe0b2', '#fff8e1', '#ffd89b', '#ffe5b4'],
    'elearning': ['#ffccbc', '#ffab91', '#ffd8cf', '#ffc8b5', '#ffe0d4', '#ffbba4', '#ffd0c2']
}

# Zorluk seviyeleri
LEVELS = {
    'basic': {'shapes': 25, 'opacity_min': 0.1, 'opacity_max': 0.25},
    'medium': {'shapes': 60, 'opacity_min': 0.1, 'opacity_max': 0.35},
    'complex': {'shapes': 120, 'opacity_min': 0.1, 'opacity_max': 0.45},
    'very_complex': {'shapes': 200, 'opacity_min': 0.1, 'opacity_max': 0.55},
    'extreme': {'shapes': 350, 'opacity_min': 0.1, 'opacity_max': 0.65}
}

def generate_blob_points(x, y, size, complexity=8):
    """Dalgalı/yumuşak şekil için nokta listesi oluşturur"""
    points = []
    angle_step = 360 / complexity
    
    for i in range(complexity):
        angle = math.radians(i * angle_step)
        r = size * (0.7 + random.uniform(-0.2, 0.3))
        px = x + r * math.cos(angle)
        py = y + r * math.sin(angle)
        points.append((px, py))
    
    return points

def add_blob(dwg, x, y, size, color, opacity):
    """Dalgalı yumuşak şekil ekler"""
    complexity = random.randint(6, 12)
    points = generate_blob_points(x, y, size, complexity)
    dwg.add(dwg.polygon(points, fill=color, opacity=opacity))

def add_ellipse(dwg, x, y, size, color, opacity):
    """Elips ekler"""
    rx = random.randint(size//3, size)
    ry = random.randint(size//4, size//2)
    angle = random.randint(0, 360)
    ellipse = dwg.ellipse(center=(x, y), r=(rx, ry), fill=color, opacity=opacity)
    ellipse.rotate(angle, center=(x, y))
    dwg.add(ellipse)

def add_rounded_rect(dwg, x, y, size, color, opacity):
    """Yuvarlak köşeli dikdörtgen ekler"""
    w = random.randint(size//2, size)
    h = random.randint(size//3, size//2)
    radius = random.randint(20, 80)
    angle = random.randint(0, 360)
    rect = dwg.rect(insert=(x - w//2, y - h//2), size=(w, h), rx=radius, ry=radius, fill=color, opacity=opacity)
    rect.rotate(angle, center=(x, y))
    dwg.add(rect)

def add_circle(dwg, x, y, size, color, opacity):
    """Daire ekler"""
    dwg.add(dwg.circle(center=(x, y), r=size//2, fill=color, opacity=opacity))

def generate_pattern(category, level_name, level_config, index):
    """Bir SVG pattern üretir"""
    filename = f"{category}_{level_name}_{index+1:02d}.svg"
    filepath = os.path.join(OUTPUT_DIR, category, filename)
    
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    
    # SVG oluştur
    dwg = svgwrite.Drawing(filepath, size=(CANVAS_WIDTH, CANVAS_HEIGHT))
    
    # Arka plan
    dwg.add(dwg.rect(insert=(0, 0), size=('100%', '100%'), fill='#0a0a0a'))
    
    palette = COLORS.get(category, COLORS['tech'])
    num_shapes = level_config['shapes']
    
    for _ in range(num_shapes):
        # Rastgele pozisyon (kenarlardan taşacak şekilde)
        x = random.randint(-CANVAS_WIDTH//4, CANVAS_WIDTH + CANVAS_WIDTH//4)
        y = random.randint(-CANVAS_HEIGHT//4, CANVAS_HEIGHT + CANVAS_HEIGHT//4)
        
        # Rastgele boyut
        size = random.randint(80, 500)
        
        # Rastgele renk
        color = random.choice(palette)
        
        # Opaklık
        opacity = random.uniform(level_config['opacity_min'], level_config['opacity_max'])
        
        # Şekil tipi
        shape_type = random.choice(['blob', 'ellipse', 'rounded_rect', 'circle'])
        
        if shape_type == 'blob':
            add_blob(dwg, x, y, size, color, opacity)
        elif shape_type == 'ellipse':
            add_ellipse(dwg, x, y, size, color, opacity)
        elif shape_type == 'rounded_rect':
            add_rounded_rect(dwg, x, y, size, color, opacity)
        else:
            add_circle(dwg, x, y, size, color, opacity)
    
    dwg.save()
    print(f"   ✅ {category}/{filename}")
    return filepath

def pattern_factory():
    """Ana üretim fonksiyonu"""
    print("=" * 60)
    print("🎨 PATTERN FACTORY - Vektörel Desen Üretici (svgwrite)")
    print(f"   📐 Canvas: {CANVAS_WIDTH}x{CANVAS_HEIGHT}")
    print("   🎨 Stil: Pastel + Dalgalı şekiller")
    print("=" * 60)
    
    categories = ['tech', 'wellness', 'eco', 'future-economy', 'elearning']
    level_names = ['basic', 'medium', 'complex', 'very_complex', 'extreme']
    total_count = 0
    
    for category in categories:
        print(f"\n📁 {category.upper()} desenleri üretiliyor...")
        
        for level_name in level_names:
            level_config = LEVELS[level_name]
            
            for i in range(5):  # Her seviyeden 5 adet
                print(f"   🎨 {level_name} desen {i+1}/5...")
                generate_pattern(category, level_name, level_config, i)
                total_count += 1
    
    print("\n" + "=" * 60)
    print("🏁 PATTERN FACTORY TAMAMLANDI!")
    print(f"   ✅ Toplam {total_count} desen üretildi")
    print(f"   📁 Klasör: {OUTPUT_DIR}/")
    print("=" * 60)

if __name__ == "__main__":
    pattern_factory()
