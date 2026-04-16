import os
import random
import math
import svgwrite

# ================= KONFIGURASYON =================
OUTPUT_DIR = "assets/patterns"
CANVAS_WIDTH = 3840
CANVAS_HEIGHT = 2160
LINE_COLOR = "#000000" # CSS'te opacity: 0.1 yaparak kullanın

# Klasör kontrolü
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

class PatternGenerator:
    def __init__(self, dwg):
        self.dwg = dwg

    def add_circuit_path(self, stroke_width):
        """90 derece dönen teknolojik devre hatları (TECH için ideal)"""
        x = random.randint(0, CANVAS_WIDTH)
        y = random.randint(0, CANVAS_HEIGHT)
        path_data = f"M {x} {y}"
        
        segments = random.randint(5, 15)
        for _ in range(segments):
            direction = random.choice(['h', 'v'])
            length = random.randint(150, 600)
            
            if direction == 'h':
                x = max(0, min(CANVAS_WIDTH, x + random.choice([-length, length])))
                path_data += f" H {x}"
            else:
                y = max(0, min(CANVAS_HEIGHT, y + random.choice([-length, length])))
                path_data += f" V {y}"
            
        self.dwg.add(self.dwg.path(d=path_data, stroke=LINE_COLOR, fill="none", 
                                   stroke_width=stroke_width, stroke_linecap="round",
                                   opacity=random.uniform(0.1, 0.4)))

    def add_concentric_waves(self, stroke_width):
        """Merkezden yayılan düzenli biyo-dalgalar (WELLNESS için ideal)"""
        cx, cy = CANVAS_WIDTH // 2, CANVAS_HEIGHT // 2
        # Rastgele bir merkez kayması ekle (asimetri için)
        cx += random.randint(-500, 500)
        cy += random.randint(-300, 300)

        for r in range(200, 2500, 200):
            path_data = ""
            for a in range(0, 365, 5):
                angle = math.radians(a)
                # Yumuşak bir dalgalanma efekti
                variation = math.sin(a * 0.05) * 30
                px = cx + (r + variation) * math.cos(angle)
                py = cy + (r + variation) * math.sin(angle)
                
                if a == 0: path_data += f"M {px} {py} "
                else: path_data += f"L {px} {py} "
            
            self.dwg.add(self.dwg.path(d=path_data, stroke=LINE_COLOR, fill="none", 
                                       stroke_width=stroke_width, opacity=0.15,
                                       stroke_dasharray="20,10"))

    def add_bento_grid(self):
        """Arka plan için modern rehber ızgarası (Tüm sayfalar için)"""
        grid_size = 120
        for x in range(0, CANVAS_WIDTH, grid_size):
            self.dwg.add(self.dwg.line((x, 0), (x, CANVAS_HEIGHT), stroke=LINE_COLOR, stroke_width=1, opacity=0.05))
        for y in range(0, CANVAS_HEIGHT, grid_size):
            self.dwg.add(self.dwg.line((0, y), (CANVAS_WIDTH, y), stroke=LINE_COLOR, stroke_width=1, opacity=0.05))

def generate_master_pattern(category, filename):
    filepath = os.path.join(OUTPUT_DIR, filename)
    dwg = svgwrite.Drawing(filepath, size=(CANVAS_WIDTH, CANVAS_HEIGHT))
    gen = PatternGenerator(dwg)

    # 1. Her zaman ince bir ızgara ekle (Modern görünümün temeli)
    gen.add_bento_grid()

    # 2. Kategoriye göre ana deseni çiz
    if category in ['tech', 'future-economy']:
        for _ in range(12): # 12 adet devre hattı
            gen.add_circuit_path(stroke_width=random.randint(2, 6))
    
    elif category in ['wellness', 'eco']:
        gen.add_concentric_waves(stroke_width=3)
        
    else: # Genel kullanım için karışık
        for _ in range(6): gen.add_circuit_path(2)
        gen.add_concentric_waves(1)

    dwg.save()
    print(f"   ✅ {category.upper()} tasarımı kaydedildi: {filename}")

# Üretim döngüsü
if __name__ == "__main__":
    print("🚀 GATEMIRROR PATTERN FACTORY 2026 BAŞLATILDI")
    categories = ['tech', 'wellness', 'eco', 'future-economy']
    
    for cat in categories:
        for i in range(1, 4): # Her kategori için 3 farklı varyasyon
            generate_master_pattern(cat, f"pattern_{cat}_{i}.svg")
    
    print("\n🫡 Hürgeneralim, tüm fütüristik desenler 'assets/patterns' klasörüne istiflendi!")
    
