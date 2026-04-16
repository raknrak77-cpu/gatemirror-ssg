import os
import random
import math
import svgwrite

# ================= KONFIGURASYON =================
OUTPUT_DIR = "assets/patterns"
CANVAS_WIDTH = 3840
CANVAS_HEIGHT = 2160

# Renk: Beyaz (dark mod'da görünür)
LINE_COLOR = "#ffffff"

# Seviye konfigürasyonları
LEVELS = {
    'basic': {'count': 5, 'lines': 6, 'stroke_widths': [1, 2, 3, 4, 5, 6]},
    'medium': {'count': 5, 'lines': 25, 'stroke_width_min': 1, 'stroke_width_max': 8},
    'complex': {'count': 5, 'lines': 55, 'stroke_width_min': 1, 'stroke_width_max': 12},
    'very_complex': {'count': 5, 'lines': 90, 'stroke_width_min': 1, 'stroke_width_max': 16},
    'extreme': {'count': 5, 'lines': 130, 'stroke_width_min': 1, 'stroke_width_max': 20}
}

def sine_wave_path(start_x, start_y, amplitude, wavelength, cycles, direction):
    """Sinüs dalgası yolu oluşturur"""
    points = []
    step = 20  # Her 20px'de bir nokta
    
    if direction == 'horizontal':
        for i in range(0, int(CANVAS_WIDTH * 1.5), step):
            x = start_x + i
            y = start_y + amplitude * math.sin(2 * math.pi * i / wavelength)
            points.append((x, y))
    elif direction == 'vertical':
        for i in range(0, int(CANVAS_HEIGHT * 1.5), step):
            y = start_y + i
            x = start_x + amplitude * math.sin(2 * math.pi * i / wavelength)
            points.append((x, y))
    else:  # diagonal
        for i in range(0, int(max(CANVAS_WIDTH, CANVAS_HEIGHT) * 1.5), step):
            x = start_x + i * 0.7
            y = start_y + i * 0.7 + amplitude * math.sin(2 * math.pi * i / wavelength)
            points.append((x, y))
    
    return points

def bezier_wave_path(start_x, start_y, end_x, end_y, amplitude, cycles):
    """Bezier eğrisi ile dalga oluşturur"""
    # Kontrol noktaları
    mid_x = (start_x + end_x) / 2
    mid_y = (start_y + end_y) / 2
    
    # Dalga etkisi için kontrol noktalarını kaydır
    ctrl1_x = start_x + (end_x - start_x) * 0.25
    ctrl1_y = start_y + amplitude * math.sin(cycles * math.pi * 0.25)
    ctrl2_x = end_x - (end_x - start_x) * 0.25
    ctrl2_y = end_y + amplitude * math.sin(cycles * math.pi * 0.75)
    
    return f"M {start_x},{start_y} C {ctrl1_x},{ctrl1_y} {ctrl2_x},{ctrl2_y} {end_x},{end_y}"

def generate_path(dwg, line_type, stroke_width):
    """Rastgele bir dalgalı çizgi oluşturur"""
    
    if line_type == 'sine_horizontal':
        start_x = random.randint(-CANVAS_WIDTH//4, CANVAS_WIDTH//4)
        start_y = random.randint(0, CANVAS_HEIGHT)
        amplitude = random.randint(30, 200)
        wavelength = random.randint(200, 800)
        points = sine_wave_path(start_x, start_y, amplitude, wavelength, 3, 'horizontal')
        polyline = dwg.polyline(points, stroke=LINE_COLOR, stroke_width=stroke_width, fill='none')
        dwg.add(polyline)
        
    elif line_type == 'sine_vertical':
        start_x = random.randint(0, CANVAS_WIDTH)
        start_y = random.randint(-CANVAS_HEIGHT//4, CANVAS_HEIGHT//4)
        amplitude = random.randint(30, 200)
        wavelength = random.randint(200, 800)
        points = sine_wave_path(start_x, start_y, amplitude, wavelength, 3, 'vertical')
        polyline = dwg.polyline(points, stroke=LINE_COLOR, stroke_width=stroke_width, fill='none')
        dwg.add(polyline)
        
    elif line_type == 'sine_diagonal':
        start_x = random.randint(-CANVAS_WIDTH//4, CANVAS_WIDTH//4)
        start_y = random.randint(-CANVAS_HEIGHT//4, CANVAS_HEIGHT//4)
        amplitude = random.randint(30, 200)
        wavelength = random.randint(200, 800)
        points = sine_wave_path(start_x, start_y, amplitude, wavelength, 3, 'diagonal')
        polyline = dwg.polyline(points, stroke=LINE_COLOR, stroke_width=stroke_width, fill='none')
        dwg.add(polyline)
        
    elif line_type == 'bezier':
        start_x = random.randint(-CANVAS_WIDTH//4, CANVAS_WIDTH + CANVAS_WIDTH//4)
        start_y = random.randint(-CANVAS_HEIGHT//4, CANVAS_HEIGHT + CANVAS_HEIGHT//4)
        end_x = start_x + random.randint(CANVAS_WIDTH//2, CANVAS_WIDTH)
        end_y = start_y + random.randint(-CANVAS_HEIGHT//2, CANVAS_HEIGHT//2)
        amplitude = random.randint(50, 300)
        cycles = random.uniform(1, 5)
        path_data = bezier_wave_path(start_x, start_y, end_x, end_y, amplitude, cycles)
        dwg.add(dwg.path(path_data, stroke=LINE_COLOR, stroke_width=stroke_width, fill='none'))
        
    elif line_type == 'nested':
        # İç içe geçen paralel çizgiler
        base_x = random.randint(0, CANVAS_WIDTH)
        base_y = random.randint(0, CANVAS_HEIGHT)
        for offset in range(-3, 4):
            offset_width = max(1, stroke_width - abs(offset) * 2)
            if offset_width < 1:
                continue
            start_x = base_x + offset * 15
            start_y = base_y + offset * 15
            end_x = base_x + CANVAS_WIDTH//2 + offset * 15
            end_y = base_y + CANVAS_HEIGHT//2 + offset * 15
            amplitude = random.randint(30, 150)
            cycles = random.uniform(1, 3)
            path_data = bezier_wave_path(start_x, start_y, end_x, end_y, amplitude, cycles)
            dwg.add(dwg.path(path_data, stroke=LINE_COLOR, stroke_width=offset_width, fill='none'))
            
    elif line_type == 'network':
        # Ağ yapısı (kesişen çizgiler)
        points = []
        for i in range(6):
            x = random.randint(0, CANVAS_WIDTH)
            y = random.randint(0, CANVAS_HEIGHT)
            points.append((x, y))
        polyline = dwg.polyline(points, stroke=LINE_COLOR, stroke_width=stroke_width, fill='none')
        dwg.add(polyline)

def generate_pattern(category, level_name, level_config, index):
    """Bir SVG pattern üretir"""
    filename = f"{category}_{level_name}_{index+1:02d}.svg"
    filepath = os.path.join(OUTPUT_DIR, category, filename)
    
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    
    # SVG oluştur (arka plan YOK - şeffaf)
    dwg = svgwrite.Drawing(filepath, size=(CANVAS_WIDTH, CANVAS_HEIGHT))
    
    line_types = ['sine_horizontal', 'sine_vertical', 'sine_diagonal', 'bezier', 'nested', 'network']
    num_lines = level_config['lines']
    
    for i in range(num_lines):
        # Rastgele çizgi tipi
        line_type = random.choice(line_types)
        
        # Rastgele kalınlık
        if 'stroke_widths' in level_config:
            stroke_width = random.choice(level_config['stroke_widths'])
        else:
            stroke_width = random.uniform(level_config['stroke_width_min'], level_config['stroke_width_max'])
            stroke_width = round(stroke_width, 1)
        
        generate_path(dwg, line_type, stroke_width)
    
    dwg.save()
    print(f"   ✅ {category}/{filename} ({num_lines} lines)")

def pattern_factory():
    """Ana üretim fonksiyonu"""
    print("=" * 60)
    print("🎨 PATTERN FACTORY - Dalgalı Çizgiler (svgwrite)")
    print(f"   📐 Canvas: {CANVAS_WIDTH}x{CANVAS_HEIGHT}")
    print(f"   🎨 Renk: {LINE_COLOR}")
    print("   📊 Seviyeler: basic(6) → medium(25) → complex(55) → very_complex(90) → extreme(130)")
    print("=" * 60)
    
    categories = ['tech', 'wellness', 'eco', 'future-economy', 'elearning']
    level_names = ['basic', 'medium', 'complex', 'very_complex', 'extreme']
    total_count = 0
    
    for category in categories:
        print(f"\n📁 {category.upper()} desenleri üretiliyor...")
        
        for level_name in level_names:
            level_config = LEVELS[level_name]
            
            for i in range(level_config['count']):
                print(f"   🎨 {level_name} desen {i+1}/{level_config['count']}...")
                generate_pattern(category, level_name, level_config, i)
                total_count += 1
    
    print("\n" + "=" * 60)
    print("🏁 PATTERN FACTORY TAMAMLANDI!")
    print(f"   ✅ Toplam {total_count} desen üretildi")
    print(f"   📁 Klasör: {OUTPUT_DIR}/")
    print("=" * 60)

if __name__ == "__main__":
    pattern_factory()
