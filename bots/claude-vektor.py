import os
import random
import math

# ================= KONFIG =================
OUTPUT_DIR = "assets/claude"
W = 3840
H = 2160

# =====================
# KATEGORİ ESTETİK TANIMLARI
# =====================
CATEGORY_STYLES = {
    'tech': {
        'dominant': ['grid_flow', 'data_stream', 'circuit_wave'],
        'secondary': ['sine_horizontal', 'bezier_arc'],
        'stroke_range': (0.5, 8),
        'opacity_range': (0.15, 0.9),
        'description': 'Sert köşeler, veri akışı, devre izleri'
    },
    'wellness': {
        'dominant': ['organic_flow', 'breath_wave', 'spiral_out'],
        'secondary': ['sine_diagonal', 'gentle_arc'],
        'stroke_range': (0.5, 6),
        'opacity_range': (0.1, 0.7),
        'description': 'Yumuşak organik dalgalar, nefes ritmi'
    },
    'eco': {
        'dominant': ['terrain_contour', 'wind_flow', 'growth_spiral'],
        'secondary': ['sine_horizontal', 'bezier_arc'],
        'stroke_range': (0.5, 10),
        'opacity_range': (0.12, 0.8),
        'description': 'Topografya, rüzgar akışı, büyüme spiralleri'
    },
    'future-economy': {
        'dominant': ['market_wave', 'flow_network', 'bezier_arc'],
        'secondary': ['data_stream', 'sine_horizontal'],
        'stroke_range': (0.5, 7),
        'opacity_range': (0.1, 0.85),
        'description': 'Piyasa dalgalanmaları, akış ağları'
    },
    'elearning': {
        'dominant': ['knowledge_wave', 'sine_horizontal', 'gentle_arc'],
        'secondary': ['organic_flow', 'breath_wave'],
        'stroke_range': (0.5, 5),
        'opacity_range': (0.15, 0.75),
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
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{W}" height="{H}" viewBox="0 0 {W} {H}">\n'
        f'<rect width="{W}" height="{H}" fill="transparent"/>\n'  # Şeffaf arka plan
    )

def svg_close():
    return '</svg>'

def path_el(d, stroke_width, opacity):
    return (
        f'<path d="{d}" stroke="#000000" '
        f'stroke-width="{stroke_width:.1f}" '
        f'fill="none" opacity="{opacity:.2f}" '
        f'stroke-linecap="round" stroke-linejoin="round"/>\n'
    )

def polyline_el(points, stroke_width, opacity):
    pts = ' '.join(f'{x:.1f},{y:.1f}' for x, y in points)
    return (
        f'<polyline points="{pts}" stroke="#000000" '
        f'stroke-width="{stroke_width:.1f}" '
        f'fill="none" opacity="{opacity:.2f}" '
        f'stroke-linecap="round" stroke-linejoin="round"/>\n'
    )

# =====================
# ÇİZGİ ÜRETECLER (TAMAMI AYNI)
# =====================

def sine_horizontal(sw, op):
    start_x = random.uniform(-W * 0.1, W * 0.2)
    y = random.uniform(H * 0.05, H * 0.95)
    amp = random.uniform(H * 0.02, H * 0.18)
    wl = random.uniform(W * 0.05, W * 0.4)
    step = 12
    pts = []
    x = start_x
    while x < W * 1.1:
        cy = y + amp * math.sin(2 * math.pi * (x - start_x) / wl)
        pts.append((x, cy))
        x += step
    return polyline_el(pts, sw, op)

def sine_diagonal(sw, op):
    angle = random.uniform(15, 45) * (1 if random.random() > 0.5 else -1)
    rad = math.radians(angle)
    cx = random.uniform(0, W)
    cy = random.uniform(0, H)
    amp = random.uniform(H * 0.03, H * 0.15)
    wl = random.uniform(W * 0.08, W * 0.35)
    length = max(W, H) * 1.5
    step = 14
    pts = []
    for i in range(int(length / step)):
        t = i * step
        px = cx + t * math.cos(rad) - length / 2 * math.cos(rad)
        py = cy + t * math.sin(rad) - length / 2 * math.sin(rad)
        perp_x = -math.sin(rad)
        perp_y = math.cos(rad)
        offset = amp * math.sin(2 * math.pi * t / wl)
        pts.append((px + offset * perp_x, py + offset * perp_y))
    return polyline_el(pts, sw, op)

def bezier_arc(sw, op):
    edge = random.randint(0, 3)
    if edge == 0:   sx, sy = random.uniform(0, W), 0
    elif edge == 1: sx, sy = W, random.uniform(0, H)
    elif edge == 2: sx, sy = random.uniform(0, W), H
    else:           sx, sy = 0, random.uniform(0, H)
    
    ex = random.uniform(W * 0.1, W * 0.9)
    ey = random.uniform(H * 0.1, H * 0.9)
    
    cx1 = sx + (ex - sx) * random.uniform(0.1, 0.4) + random.uniform(-W * 0.3, W * 0.3)
    cy1 = sy + (ey - sy) * random.uniform(0.1, 0.4) + random.uniform(-H * 0.3, H * 0.3)
    cx2 = sx + (ex - sx) * random.uniform(0.6, 0.9) + random.uniform(-W * 0.2, W * 0.2)
    cy2 = sy + (ey - sy) * random.uniform(0.6, 0.9) + random.uniform(-H * 0.2, H * 0.2)
    
    d = f"M {sx:.1f},{sy:.1f} C {cx1:.1f},{cy1:.1f} {cx2:.1f},{cy2:.1f} {ex:.1f},{ey:.1f}"
    return path_el(d, sw, op)

def gentle_arc(sw, op):
    y = random.uniform(H * 0.1, H * 0.9)
    num_segments = random.randint(3, 7)
    seg_w = W * 1.2 / num_segments
    x = -W * 0.1
    d = f"M {x:.1f},{y:.1f}"
    for _ in range(num_segments):
        cx1 = x + seg_w * 0.33
        cy1 = y + random.uniform(-H * 0.12, H * 0.12)
        cx2 = x + seg_w * 0.67
        cy2 = y + random.uniform(-H * 0.12, H * 0.12)
        ex = x + seg_w
        ey = y + random.uniform(-H * 0.05, H * 0.05)
        d += f" C {cx1:.1f},{cy1:.1f} {cx2:.1f},{cy2:.1f} {ex:.1f},{ey:.1f}"
        x = ex
        y = ey
    return path_el(d, sw, op)

def organic_flow(sw, op):
    x = random.uniform(-W * 0.05, W * 0.15)
    y = random.uniform(H * 0.1, H * 0.9)
    pts = [(x, y)]
    phase1 = random.uniform(0, 2 * math.pi)
    phase2 = random.uniform(0, 2 * math.pi)
    freq1 = random.uniform(0.002, 0.008)
    freq2 = random.uniform(0.005, 0.015)
    amp1 = random.uniform(H * 0.05, H * 0.2)
    amp2 = random.uniform(H * 0.01, H * 0.06)
    step = 18
    while x < W * 1.05:
        x += step
        dy = (amp1 * math.sin(freq1 * x + phase1) +
              amp2 * math.sin(freq2 * x + phase2))
        y_new = pts[-1][1] + dy * 0.08
        pts.append((x, y_new))
    return polyline_el(pts, sw, op)

def breath_wave(sw, op):
    sx = random.uniform(-W * 0.05, W * 0.1)
    cy = random.uniform(H * 0.15, H * 0.85)
    max_amp = random.uniform(H * 0.05, H * 0.22)
    wl = random.uniform(W * 0.15, W * 0.5)
    step = 10
    pts = []
    x = sx
    while x < W * 1.05:
        t = (x - sx) / (W * 1.1)
        env = math.sin(math.pi * t)
        amp = max_amp * env
        y = cy + amp * math.sin(2 * math.pi * (x - sx) / wl)
        pts.append((x, y))
        x += step
    return polyline_el(pts, sw, op)

def data_stream(sw, op):
    y = random.uniform(H * 0.05, H * 0.95)
    amp_base = random.uniform(2, 25)
    wl = random.uniform(30, 120)
    spike_prob = random.uniform(0.02, 0.1)
    step = 8
    pts = []
    x = 0.0
    while x < W:
        if random.random() < spike_prob:
            amp = amp_base * random.uniform(3, 8)
        else:
            amp = amp_base
        y_cur = y + amp * math.sin(2 * math.pi * x / wl)
        pts.append((x, y_cur))
        x += step
    return polyline_el(pts, sw, op)

def grid_flow(sw, op):
    sx = random.uniform(0, W)
    sy = random.uniform(0, H)
    num_turns = random.randint(3, 8)
    d = f"M {sx:.1f},{sy:.1f}"
    x, y = sx, sy
    for _ in range(num_turns):
        if random.random() > 0.5:
            nx = x + random.uniform(-W * 0.25, W * 0.25)
            ny = y
        else:
            nx = x
            ny = y + random.uniform(-H * 0.25, H * 0.25)
        mx = (x + nx) / 2
        my = (y + ny) / 2
        d += f" Q {x:.1f},{y:.1f} {mx:.1f},{my:.1f} L {nx:.1f},{ny:.1f}"
        x, y = nx, ny
    return path_el(d, sw, op)

def circuit_wave(sw, op):
    y = random.uniform(H * 0.1, H * 0.9)
    x = 0.0
    segments = random.randint(4, 10)
    seg_w = W / segments
    d = f"M 0,{y:.1f}"
    for i in range(segments):
        x1 = x + seg_w * 0.2
        mid_y = y + random.choice([-1, 1]) * random.uniform(20, 120)
        x2 = x + seg_w * 0.5
        x3 = x + seg_w * 0.8
        ex = x + seg_w
        d += (f" L {x1:.1f},{y:.1f}"
              f" L {x1:.1f},{mid_y:.1f}"
              f" L {x3:.1f},{mid_y:.1f}"
              f" L {x3:.1f},{y:.1f}"
              f" L {ex:.1f},{y:.1f}")
        x = ex
    return path_el(d, sw, op)

def terrain_contour(sw, op):
    base_y = random.uniform(H * 0.2, H * 0.8)
    peaks = []
    for _ in range(random.randint(2, 5)):
        peaks.append((random.uniform(0, W), random.uniform(-H * 0.25, H * 0.25)))
    step = 10
    pts = []
    x = -W * 0.05
    while x < W * 1.05:
        y = base_y
        for px, pamp in peaks:
            dist = abs(x - px)
            sigma = random.uniform(W * 0.1, W * 0.35)
            y += pamp * math.exp(-0.5 * (dist / sigma) ** 2)
        pts.append((x, y))
        x += step
    return polyline_el(pts, sw, op)

def wind_flow(sw, op):
    y = random.uniform(H * 0.05, H * 0.95)
    harmonics = [(random.uniform(0.001, 0.005), random.uniform(20, 150), random.uniform(0, 6.28))
                 for _ in range(random.randint(2, 4))]
    step = 10
    pts = []
    x = -W * 0.05
    while x < W * 1.05:
        cy = y
        for freq, amp, phase in harmonics:
            cy += amp * math.sin(freq * x + phase)
        pts.append((x, cy))
        x += step
    return polyline_el(pts, sw, op)

def growth_spiral(sw, op):
    cx = random.uniform(W * 0.2, W * 0.8)
    cy = random.uniform(H * 0.2, H * 0.8)
    a = random.uniform(5, 20)
    b = random.uniform(0.08, 0.25)
    start_angle = random.uniform(0, 2 * math.pi)
    turns = random.uniform(1.5, 5)
    step = 0.05
    pts = []
    theta = start_angle
    while theta < start_angle + turns * 2 * math.pi:
        r = a * math.exp(b * (theta - start_angle))
        x = cx + r * math.cos(theta)
        y = cy + r * math.sin(theta)
        if 0 <= x <= W and 0 <= y <= H:
            pts.append((x, y))
        elif pts:
            break
        theta += step
    if len(pts) > 2:
        return polyline_el(pts, sw, op)
    return ''

def market_wave(sw, op):
    x = 0.0
    y = random.uniform(H * 0.2, H * 0.8)
    trend = random.uniform(-H * 0.0002, H * 0.0002)
    volatility = random.uniform(5, 60)
    mean_revert = 0.05
    pts = [(x, y)]
    step = 6
    while x < W:
        x += step
        drift = trend
        shock = random.gauss(0, volatility)
        mean_r = mean_revert * (H / 2 - y)
        y = y + drift + shock * 0.3 + mean_r
        y = max(H * 0.05, min(H * 0.95, y))
        pts.append((x, y))
    return polyline_el(pts, sw, op)

def flow_network(sw, op):
    num_sources = random.randint(3, 6)
    target_x = random.uniform(W * 0.3, W * 0.7)
    target_y = random.uniform(H * 0.3, H * 0.7)
    result = ''
    for _ in range(num_sources):
        sx = random.uniform(0, W)
        sy = random.uniform(0, H)
        cx1 = sx + (target_x - sx) * random.uniform(0.2, 0.5)
        cy1 = sy + random.uniform(-H * 0.2, H * 0.2)
        cx2 = target_x + random.uniform(-W * 0.1, W * 0.1)
        cy2 = target_y + random.uniform(-H * 0.1, H * 0.1)
        d = f"M {sx:.1f},{sy:.1f} C {cx1:.1f},{cy1:.1f} {cx2:.1f},{cy2:.1f} {target_x:.1f},{target_y:.1f}"
        result += path_el(d, sw, op)
    return result

def knowledge_wave(sw, op):
    sx = -W * 0.05
    y = random.uniform(H * 0.2, H * 0.8)
    base_wl = random.uniform(W * 0.25, W * 0.5)
    amp = random.uniform(H * 0.04, H * 0.15)
    step = 10
    pts = []
    x = sx
    while x < W * 1.05:
        t = (x - sx) / (W * 1.1)
        wl = base_wl * (1 - t * 0.6)
        wl = max(wl, 40)
        y_cur = y + amp * math.sin(2 * math.pi * (x - sx) / wl)
        pts.append((x, y_cur))
        x += step
    return polyline_el(pts, sw, op)

def spiral_out(sw, op):
    cx = random.uniform(W * 0.25, W * 0.75)
    cy = random.uniform(H * 0.25, H * 0.75)
    start_r = random.uniform(5, 30)
    grow = random.uniform(8, 25)
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
    if len(pts) > 2:
        return polyline_el(pts, sw, op)
    return ''

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
    print(f"   🎨 Renk: Siyah, değişken opaklık")
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
    print("=" * 60)

if __name__ == "__main__":
    pattern_factory()
