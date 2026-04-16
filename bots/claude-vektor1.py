import os
import random
import math

# ================= KONFIG =================
OUTPUT_DIR = "assets/claude"
W = 3840
H = 2160

# ÖNİZLEME MODU: True = görmek için hafif arka plan, False = şeffaf
PREVIEW_MODE = True  # 🔥 BUNU False yaparsan şeffaf olur

# =====================
# KATEGORİ ESTETİK TANIMLARI
# =====================
CATEGORY_STYLES = {
    'tech': {
        'dominant': ['grid_flow', 'data_stream', 'circuit_wave'],
        'secondary': ['sine_horizontal', 'bezier_arc'],
        'stroke_range': (0.5, 8),
        'opacity_range': (0.3, 0.9),  # Opaklık artırıldı
        'description': 'Sert köşeler, veri akışı, devre izleri'
    },
    'wellness': {
        'dominant': ['organic_flow', 'breath_wave', 'spiral_out'],
        'secondary': ['sine_diagonal', 'gentle_arc'],
        'stroke_range': (0.5, 6),
        'opacity_range': (0.3, 0.85),
        'description': 'Yumuşak organik dalgalar, nefes ritmi'
    },
    'eco': {
        'dominant': ['terrain_contour', 'wind_flow', 'growth_spiral'],
        'secondary': ['sine_horizontal', 'bezier_arc'],
        'stroke_range': (0.5, 10),
        'opacity_range': (0.3, 0.9),
        'description': 'Topografya, rüzgar akışı, büyüme spiralleri'
    },
    'future-economy': {
        'dominant': ['market_wave', 'flow_network', 'bezier_arc'],
        'secondary': ['data_stream', 'sine_horizontal'],
        'stroke_range': (0.5, 7),
        'opacity_range': (0.3, 0.85),
        'description': 'Piyasa dalgalanmaları, akış ağları'
    },
    'elearning': {
        'dominant': ['knowledge_wave', 'sine_horizontal', 'gentle_arc'],
        'secondary': ['organic_flow', 'breath_wave'],
        'stroke_range': (0.5, 5),
        'opacity_range': (0.3, 0.8),
        'description': 'Bilgi akışı, yumuşak öğrenme eğrileri'
    }
}

LEVELS = {
    'basic':       {'lines': 6,   'stroke_mult': 1.0},
    'medium':      {'lines': 25,  'stroke_mult': 1.2},
    'complex':     {'lines': 55,  'stroke_mult': 1.5},
    'very_complex':{'lines': 90,  'stroke_mult': 1.8},
    'extreme':     {'lines': 130, 'stroke_mult': 2.2},
}

COUNT_PER_LEVEL = 5

# =====================
# SVG YARDIMCI
# =====================
def svg_open(filepath):
    if PREVIEW_MODE:
        # Önizleme için: açık gri arka plan (çizgiler görünsün)
        bg = f'<rect width="{W}" height="{H}" fill="#f0f0f0"/>\n'
    else:
        # Canlı için: şeffaf arka plan
        bg = f'<rect width="{W}" height="{H}" fill="transparent"/>\n'
    
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{W}" height="{H}" viewBox="0 0 {W} {H}">\n'
        f'{bg}'
    )

def svg_close():
    return '</svg>'

def path_el(d, stroke_width, opacity):
    # stroke="currentColor" → CSS ile renk değiştirilebilir
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

# =====================
# ÇİZGİ ÜRETECLER (AYNI)
# =====================
# ... (tüm üreteç fonksiyonları aynen kalacak)
# sine_horizontal, sine_diagonal, bezier_arc, gentle_arc, organic_flow,
# breath_wave, data_stream, grid_flow, circuit_wave, terrain_contour,
# wind_flow, growth_spiral, market_wave, flow_network, knowledge_wave, spiral_out
# AYNEN KALACAK, sadece stroke rengi değişti

# ... (aradaki tüm üreteç fonksiyonlarını buraya kopyala)

# =====================
# ÜRETEC MAP
# =====================
GENERATORS = {
    'sine_horizontal': sine_horizontal,
    'sine_diagonal':   sine_diagonal,
    'bezier_arc':      bezier_arc,
    'gentle_arc':      gentle_arc,
    'organic_flow':    organic_flow,
    'breath_wave':     breath_wave,
    'data_stream':     data_stream,
    'grid_flow':       grid_flow,
    'circuit_wave':    circuit_wave,
    'terrain_contour': terrain_contour,
    'wind_flow':       wind_flow,
    'growth_spiral':   growth_spiral,
    'market_wave':     market_wave,
    'flow_network':    flow_network,
    'knowledge_wave':  knowledge_wave,
    'spiral_out':      spiral_out,
}

# =====================
# ANA ÜRETIM
# =====================
def generate_pattern(category, level_name, level_config, index):
    style = CATEGORY_STYLES[category]
    filename = f"{category}_{level_name}_{index+1:02d}.svg"
    filepath = os.path.join(OUTPUT_DIR, category, filename)
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    num_lines = level_config['lines']
    sw_min, sw_max = style['stroke_range']
    sw_max *= level_config['stroke_mult']
    op_min, op_max = style['opacity_range']

    svg = svg_open(filepath)

    all_types = style['dominant'] * 3 + style['secondary']
    for _ in range(num_lines):
        line_type = random.choice(all_types)
        sw = random.uniform(sw_min, sw_max)
        op = random.uniform(op_min, op_max)
        gen = GENERATORS.get(line_type)
        if gen:
            svg += gen(sw, op)

    svg += svg_close()

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(svg)

    print(f"   ✅ {category}/{filename} ({num_lines} lines)")

def pattern_factory():
    print("=" * 60)
    print("🎨 CLAUDE PATTERN FACTORY — Kategori Bazlı Estetik")
    print(f"   📐 Canvas: {W}x{H}")
    print(f"   🎨 Renk: currentColor (CSS ile kontrol)")
    print(f"   🖼️ Önizleme modu: {'AÇIK (gri arka plan)' if PREVIEW_MODE else 'KAPALI (şeffaf)'}")
    print(f"   📁 Çıktı: {OUTPUT_DIR}/")
    levels_str = ' → '.join('%s(%d)' % (k, v['lines']) for k, v in LEVELS.items())
    print(f"   📊 Seviyeler: {levels_str}")
    print("=" * 60)

    categories = list(CATEGORY_STYLES.keys())
    total = 0

    for category in categories:
        style = CATEGORY_STYLES[category]
        print(f"\n📁 {category.upper()} — {style['description']}")
        for level_name, level_config in LEVELS.items():
            for i in range(COUNT_PER_LEVEL):
                generate_pattern(category, level_name, level_config, i)
                total += 1

    print("\n" + "=" * 60)
    print(f"🏁 TAMAMLANDI! {total} desen üretildi")
    print(f"   📁 {OUTPUT_DIR}/")
    print("\n💡 CSS ile renk değiştirmek için:")
    print("   .hero-pattern svg { color: #2ecc71; }")
    print("   veya animation ile dalga dalga renk değişimi")
    print("=" * 60)

if __name__ == "__main__":
    pattern_factory()
