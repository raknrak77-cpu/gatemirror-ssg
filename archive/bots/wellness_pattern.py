import os
import random
import math

# ================= KONFIGÜRASYON =================
OUTPUT_DIR = "assets/wellness-variations"
W = 3840
H = 2160

# ================= VARYASYON SEVİYELERİ =================
VARIATIONS = {
    'horizontal_spiral': {'count': 3, 'lines': 8},
    'elliptic_spiral': {'count': 3, 'lines': 12},
    'wavy_spiral': {'count': 3, 'lines': 10},
    'horizontal_flow': {'count': 3, 'lines': 15},
    'layered_combo': {'count': 3, 'lines': 20},  # 3 katman tek dosyada
}
COUNT_PER_VARIATION = 6

# ================= SVG YARDIMCI =================
def svg_open(filepath):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{W}" height="{H}" viewBox="0 0 {W} {H}">\n'
        f'<rect width="{W}" height="{H}" fill="transparent"/>\n'
    )

def svg_close():
    return '</svg>'

def path_el(d, stroke_width, opacity):
    return (
        f'<path d="{d}" stroke="currentColor" '
        f'stroke-width="{stroke_width:.1f}" '
        f'fill="none" opacity="{opacity:.2f}" '
        f'stroke-linecap="round" stroke-linejoin="round"/>\n'
    )

def polyline_el(points, stroke_width, opacity):
    pts = ' '.join(f'{x:.1f},{y:.1f}' for x, y in points)
    return (
        f'<polyline points="{pts}" stroke="currentColor" '
        f'stroke-width="{stroke_width:.1f}" '
        f'fill="none" opacity="{opacity:.2f}" '
        f'stroke-linecap="round" stroke-linejoin="round"/>\n'
    )

# ================= VARYASYON 1: YATAY SPİRAL =================
def horizontal_spiral_line(sw, op):
    """Yatay düzleme yatırılmış spiral (eliptik)"""
    cx = random.uniform(W * 0.2, W * 0.8)
    cy = random.uniform(H * 0.3, H * 0.7)
    start_r = random.uniform(10, 40)
    grow = random.uniform(12, 30)
    theta = 0
    pts = []
    while True:
        r = start_r + grow * theta / (2 * math.pi)
        # Yatayda uzat (x), dikeyde sıkıştır (y)
        x = cx + r * math.cos(theta) * 1.8
        y = cy + r * math.sin(theta) * 0.4
        if x < -W * 0.1 or x > W * 1.1 or y < -H * 0.1 or y > H * 1.1:
            break
        pts.append((x, y))
        theta += 0.05
    if len(pts) > 2:
        return polyline_el(pts, sw, op)
    return ''

# ================= VARYASYON 2: ELİPTİK SPİRAL =================
def elliptic_spiral_line(sw, op):
    """Elips şeklinde, yumurta formunda spiral"""
    cx = random.uniform(W * 0.3, W * 0.7)
    cy = random.uniform(H * 0.3, H * 0.7)
    start_r = random.uniform(15, 50)
    grow = random.uniform(10, 25)
    theta = 0
    pts = []
    # Elips oranları
    x_ratio = random.uniform(1.3, 2.0)  # yatay uzama
    y_ratio = random.uniform(0.4, 0.8)  # dikey kısalma
    while True:
        r = start_r + grow * theta / (2 * math.pi)
        x = cx + r * math.cos(theta) * x_ratio
        y = cy + r * math.sin(theta) * y_ratio
        if x < -W * 0.1 or x > W * 1.1 or y < -H * 0.1 or y > H * 1.1:
            break
        pts.append((x, y))
        theta += 0.05
    if len(pts) > 2:
        return polyline_el(pts, sw, op)
    return ''

# ================= VARYASYON 3: DALGALI SPİRAL =================
def wavy_spiral_line(sw, op):
    """Dalgalı, kıvrımlı spiral"""
    cx = random.uniform(W * 0.25, W * 0.75)
    cy = random.uniform(H * 0.25, H * 0.75)
    start_r = random.uniform(10, 35)
    grow = random.uniform(10, 28)
    theta = 0
    pts = []
    # Dalga parametreleri
    wave_amp = random.uniform(20, 60)
    wave_freq = random.uniform(0.02, 0.08)
    while True:
        r = start_r + grow * theta / (2 * math.pi)
        x = cx + r * math.cos(theta)
        y = cy + r * math.sin(theta)
        # Dalga ekle
        y += wave_amp * math.sin(theta * wave_freq * 2 * math.pi)
        x += wave_amp * 0.3 * math.cos(theta * wave_freq * 1.5)
        if x < -W * 0.1 or x > W * 1.1 or y < -H * 0.1 or y > H * 1.1:
            break
        pts.append((x, y))
        theta += 0.05
    if len(pts) > 2:
        return polyline_el(pts, sw, op)
    return ''

# ================= VARYASYON 4: YATAY AKIŞ (UZUN DALGALAR) =================
def horizontal_flow_line(sw, op):
    """Uzun dalgalı yatay akış - sinüs dalgaları çok uzun"""
    start_x = random.uniform(-W * 0.1, W * 0.2)
    y = random.uniform(H * 0.1, H * 0.9)
    # Dalga boyu ÇOK UZUN (W*0.8 ile W*1.5 arası)
    amp = random.uniform(H * 0.03, H * 0.12)
    wl = random.uniform(W * 0.8, W * 1.5)  # Uzun dalga
    step = 15
    pts = []
    x = start_x
    while x < W * 1.1:
        cy = y + amp * math.sin(2 * math.pi * (x - start_x) / wl)
        pts.append((x, cy))
        x += step
    return polyline_el(pts, sw, op)

# ================= VARYASYON 5: KATMANLI KOMBO (TEK DOSYADA 3 KATMAN) =================
def layered_combo(sw, op):
    """Tek bir çağrıda 3 farklı tip çizgi (katman efekti)"""
    result = ""
    
    # Katman 1: Yatay spiral (arka, silik)
    result += horizontal_spiral_line(sw * 0.6, op * 0.3)
    
    # Katman 2: Eliptik spiral (orta)
    result += elliptic_spiral_line(sw * 0.8, op * 0.6)
    
    # Katman 3: Dalgalı spiral (ön, belirgin)
    result += wavy_spiral_line(sw * 1.2, op * 0.9)
    
    return result

# ================= ÜRETEC MAP =================
GENERATORS = {
    'horizontal_spiral': horizontal_spiral_line,
    'elliptic_spiral': elliptic_spiral_line,
    'wavy_spiral': wavy_spiral_line,
    'horizontal_flow': horizontal_flow_line,
    'layered_combo': layered_combo,
}

# ================= ANA ÜRETİM =================
def generate_pattern(variation_name, variation_config, index):
    filename = f"wellness_{variation_name}_{index+1:02d}.svg"
    filepath = os.path.join(OUTPUT_DIR, variation_name, filename)
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    num_lines = variation_config['lines']
    svg = svg_open(filepath)

    gen = GENERATORS[variation_name]
    for _ in range(num_lines):
        sw = random.uniform(0.8, 5)   # çizgi kalınlığı
        op = random.uniform(0.2, 0.8) # opaklık
        svg += gen(sw, op)

    svg += svg_close()

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(svg)

    print(f"   ✅ {variation_name}/{filename} ({num_lines} lines)")

def pattern_factory():
    print("=" * 60)
    print("🌿 WELLNESS VARYASYON FACTORY")
    print(f"   📐 Canvas: {W}x{H}")
    print(f"   🎨 Renk: currentColor (CSS ile kontrol)")
    print(f"   📁 Çıktı: {OUTPUT_DIR}/")
    print("=" * 60)

    total = 0
    for var_name, var_config in VARIATIONS.items():
        print(f"\n📊 Varyasyon: {var_name.upper()} ({var_config['lines']} çizgi/kombinasyon)")
        for i in range(COUNT_PER_VARIATION):
            generate_pattern(var_name, var_config, i)
            total += 1

    print("\n" + "=" * 60)
    print(f"🏁 TAMAMLANDI! {total} desen üretildi")
    print(f"   📁 {OUTPUT_DIR}/")
    print("\n📂 Klasör yapısı:")
    print("   assets/wellness-variations/")
    print("   ├── horizontal_spiral/")
    print("   ├── elliptic_spiral/")
    print("   ├── wavy_spiral/")
    print("   ├── horizontal_flow/")
    print("   └── layered_combo/")
    print("\n💡 CSS ile renk değiştirmek için:")
    print("   .wellness-bg svg { color: #7a4a6a; }")
    print("=" * 60)

if __name__ == "__main__":
    pattern_factory()
