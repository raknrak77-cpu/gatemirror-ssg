import os
import random
import math
import svgwrite

OUTPUT_DIR = "assets/gpt"
WIDTH = 1920   # Test için küçülttüm
HEIGHT = 1080
COLOR = "#000000"
TOTAL_OUTPUT = 150  # Test için 10 adet

CATEGORIES = ["tech", "wellness", "eco", "future-economy", "elearning"]

os.makedirs(OUTPUT_DIR, exist_ok=True)

class PatternEngine:
    def __init__(self, dwg, seed):
        self.dwg = dwg
        self.rand = random.Random(seed)

    def circuit(self):
        for _ in range(self.rand.randint(5, 10)):
            x = self.rand.randint(0, WIDTH)
            y = self.rand.randint(0, HEIGHT)
            path = f"M {x} {y}"
            for _ in range(self.rand.randint(3, 8)):
                if self.rand.random() > 0.5:
                    x += self.rand.choice([-1, 1]) * self.rand.randint(50, 200)
                    x = max(0, min(WIDTH, x))
                    path += f" H {x}"
                else:
                    y += self.rand.choice([-1, 1]) * self.rand.randint(50, 200)
                    y = max(0, min(HEIGHT, y))
                    path += f" V {y}"
            self.dwg.add(self.dwg.path(d=path, stroke=COLOR, fill="none", stroke_width=1.5, opacity=0.3))

    def waves(self):
        cx, cy = WIDTH // 2, HEIGHT // 2
        for i in range(self.rand.randint(3, 6)):
            r = 100 + i * 100
            path = ""
            for a in range(0, 361, 10):
                angle = math.radians(a)
                offset = math.sin(a * 0.05) * (5 + i * 2)
                x = cx + (r + offset) * math.cos(angle)
                y = cy + (r + offset) * math.sin(angle)
                if a == 0:
                    path += f"M {x} {y}"
                else:
                    path += f"L {x} {y}"
            self.dwg.add(self.dwg.path(d=path, stroke=COLOR, fill="none", stroke_width=1.5, opacity=0.2))

    def organic(self):
        for _ in range(self.rand.randint(10, 20)):
            x = self.rand.randint(0, WIDTH)
            y = self.rand.randint(0, HEIGHT)
            r = self.rand.randint(20, 100)
            self.dwg.add(self.dwg.circle(center=(x, y), r=r, stroke=COLOR, fill="none", stroke_width=1, opacity=0.15))

    def flow(self):
        for _ in range(self.rand.randint(5, 10)):
            x, y = 0, self.rand.randint(0, HEIGHT)
            path = f"M {x} {y}"
            for _ in range(6):
                x += WIDTH // 6
                y += self.rand.randint(-60, 60)
                path += f"L {x} {y}"
            self.dwg.add(self.dwg.path(d=path, stroke=COLOR, fill="none", stroke_width=1.5, opacity=0.25))

def generate_pattern(category, index):
    filename = f"{category}_{index+1:03d}.svg"
    filepath = os.path.join(OUTPUT_DIR, category, filename)
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    dwg = svgwrite.Drawing(filepath, size=(WIDTH, HEIGHT))
    engine = PatternEngine(dwg, f"{category}_{index}")

    if category == "tech":
        engine.circuit()
    elif category == "wellness":
        engine.waves()
    elif category == "eco":
        engine.organic()
    elif category == "future-economy":
        engine.flow()
    elif category == "elearning":
        engine.flow()

    dwg.save()
    print(f"✅ {category}/{filename}")

if __name__ == "__main__":
    print(f"🚀 GPT PATTERN FACTORY - {TOTAL_OUTPUT} desen")
    for i in range(TOTAL_OUTPUT):
        category = CATEGORIES[i % len(CATEGORIES)]
        generate_pattern(category, i)
    print("🏁 TAMAM")
