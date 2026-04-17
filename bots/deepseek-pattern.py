import os
import random
import math

# ================= KONFIGÜRASYON =================
OUTPUT_DIR = "assets/all-patterns"
W = 1920
H = 1080

# ================= SEVİYE TANIMLARI =================
LEVELS = {
    'basic': {'lines': 3, 'sw_min': 0.8, 'sw_max': 1.5, 'op_min': 0.3, 'op_max': 0.5},
    'medium': {'lines': 8, 'sw_min': 1.5, 'sw_max': 3.0, 'op_min': 0.4, 'op_max': 0.6},
    'extra': {'lines': 16, 'sw_min': 2.5, 'sw_max': 5.0, 'op_min': 0.5, 'op_max': 0.8},
}
COUNT_PER_LEVEL = 2  # Her seviyeden 2 desen

# ================= RENK PALETİ =================
COLORS = {
    'organic_flow': '#FF1493',      # DeepPink
    'breath_wave': '#00CED1',       # DarkTurquoise
    'spiral_out': '#FFD700',        # Gold
    'gentle_arc': '#8A2BE2',        # BlueViolet
    'sine_diagonal': '#FF4500',     # OrangeRed
    'topographic': '#228B22',       # ForestGreen
    'marble_vein': '#C71585',       # MediumVioletRed
    'fractal_tree': '#D2691E',      # Chocolate
    'particle_trail': '#1E90FF',    # DodgerBlue
    'voronoi': '#FF6347',           # Tomato
    'lemniscate': '#9400D3',        # DarkViolet
    'glassmorphism': '#00BFFF',     # DeepSkyBlue
    'grid_random': '#FF8C00',       # DarkOrange
}

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
    pts = ' '.join(f'{x:.1f},{y:.1f}' for x, y in points)
    return f'<polyline points="{pts}" stroke="{color}" stroke-width="{sw:.1f}" fill="none" opacity="{op:.2f}" stroke-linecap="round" stroke-linejoin="round"/>\n'

def path_el(d, sw, op, color):
    return f'<path d="{d}" stroke="{color}" stroke-width="{sw:.1f}" fill="none" opacity="{op:.2f}" stroke-linecap="round" stroke-linejoin="round"/>\n'

# ================= 1. ORGANIC FLOW =================
def draw_organic_flow(sw, op):
    color = COLORS['organic_flow']
    x = random.uniform(-W * 0.05, W * 0.15)
    y = random.uniform(H * 0.1, H * 0.9)
    pts = [(x, y)]
    freq1 = random.uniform(0.002, 0.008)
    freq2 = random.uniform(0.005, 0.015)
    amp1 = random.uniform(H * 0.05, H * 0.2)
    amp2 = random.uniform(H * 0.01, H * 0.06)
    step = 18
    while x < W * 1.05:
        x += step
        dy = (amp1 * math.sin(freq1 * x) + amp2 * math.sin(freq2 * x))
        y_new = pts[-1][1] + dy * 0.08
        pts.append((x, y_new))
    return polyline_el(pts, sw, op, color)

# ================= 2. BREATH WAVE =================
def draw_breath_wave(sw, op):
    color = COLORS['breath_wave']
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
    return polyline_el(pts, sw, op, color)

# ================= 3. SPIRAL OUT =================
def draw_spiral_out(sw, op):
    color = COLORS['spiral_out']
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
        return polyline_el(pts, sw, op, color)
    return ''

# ================= 4. GENTLE ARC =================
def draw_gentle_arc(sw, op):
    color = COLORS['gentle_arc']
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
    return path_el(d, sw, op, color)

# ================= 5. SINE DIAGONAL =================
def draw_sine_diagonal(sw, op):
    color = COLORS['sine_diagonal']
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
    return polyline_el(pts, sw, op, color)

# ================= 6. TOPOGRAFİK =================
def draw_topographic(sw, op):
    color = COLORS['topographic']
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
    return polyline_el(pts, sw, op, color)

# ================= 7. MERMER DAMARI =================
def draw_marble_vein(sw, op):
    color = COLORS['marble_vein']
    x = random.uniform(-W * 0.05, W * 0.15)
    y = random.uniform(H * 0.1, H * 0.9)
    pts = [(x, y)]
    freq = random.uniform(0.003, 0.015)
    amp = random.uniform(H * 0.02, H * 0.15)
    step = 12
    while x < W * 1.05:
        x += step
        dy = amp * math.sin(freq * x + random.uniform(0, 2*math.pi))
        y_new = pts[-1][1] + dy * 0.15
        pts.append((x, y_new))
    return polyline_el(pts, sw, op, color)

# ================= 8. FRAKTAL AĞAÇ =================
def draw_fractal_tree(sw, op):
    color = COLORS['fractal_tree']
    result = ""
    start_x = random.uniform(W * 0.3, W * 0.7)
    start_y = H * 0.9
    result += f'<line x1="{start_x}" y1="{start_y}" x2="{start_x}" y2="{H*0.5}" stroke="{color}" stroke-width="{sw}" opacity="{op}"/>\n'
    for i in range(int(sw * 2)):
        angle = random.uniform(-0.5, 0.5)
        length = random.uniform(100, 250)
        end_x = start_x + length * math.cos(angle)
        end_y = H*0.5 - length * math.sin(angle)
        result += f'<line x1="{start_x}" y1="{H*0.5}" x2="{end_x}" y2="{end_y}" stroke="{color}" stroke-width="{sw*0.6}" opacity="{op*0.7}"/>\n'
    return result

# ================= 9. PARÇACIK İZİ =================
def draw_particle_trail(sw, op):
    color = COLORS['particle_trail']
    x = random.uniform(0, W)
    y = random.uniform(0, H)
    pts = [(x, y)]
    steps = int(20 + sw * 5)
    for _ in range(steps):
        x += random.uniform(-30, 30)
        y += random.uniform(-30, 30)
        x = max(0, min(W, x))
        y = max(0, min(H, y))
        pts.append((x, y))
    return polyline_el(pts, sw, op, color)

# ================= 10. VORONOI =================
def draw_voronoi(sw, op):
    color = COLORS['voronoi']
    result = ""
    points = []
    num_points = int(5 + sw)
    for _ in range(num_points):
        points.append((random.uniform(0, W), random.uniform(0, H)))
    for i, (x1, y1) in enumerate(points):
        for j, (x2, y2) in enumerate(points):
            if i < j and random.random() > 0.6:
                result += f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="{sw*0.8}" opacity="{op*0.5}"/>\n'
    return result

# ================= 11. LEMNİSCATE =================
def draw_lemniscate(sw, op):
    color = COLORS['lemniscate']
    cx = W / 2
    cy = H / 2
    a = random.uniform(150, 300)
    pts = []
    for t in range(0, 360, 5):
        rad = math.radians(t)
        x = cx + a * math.cos(rad) / (1 + math.sin(rad)**2)
        y = cy + a * math.sin(rad) * math.cos(rad) / (1 + math.sin(rad)**2)
        pts.append((x, y))
    return polyline_el(pts, sw, op, color)

# ================= 12. GLASSMORPHISM =================
def draw_glassmorphism(sw, op):
    color = COLORS['glassmorphism']
    result = ""
    num_rects = int(3 + sw * 0.5)
    for _ in range(num_rects):
        x = random.uniform(0, W)
        y = random.uniform(0, H)
        w = random.uniform(50, 200)
        h = random.uniform(50, 200)
        angle = random.uniform(0, 360)
        result += f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="20" fill="none" stroke="{color}" stroke-width="{sw}" opacity="{op*0.5}" transform="rotate({angle} {x+w/2} {y+h/2})"/>\n'
    return result

# ================= 13. IZGARA + RASTGELE =================
def draw_grid_random(sw, op):
    color = COLORS['grid_random']
    result = ""
    step = random.randint(40, 100)
    for x in range(0, W, step):
        for y in range(0, H, step):
            if random.random() > 0.5:
                w = random.uniform(step*0.3, step*0.8)
                h = random.uniform(step*0.3, step*0.8)
                result += f'<rect x="{x + step*0.1}" y="{y + step*0.1}" width="{w}" height="{h}" fill="none" stroke="{color}" stroke-width="{sw*0.8}" opacity="{op*0.5}"/>\n'
    return result

# ================= TÜM DESENLERİN LİSTESİ =================
ALL_DRAWERS = [
    ("organic_flow", draw_organic_flow),
    ("breath_wave", draw_breath_wave),
    ("spiral_out", draw_spiral_out),
    ("gentle_arc", draw_gentle_arc),
    ("sine_diagonal", draw_sine_diagonal),
    ("topographic", draw_topographic),
    ("marble_vein", draw_marble_vein),
    ("fractal_tree", draw_fractal_tree),
    ("particle_trail", draw_particle_trail),
    ("voronoi", draw_voronoi),
    ("lemniscate", draw_lemniscate),
    ("glassmorphism", draw_glassmorphism),
    ("grid_random", draw_grid_random),
]

# ================= ANA ÜRETİM =================
def generate_all_patterns():
    print("=" * 60)
    print("🎨 13 DESEN TÜRÜ × 3 SEVİYE × 2 TEKRAR")
    print(f"   📐 Canvas: {W}x{H}")
    print(f"   📁 Çıktı: {OUTPUT_DIR}/")
    print("=" * 60)

    total = 0
    for name, drawer in ALL_DRAWERS:
        color = COLORS[name]
        print(f"\n📁 {name.upper()} ({color})")
        
        for level_name, level in LEVELS.items():
            for i in range(COUNT_PER_LEVEL):
                filename = f"{name}_{level_name}_{i+1:02d}.svg"
                filepath = os.path.join(OUTPUT_DIR, name, filename)
                os.makedirs(os.path.dirname(filepath), exist_ok=True)

                sw = random.uniform(level['sw_min'], level['sw_max'])
                op = random.uniform(level['op_min'], level['op_max'])
                num_lines = level['lines']

                svg = svg_open(filepath)
                for _ in range(num_lines):
                    svg += drawer(sw, op)
                svg += svg_close()

                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(svg)

                print(f"   ✅ {level_name}/{filename} ({num_lines} lines, sw={sw:.1f})")
                total += 1

    print("\n" + "=" * 60)
    print(f"🏁 TAMAMLANDI! Toplam {total} desen üretildi")
    print(f"   📁 {OUTPUT_DIR}/")
    print("=" * 60)

if __name__ == "__main__":
    generate_all_patterns()
