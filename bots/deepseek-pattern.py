import os
import random
import math

# ================= KONFIGÜRASYON =================
OUTPUT_DIR = "assets/selected-patterns"
W = 1920
H = 1080

# ================= SEVİYE TANIMLARI =================
LEVELS = {
    'basic': {'lines': 3, 'sw_min': 0.8, 'sw_max': 1.5, 'op_min': 0.3, 'op_max': 0.5},
    'medium': {'lines': 8, 'sw_min': 1.5, 'sw_max': 3.0, 'op_min': 0.4, 'op_max': 0.6},
    'extra': {'lines': 16, 'sw_min': 2.5, 'sw_max': 5.0, 'op_min': 0.5, 'op_max': 0.8},
}
COUNT_PER_LEVEL = 2

# ================= RENK PALETİ =================
COLORS = {
    # BEĞENDİKLERİN (7)
    'lemniscate': '#9400D3',        # DarkViolet
    'breath_wave': '#00CED1',       # DarkTurquoise
    'organic_flow': '#FF1493',      # DeepPink
    'spiral_out': '#FFD700',        # Gold
    'voronoi': '#FF6347',           # Tomato
    'fractal_tree': '#D2691E',      # Chocolate
    'glassmorphism': '#00BFFF',     # DeepSkyBlue
    
    # YENİLER (8)
    'lissajous': '#2E8B57',         # SeaGreen
    'noise_walk': '#FF4500',        # OrangeRed
    'superformula': '#8A2BE2',      # BlueViolet
    'horseshoe': '#DC143C',         # Crimson
    'delaunay': '#20B2AA',          # LightSeaGreen
    'random_branch': '#CD853F',     # Peru
    'particle_network': '#4682B4',  # SteelBlue
    'reaction_diffusion': '#DA70D6', # Orchid
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
    return f'<polyline points="{pts}" stroke="{color}" stroke-width="{sw:.1f}" fill="none" opacity="{op}" stroke-linecap="round" stroke-linejoin="round"/>\n'

def path_el(d, sw, op, color):
    return f'<path d="{d}" stroke="{color}" stroke-width="{sw:.1f}" fill="none" opacity="{op}" stroke-linecap="round" stroke-linejoin="round"/>\n'

# ========== 1. LEMNISCATE (BEĞENDİN) ==========
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

# ========== 2. BREATH WAVE (BEĞENDİN) ==========
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

# ========== 3. ORGANIC FLOW (BEĞENDİN) ==========
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

# ========== 4. SPIRAL OUT (BEĞENDİN) ==========
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

# ========== 5. VORONOI (BEĞENDİN) ==========
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

# ========== 6. FRACTAL TREE (BEĞENDİN) ==========
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

# ========== 7. GLASSMORPHISM (BEĞENDİN) ==========
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

# ========== 8. LISSAJOUS (YENİ) ==========
def draw_lissajous(sw, op):
    color = COLORS['lissajous']
    cx, cy = W/2, H/2
    a = random.uniform(200, 350)
    b = random.uniform(200, 350)
    freq_x = random.choice([1,2,3,4])
    freq_y = random.choice([1,2,3,4])
    phase = random.uniform(0, math.pi/2)
    pts = []
    for t in range(0, 360, 3):
        rad = math.radians(t)
        x = cx + a * math.sin(freq_x * rad + phase)
        y = cy + b * math.cos(freq_y * rad)
        pts.append((x, y))
    return polyline_el(pts, sw, op, color)

# ========== 9. NOISE WALK (YENİ) ==========
def draw_noise_walk(sw, op):
    color = COLORS['noise_walk']
    x = W/2
    y = H/2
    pts = [(x, y)]
    step = 15
    angle = 0
    for _ in range(50):
        angle += random.uniform(-0.5, 0.5)
        x += math.cos(angle) * step
        y += math.sin(angle) * step
        x = max(0, min(W, x))
        y = max(0, min(H, y))
        pts.append((x, y))
    return polyline_el(pts, sw, op, color)

# ========== 10. SUPERFORMULA (YENİ) ==========
def draw_superformula(sw, op):
    color = COLORS['superformula']
    cx, cy = W/2, H/2
    a = b = random.uniform(150, 250)
    m = random.choice([4,5,6,7,8])
    n1 = random.uniform(0.5, 1.5)
    n2 = random.uniform(0.5, 1.5)
    n3 = random.uniform(0.5, 1.5)
    pts = []
    for t in range(0, 360, 2):
        rad = math.radians(t)
        r = ((abs(math.cos(m * rad / 4))**n2 + abs(math.sin(m * rad / 4))**n3) ** (-1/n1)) * a
        x = cx + r * math.cos(rad)
        y = cy + r * math.sin(rad)
        pts.append((x, y))
    return polyline_el(pts, sw, op, color)

# ========== 11. HORSESHOE (YENİ) ==========
def draw_horseshoe(sw, op):
    color = COLORS['horseshoe']
    x, y = random.uniform(0.3, 0.7), random.uniform(0.3, 0.7)
    pts = [(x*W, y*H)]
    for _ in range(200):
        x = (y + 1) % 1
        y = (x - 0.5 * y) % 1
        pts.append((x*W, y*H))
    return polyline_el(pts, sw, op, color)

# ========== 12. DELAUNAY (YENİ) ==========
def draw_delaunay(sw, op):
    color = COLORS['delaunay']
    result = ""
    points = []
    num_points = int(8 + sw)
    for _ in range(num_points):
        points.append((random.uniform(0, W), random.uniform(0, H)))
    # Basit üçgenleme (komşu noktaları birleştir)
    for i, (x1, y1) in enumerate(points):
        for j, (x2, y2) in enumerate(points):
            if i < j and abs(x1-x2) < W/3 and abs(y1-y2) < H/3:
                result += f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="{sw*0.6}" opacity="{op*0.4}"/>\n'
    return result

# ========== 13. RANDOM BRANCH (YENİ) ==========
def draw_random_branch(sw, op):
    color = COLORS['random_branch']
    result = ""
    start_x = random.uniform(W*0.2, W*0.8)
    start_y = H * 0.8
    result += f'<line x1="{start_x}" y1="{H}" x2="{start_x}" y2="{start_y}" stroke="{color}" stroke-width="{sw}" opacity="{op}"/>\n'
    
    branches = int(sw * 2)
    for _ in range(branches):
        angle = random.uniform(-math.pi/3, math.pi/3)
        length = random.uniform(50, 150)
        end_x = start_x + length * math.cos(angle)
        end_y = start_y - length * math.sin(angle)
        result += f'<line x1="{start_x}" y1="{start_y}" x2="{end_x}" y2="{end_y}" stroke="{color}" stroke-width="{sw*0.5}" opacity="{op*0.6}"/>\n'
    return result

# ========== 14. PARTICLE NETWORK (YENİ) ==========
def draw_particle_network(sw, op):
    color = COLORS['particle_network']
    result = ""
    points = []
    num_points = int(6 + sw)
    for _ in range(num_points):
        points.append((random.uniform(0, W), random.uniform(0, H)))
    for i, (x1, y1) in enumerate(points):
        distances = []
        for j, (x2, y2) in enumerate(points):
            if i != j:
                dist = math.hypot(x1-x2, y1-y2)
                distances.append((dist, j))
        distances.sort()
        for _, j in distances[:3]:
            x2, y2 = points[j]
            result += f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="{sw*0.5}" opacity="{op*0.3}"/>\n'
    return result

# ========== 15. REACTION DIFFUSION (YENİ) ==========
def draw_reaction_diffusion(sw, op):
    color = COLORS['reaction_diffusion']
    result = ""
    cells = []
    for _ in range(50):
        x = random.uniform(0, W)
        y = random.uniform(0, H)
        cells.append((x, y))
    for i in range(len(cells)):
        for j in range(i+1, len(cells)):
            dist = math.hypot(cells[i][0]-cells[j][0], cells[i][1]-cells[j][1])
            if dist < 100 and random.random() > 0.7:
                result += f'<line x1="{cells[i][0]}" y1="{cells[i][1]}" x2="{cells[j][0]}" y2="{cells[j][1]}" stroke="{color}" stroke-width="{sw*0.5}" opacity="{op*0.3}"/>\n'
    return result

# ================= TÜM DESENLERİN LİSTESİ (SADECE 15) =================
ALL_DRAWERS = [
    # BEĞENDİKLERİN (7)
    ("lemniscate", draw_lemniscate),
    ("breath_wave", draw_breath_wave),
    ("organic_flow", draw_organic_flow),
    ("spiral_out", draw_spiral_out),
    ("voronoi", draw_voronoi),
    ("fractal_tree", draw_fractal_tree),
    ("glassmorphism", draw_glassmorphism),
    
    # YENİLER (8)
    ("lissajous", draw_lissajous),
    ("noise_walk", draw_noise_walk),
    ("superformula", draw_superformula),
    ("horseshoe", draw_horseshoe),
    ("delaunay", draw_delaunay),
    ("random_branch", draw_random_branch),
    ("particle_network", draw_particle_network),
    ("reaction_diffusion", draw_reaction_diffusion),
]

# ================= ANA ÜRETİM =================
def generate_all_patterns():
    print("=" * 60)
    print("🎨 15 DESEN TÜRÜ (7 Beğenilen + 8 Yeni) × 3 SEVİYE × 2 TEKRAR")
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
