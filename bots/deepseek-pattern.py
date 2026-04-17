import os
import random
import math

# ================= KONFIGÜRASYON =================
OUTPUT_DIR = "assets/all-patterns/spiral_out"
W = 1920
H = 1080

# ================= SEVİYE TANIMLARI =================
LEVELS = {
    'basic': {'lines': 3, 'sw_min': 3.5, 'sw_max': 3.5, 'op_min': 0.5, 'op_max': 1},
    'medium': {'lines': 4, 'sw_min': 4.5, 'sw_max': 6.5, 'op_min': 0.7, 'op_max': 1},
}

# ================= SVG YARDIMCI =================
def svg_open(filepath):
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">\n'

def svg_close():
    return '</svg>'

def polyline_el(points, sw, op):
    if len(points) < 2:
        return ''
    pts = ' '.join(f'{x:.1f},{y:.1f}' for x, y in points)
    return f'<polyline points="{pts}" stroke="currentColor" stroke-width="{sw:.1f}" fill="none" opacity="{op}" stroke-linecap="round" stroke-linejoin="round"/>\n'

def draw_circular_spiral(sw, op):
    cx = random.uniform(W * 0.3, W * 0.8)
    cy = random.uniform(H * 0.3, H * 0.8)
    start_r = random.uniform(10, 50)
    grow = random.uniform(11, 22)
    theta = 0
    pts = []
    while True:
        r = start_r + grow * theta / (2 * math.pi)
        x = cx + r * math.cos(theta)
        y = cy + r * math.sin(theta)
        if x < -W * 0.1 or x > W * 1.1 or y < -H * 0.1 or y > H * 1.1:
            break
        pts.append((x, y))
        theta += 0.06
    return polyline_el(pts, sw, op)

def draw_elliptic_spiral(sw, op, var_num):
    cx = random.uniform(W * 0.2, W * 0.8)
    cy = random.uniform(H * 0.2, H * 0.8)
    start_r = random.uniform(10, 50)
    grow = random.uniform(11, 22)
    
    if var_num % 2 == 0:
        x_ratio = random.uniform(1.3, 2.2)
        y_ratio = random.uniform(0.4, 0.8)
    else:
        x_ratio = random.uniform(0.4, 0.8)
        y_ratio = random.uniform(1.3, 2.2)
    
    theta = 0
    pts = []
    while True:
        r = start_r + grow * theta / (2 * math.pi)
        x = cx + r * math.cos(theta) * x_ratio
        y = cy + r * math.sin(theta) * y_ratio
        if x < -W * 0.1 or x > W * 1.1 or y < -H * 0.1 or y > H * 1.1:
            break
        pts.append((x, y))
        theta += 0.06
    return polyline_el(pts, sw, op)

# ================= ANA ÜRETİM =================
def generate_spiral_variations():
    print("=" * 60)
    print("🌀 SPIRAL OUT VARYASYONLARI (120 adet)")
    print(f"   📐 Canvas: {W}x{H}")
    print(f"   🎨 Renk: currentColor (CSS ile kontrol)")
    print(f"   📁 Çıktı: {OUTPUT_DIR}/")
    print("=" * 60)
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    total = 0
    
    # ===== 1. DAİRESEL SPİRALLER (30 varyasyon) =====
    print("\n🔘 DAİRESEL SPİRALLER (30 adet)")
    for v in range(1, 31):  # 🔥 20 → 30
        for level_name, level in LEVELS.items():
            filename = f"spiral_circular_{level_name}_{v:02d}.svg"
            filepath = os.path.join(OUTPUT_DIR, filename)
            
            sw = random.uniform(level['sw_min'], level['sw_max'])
            op = random.uniform(level['op_min'], level['op_max'])
            num_lines = level['lines']
            
            svg = svg_open(filepath)
            for _ in range(num_lines):
                svg += draw_circular_spiral(sw, op)
            svg += svg_close()
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(svg)
            print(f"   ✅ {filename}")
            total += 1
    
    # ===== 2. ELİPTİK SPİRALLER (30 varyasyon) =====
    print("\n🥚 ELİPTİK SPİRALLER (30 adet)")
    for v in range(1, 31):  # 🔥 20 → 30
        for level_name, level in LEVELS.items():
            filename = f"spiral_elliptic_{level_name}_{v:02d}.svg"
            filepath = os.path.join(OUTPUT_DIR, filename)
            
            sw = random.uniform(level['sw_min'], level['sw_max'])
            op = random.uniform(level['op_min'], level['op_max'])
            num_lines = level['lines']
            
            svg = svg_open(filepath)
            for _ in range(num_lines):
                svg += draw_elliptic_spiral(sw, op, v)
            svg += svg_close()
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(svg)
            print(f"   ✅ {filename}")
            total += 1
    
    print("\n" + "=" * 60)
    print(f"🏁 TAMAMLANDI! Toplam {total} desen üretildi")
    print(f"   📁 {OUTPUT_DIR}/")
    print("\n📊 HESAPLAMA:")
    print("   30 dairesel × 2 seviye = 60")
    print("   30 eliptik × 2 seviye = 60")
    print("   TOPLAM = 120")
    print("\n💡 CSS ile renk değiştirmek için:")
    print("   .pattern svg { color: #2ecc71; }")
    print("=" * 60)

if __name__ == "__main__":
    generate_spiral_variations()
                        
