import os
import random
import math
import svgwrite

# ================= CONFIG =================
OUTPUT_DIR = "assets/gpt"
WIDTH = 3840
HEIGHT = 2160
COLOR = "#000000"

TOTAL_OUTPUT = 125   # 125 görsel

CATEGORIES = ["tech", "wellness", "eco", "future-economy", "elearning"]

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

# ================= ENGINE =================
class PatternEngine:
    def __init__(self, dwg, seed):
        self.dwg = dwg
        self.rand = random.Random(seed)

    def grid(self):
        for x in range(0, WIDTH, 120):
            self.dwg.add(self.dwg.line((x, 0), (x, HEIGHT),
                                      stroke=COLOR, stroke_width=1, opacity=0.05))
        for y in range(0, HEIGHT, 120):
            self.dwg.add(self.dwg.line((0, y), (WIDTH, y),
                                      stroke=COLOR, stroke_width=1, opacity=0.05))

    def circuit(self):
        for _ in range(self.rand.randint(6, 12)):
            x = self.rand.randint(0, WIDTH)
            y = self.rand.randint(0, HEIGHT)
            path = f"M {x} {y}"

            for _ in range(self.rand.randint(4, 10)):
                if self.rand.random() > 0.5:
                    x += self.rand.choice([-1, 1]) * self.rand.randint(100, 400)
                    x = max(0, min(WIDTH, x))
                    path += f" H {x}"
                else:
                    y += self.rand.choice([-1, 1]) * self.rand.randint(100, 400)
                    y = max(0, min(HEIGHT, y))
                    path += f" V {y}"

            self.dwg.add(self.dwg.path(d=path, stroke=COLOR, fill="none",
                                      stroke_width=2, opacity=0.2))

    def waves(self):
        cx, cy = WIDTH // 2, HEIGHT // 2
        for i in range(self.rand.randint(5, 8)):
            r = 200 + i * 180
            path = ""
            for a in range(0, 361, 5):
                angle = math.radians(a)
                offset = math.sin(a * 0.04) * (10 + i * 3)
                x = cx + (r + offset) * math.cos(angle)
                y = cy + (r + offset) * math.sin(angle)

                if a == 0:
                    path += f"M {x} {y}"
                else:
                    path += f"L {x} {y}"

            self.dwg.add(self.dwg.path(d=path, stroke=COLOR,
                                      fill="none", stroke_width=2, opacity=0.12))

    def organic(self):
        for _ in range(self.rand.randint(15, 30)):
            x = self.rand.randint(0, WIDTH)
            y = self.rand.randint(0, HEIGHT)
            r = self.rand.randint(40, 180)

            self.dwg.add(self.dwg.circle(center=(x, y), r=r,
                                        stroke=COLOR, fill="none",
                                        stroke_width=1, opacity=0.08))

    def flow(self):
        for _ in range(self.rand.randint(10, 18)):
            x, y = 0, self.rand.randint(0, HEIGHT)
            path = f"M {x} {y}"

            for _ in range(10):
                x += WIDTH // 10
                y += self.rand.randint(-120, 120)
                path += f"L {x} {y}"

            self.dwg.add(self.dwg.path(d=path, stroke=COLOR,
                                      fill="none", stroke_width=2, opacity=0.15))

# ================= GENERATOR =================
def generate_pattern(category, index):
    seed = f"{category}_{index}_{random.randint(0,999999)}"
    filename = f"{category}_{index+1:03d}.svg"
    filepath = os.path.join(OUTPUT_DIR, category, filename)
    
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    dwg = svgwrite.Drawing(filepath, size=(WIDTH, HEIGHT))
    engine = PatternEngine(dwg, seed)

    engine.grid()

    if category == "tech":
        engine.circuit()
    elif category == "wellness":
        engine.waves()
    elif category == "eco":
        engine.organic()
    elif category == "future-economy":
        engine.flow()
    elif category == "elearning":
        engine.flow()  # elearning için flow kullanalım

    dwg.save()
    print(f"   ✅ {category}/{filename}")

# ================= FACTORY =================
if __name__ == "__main__":
    print("=" * 60)
    print("🚀 PATTERN FACTORY - GPT VERSİYON")
    print(f"   📐 Canvas: {WIDTH}x{HEIGHT}")
    print(f"   🎨 Renk: {COLOR}")
    print(f"   📁 Klasör: {OUTPUT_DIR}/")
    print("=" * 60)
    
    for i in range(TOTAL_OUTPUT):
        category = CATEGORIES[i % len(CATEGORIES)]
        if i % 25 == 0:
            print(f"\n📁 {category.upper()} desenleri üretiliyor...")
        generate_pattern(category, i)
    
    print("\n" + "=" * 60)
    print(f"✅ {TOTAL_OUTPUT} adet pattern üretildi.")
    print(f"📁 Klasör: {OUTPUT_DIR}/")
    print("=" * 60)
