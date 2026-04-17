import os
import random
import math

# ================= KONFIGÜRASYON =================
OUTPUT_DIR = "assets/all-patterns/spiral_out"
W = 1920
H = 1080

# ================= SEVİYE TANIMLARI =================
LEVELS = {
    'basic': {'lines': 4, 'sw_min': 0.8, 'sw_max': 1.5, 'op_min': 0.3, 'op_max': 0.5},
    'medium': {'lines': 10, 'sw_min': 1.5, 'sw_max': 2.5, 'op_min': 0.4, 'op_max': 0.6},
}
COUNT_PER_LEVEL = 4

# ================= RENK (GRİ TONLARI) =================
GRAY_TONES = ['#222222', '#333333', '#444444', '#555555', '#666666', '#777777']

# ================= SVG YARDIMCI =================
def svg_open(filepath):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{W}" height="{H}" viewBox="0 0 {W} {H}">\n'
        f'<rect width="{W}" height="{H}" fill="#e0e0e0"/>\n'
    )

def svg_close():
    return '</svg>'

def polyline_el(points, sw, op, color):
    if len(points) < 2:
        return ''
    pts = ' '.join(f'{x:.1f},{y:.1f}' for x, y in points)
    return f'<polyline points="{pts}" stroke="{color}" stroke-width="{sw:.1f}" fill="none" opacity="{op}" stroke-linecap="round" stroke-linejoin="round"/>\n'

# ========== 1. DAİRESEL SPIRAL ==========
def draw_circular_spiral(sw, op, color):
    """Dairesel spiral - merkez rastgele"""
    cx = random.uniform(W * 0.2, W * 0.8)
    cy = random.uniform(H * 0.2, H * 0.8)
    start_r = random.uniform(10, 50)
    grow = random.uniform(8, 22)
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
    return polyline_el(pts, sw, op, color)

# ========== 2. ELİPTİK SPIRAL ==========
def draw_elliptic_spiral(sw, op, color, var_num):
    """Eliptik spiral - yatay veya dikey uzamış"""
    cx = random.uniform(W * 0.2, W * 0.8)
    cy = random.uniform(H * 0.2, H * 0.8)
    start_r = random.uniform(10, 50)
    grow = random.uniform(8, 22)
    
    # Elips oranları (varyasyon numarasına göre değişir)
    if var_num % 2 == 0:
        x_ratio = random.uniform(1.3, 2.2)  # yatay uzun
        y_ratio = random.uniform(0.4, 0.8)  # dikey kısa
    else:
        x_ratio = random.uniform(0.4, 0.8)  # yatay kısa
        y_ratio = random.uniform(1.3, 2.2)  # dikey uzun
    
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
    return polyline_el(pts, sw, op, color)

# ========== 3. İZOHİPST SPIRAL ==========
def draw_contour_spiral(sw, op, color):
    """İzohips tarzı - iç içe geçmiş, sıkı spiraller"""
    cx = random.uniform(W * 0.25, W * 0.75)
    cy = random.uniform(H * 0.25, H * 0.75)
    start_r = random.uniform(5, 25)
    grow = random.uniform(4, 12)  # Daha yavaş büyüme
    theta = 0
    pts = []
    
    # Daha fazla tur için
    max_theta = random.uniform(8 * math.pi, 16 * math.pi)
    
    while theta < max_theta:
        r = start_r + grow * theta / (2 * math.pi)
        # Hafif eliptik yaparak daha doğal topografik görünüm
        x_ratio = random.uniform(0.9, 1.1)
        y_ratio = random.uniform(0.9, 1.1)
        x = cx + r * math.cos(theta) * x_ratio
        y = cy + r * math.sin(theta) * y_ratio
        if 0 <= x <= W and 0 <= y <= H:
            pts.append((x, y))
        elif len(pts) > 10:
            break
        theta += 0.05
    
    if len(pts) > 2:
        # Başlangıç ve bitişi birleştir (kapalı eğri)
        dist = math.hypot(pts[0][0] - pts[-1][0], pts[0][1] - pts[-1][1])
        if dist < 50:
            pts.append(pts[0])
        return polyline_el(pts, sw, op, color)
    return ''

# ================= ANA ÜRETİM =================
def generate_spiral_variations():
    print("=" * 60)
    print("🌀 SPIRAL OUT VARYASYONLARI (60 adet)")
    print(f"   📐 Canvas: {W}x{H}")
    print(f"   📁 Çıktı: {OUTPUT_DIR}/")
    print("=" * 60)
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    total = 0
    
    # ===== 1. DAİRESEL SPİRALLER (20 varyasyon) =====
    print("\n🔘 DAİRESEL SPİRALLER (20 adet)")
    for v in range(1, 21):
        color = random.choice(GRAY_TONES)
        for level_name, level in LEVELS.items():
            filename = f"spiral_circular_{level_name}_{v:02d}.svg"
            filepath = os.path.join(OUTPUT_DIR, filename)
            
            sw = random.uniform(level['sw_min'], level['sw_max'])
            op = random.uniform(level['op_min'], level['op_max'])
            num_lines = level['lines']
            
            svg = svg_open(filepath)
            for _ in range(num_lines):
                svg += draw_circular_spiral(sw, op, color)
            svg += svg_close()
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(svg)
            print(f"   ✅ {filename}")
            total += 1
    
    # ===== 2. ELİPTİK SPİRALLER (20 varyasyon) =====
    print("\n🥚 ELİPTİK SPİRALLER (20 adet)")
    for v in range(1, 21):
        color = random.choice(GRAY_TONES)
        for level_name, level in LEVELS.items():
            filename = f"spiral_elliptic_{level_name}_{v:02d}.svg"
            filepath = os.path.join(OUTPUT_DIR, filename)
            
            sw = random.uniform(level['sw_min'], level['sw_max'])
            op = random.uniform(level['op_min'], level['op_max'])
            num_lines = level['lines']
            
            svg = svg_open(filepath)
            for _ in range(num_lines):
                svg += draw_elliptic_spiral(sw, op, color, v)
            svg += svg_close()
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(svg)
            print(f"   ✅ {filename}")
            total += 1
    
    # ===== 3. İZOHİPST SPİRALLER (20 varyasyon) =====
    print("\n🗺️ İZOHİPST SPİRALLER (20 adet)")
    for v in range(1, 21):
        color = random.choice(GRAY_TONES)
        for level_name, level in LEVELS.items():
            filename = f"spiral_contour_{level_name}_{v:02d}.svg"
            filepath = os.path.join(OUTPUT_DIR, filename)
            
            sw = random.uniform(level['sw_min'], level['sw_max'])
            op = random.uniform(level['op_min'], level['op_max'])
            num_lines = level['lines']
            
            svg = svg_open(filepath)
            for _ in range(num_lines):
                svg += draw_contour_spiral(sw, op, color)
            svg += svg_close()
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(svg)
            print(f"   ✅ {filename}")
            total += 1
    
    print("\n" + "=" * 60)
    print(f"🏁 TAMAMLANDI! Toplam {total} desen üretildi")
    print(f"   📁 {OUTPUT_DIR}/")
    print("\n📂 DOSYA İSİMLENDİRME:")
    print("   spiral_circular_basic_01.svg  → Dairesel, basic, varyasyon 1")
    print("   spiral_elliptic_medium_05.svg → Eliptik, medium, varyasyon 5")
    print("   spiral_contour_basic_12.svg   → İzohips, basic, varyasyon 12")
    print("=" * 60)

if __name__ == "__main__":
    generate_spiral_variations()
