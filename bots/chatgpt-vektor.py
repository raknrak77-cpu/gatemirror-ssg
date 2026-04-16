import os
import random
import math
import svgwrite
import traceback

OUTPUT_DIR = "assets/gpt"
WIDTH = 1920
HEIGHT = 1080
COLOR = "#000000"
TOTAL_OUTPUT = 125

CATEGORIES = ["tech", "wellness", "eco", "future-economy", "elearning"]

# Ana klasörü oluştur
os.makedirs(OUTPUT_DIR, exist_ok=True)
print(f"📁 Ana klasör: {os.path.abspath(OUTPUT_DIR)}")

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
                y = max(0, min(HEIGHT, y))
                path += f"L {x} {y}"
            self.dwg.add(self.dwg.path(d=path, stroke=COLOR, fill="none", stroke_width=1.5, opacity=0.25))

def generate_pattern(category, index):
    try:
        # Klasör ve dosya yolu
        category_dir = os.path.join(OUTPUT_DIR, category)
        os.makedirs(category_dir, exist_ok=True)
        
        filename = f"{category}_{index+1:03d}.svg"
        filepath = os.path.join(category_dir, filename)
        
        print(f"   📝 Yazılıyor: {filepath}")
        
        # SVG oluştur
        dwg = svgwrite.Drawing(filepath, size=(WIDTH, HEIGHT))
        engine = PatternEngine(dwg, f"{category}_{index}_{random.randint(0,999999)}")
        
        # Kategoriye göre desen seç
        if category == "tech":
            engine.circuit()
        elif category == "wellness":
            engine.waves()
        elif category == "eco":
            engine.organic()
        else:
            engine.flow()
        
        # Kaydet
        dwg.save()
        
        # Dosyanın gerçekten oluştuğunu kontrol et
        if os.path.exists(filepath):
            size = os.path.getsize(filepath)
            print(f"   ✅ {category}/{filename} ({size} bytes)")
            return True
        else:
            print(f"   ❌ {category}/{filename} kaydedilemedi!")
            return False
            
    except Exception as e:
        print(f"   ❌ HATA: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 GPT PATTERN FACTORY (HATA AYIKLAMALI)")
    print(f"   📁 Klasör: {os.path.abspath(OUTPUT_DIR)}")
    print("=" * 60)
    
    success_count = 0
    
    for i in range(TOTAL_OUTPUT):
        category = CATEGORIES[i % len(CATEGORIES)]
        if i % 5 == 0:
            print(f"\n📁 {category.upper()} desenleri üretiliyor...")
        
        if generate_pattern(category, i):
            success_count += 1
    
    print("\n" + "=" * 60)
    print(f"🏁 TAMAMLANDI! {success_count}/{TOTAL_OUTPUT} desen üretildi")
    
    # Listele
    if success_count > 0:
        print("\n📂 OLUŞAN DOSYALAR:")
        for root, dirs, files in os.walk(OUTPUT_DIR):
            for file in files:
                if file.endswith('.svg'):
                    print(f"   📄 {os.path.join(root, file)}")
    else:
        print("❌ HİÇ DOSYA OLUŞMADI! Kontrol edin.")
    print("=" * 60)
