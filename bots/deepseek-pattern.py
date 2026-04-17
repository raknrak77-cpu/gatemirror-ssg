import os
import random
import math

# ================= KONFIGÜRASYON =================
OUTPUT_DIR = "assets/wellness-variations"  # 🔥 SADECE BURASI DEĞİŞTİ
W = 3840
H = 2160

# ================= WELLNESS ÜRETİM SAYILARI =================
LEVELS = {
    'basic':       6,
    'medium':      15,
    'extra':       20,
}
COUNT_PER_LEVEL = 6

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

# ================= WELLNESS ÇİZGİ ÜRETECLERİ =================

def organic_flow(sw, op):
    """Organik akış - wellness"""
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
    """Nefes ritmi - wellness"""
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

def spiral_out(sw, op):
    """Dışa açılan spiral - wellness"""
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

def gentle_arc(sw, op):
    """Yumuşak yay - wellness"""
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

def sine_diagonal(sw, op):
    """Diyagonal sinüs - wellness"""
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

# ================= ÜRETEC MAP =================
GENERATORS = [
    organic_flow,
    breath_wave,
    spiral_out,
    gentle_arc,
    sine_diagonal,
]

# ================= ANA ÜRETİM =================
def generate_pattern(level_name, num_lines, index):
    filename = f"wellness_{level_name}_{index+1:02d}.svg"
    filepath = os.path.join(OUTPUT_DIR, filename)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    svg = svg_open(filepath)

    for _ in range(num_lines):
        gen = random.choice(GENERATORS)
        sw = random.uniform(0.5, 6)
        op = random.uniform(0.1, 0.7)
        svg += gen(sw, op)

    svg += svg_close()

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(svg)

    print(f"   ✅ {filename} ({num_lines} lines)")

def pattern_factory():
    print("=" * 60)
    print("🌿 WELLNESS PATTERN FACTORY")
    print(f"   📐 Canvas: {W}x{H}")
    print(f"   🎨 Renk: currentColor (CSS ile kontrol)")
    print(f"   📁 Çıktı: {OUTPUT_DIR}/")
    print(f"   🧬 Desenler: organic_flow, breath_wave, spiral_out, gentle_arc, sine_diagonal")
    print("=" * 60)

    total = 0
    for level_name, num_lines in LEVELS.items():
        print(f"\n📊 Seviye: {level_name.upper()} ({num_lines} çizgi)")
        for i in range(COUNT_PER_LEVEL):
            generate_pattern(level_name, num_lines, i)
            total += 1

    print("\n" + "=" * 60)
    print(f"🏁 TAMAMLANDI! {total} desen üretildi")
    print(f"   📁 {OUTPUT_DIR}/")
    print("\n💡 CSS ile renk değiştirmek için:")
    print("   .wellness-bg svg { color: #7a4a6a; }")
    print("=" * 60)

if __name__ == "__main__":
    pattern_factory()
