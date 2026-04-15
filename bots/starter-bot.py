import os
import sys
import json
import re

def test_templates():
    """Tüm template'leri kontrol eder, hata varsa workflow durur"""
    templates_dir = "templates"
    errors = []
    
    if not os.path.exists(templates_dir):
        print("❌ templates/ klasörü bulunamadı!")
        sys.exit(1)
    
    for file in os.listdir(templates_dir):
        if not file.endswith('.html'):
            continue
        
        path = os.path.join(templates_dir, file)
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # hero.html özel kontroller (farklı kurallar)
        if file == 'hero.html':
            # Hero bileşeninde sadece kritik elementleri kontrol et
            if 'class="hero"' not in content:
                errors.append(f"{file}: .hero sınıfı yok")
            if 'hero-title' not in content:
                errors.append(f"{file}: hero-title sınıfı yok")
            if 'hero-description' not in content:
                errors.append(f"{file}: hero-description sınıfı yok")
            # hero.html'de dark mode butonu ARANMAZ (template'lerde olmalı)
            continue
        
        # Diğer template'ler (home, list, single) için tam kontroller
        # 1. Lang değişkeni kontrolü
        if '/en/' in content and '{{ lang }}' not in content:
            errors.append(f"{file}: /en/ var ama {{ lang }} yok (dil yönlendirme hatası)")
        
        # 2. Side menu link kontrolü
        if 'href="{{ lang }}"' in content or 'href="{{ lang }}/"' in content:
            errors.append(f"{file}: href başında / eksik (href=\"/{{ lang }}/\" olmalı)")
        
        # 3. Dark mode toggle kontrolü
        if 'darkModeToggle' not in content:
            errors.append(f"{file}: Dark mode butonu yok")
        
        # 4. Toggle switch kontrolü
        if 'toggle-switch' not in content:
            errors.append(f"{file}: toggle-switch sınıfı yok")
        
        # 5. CSS linki kontrolü (style.css var mı?)
        if 'style.css' not in content:
            errors.append(f"{file}: style.css linki yok (master CSS dosyası eklenmeli)")
        
        # 6. Hero include kontrolü (artık include değil, variable kullanılıyor)
        if '{% include "hero.html"' in content:
            errors.append(f"{file}: include hero.html kullanılıyor, hero.html safe ile değiştirin")
    
    return errors

def test_css():
    """CSS dosyasını kontrol eder"""
    css_path = "templates/css/style.css"
    errors = []
    
    if not os.path.exists(css_path):
        errors.append(f"CSS dosyası bulunamadı: {css_path}")
        return errors
    
    with open(css_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Kritik CSS sınıflarının varlığını kontrol et
    required_classes = [
        '.hero', '.hero-title', '.hero-description',
        '.side-menu', '.nav-links', '.dark-mode-toggle', '.toggle-switch',
        '.article-grid', '.article-card', '.footer-content'
    ]
    
    for cls in required_classes:
        if cls not in content:
            errors.append(f"CSS: {cls} sınıfı bulunamadı")
    
    # Dark mode kontrolü
    if 'body.dark' not in content:
        errors.append("CSS: Dark mode stilleri (body.dark) bulunamadı")
    
    # Responsive kontrolü
    if '@media (max-width: 768px)' not in content:
        errors.append("CSS: Responsive stiller (@media) bulunamadı")
    
    # Değişken kontrolü (CSS variables)
    if ':root' not in content:
        errors.append("CSS: :root değişkenleri bulunamadı")
    
    return errors

def test_static_pages():
    """Statik sayfaları (about, contact, privacy) kontrol eder"""
    static_pages = ['about-us.html', 'contact.html', 'privacy-policy.html']
    errors = []
    
    for page in static_pages:
        path = os.path.join(".", page)
        if not os.path.exists(path):
            errors.append(f"Statik sayfa bulunamadı: {page}")
            continue
        
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # CSS linki kontrolü
        if 'style.css' not in content:
            errors.append(f"{page}: style.css linki yok")
        
        # Hero kontrolü
        if 'class="hero"' not in content:
            errors.append(f"{page}: Hero bileşeni yok")
        
        # Side menu kontrolü
        if 'side-menu' not in content:
            errors.append(f"{page}: Side menu yok")
        
        # Dark mode kontrolü
        if 'darkModeToggle' not in content:
            errors.append(f"{page}: Dark mode butonu yok")
    
    return errors

def test_hero_json():
    """hero.json dosyasını kontrol eder"""
    hero_path = "templates/hero.json"
    errors = []
    
    if not os.path.exists(hero_path):
        errors.append(f"hero.json bulunamadı: {hero_path}")
        return errors
    
    try:
        with open(hero_path, 'r', encoding='utf-8') as f:
            hero_data = json.load(f)
        
        # Gerekli alanların varlığını kontrol et
        if 'pages' not in hero_data:
            errors.append("hero.json: 'pages' alanı yok")
        
        if 'home' not in hero_data.get('pages', {}):
            errors.append("hero.json: 'pages.home' alanı yok")
        
        # Her dil için kontrol
        for lang in ['en', 'es', 'de', 'fr']:
            if lang not in hero_data.get('pages', {}).get('home', {}):
                errors.append(f"hero.json: pages.home.{lang} alanı yok")
        
    except json.JSONDecodeError as e:
        errors.append(f"hero.json geçersiz JSON: {e}")
    except Exception as e:
        errors.append(f"hero.json okunamadı: {e}")
    
    return errors

def test_explore_folder():
    """Explore klasörü yapısını kontrol eder (opsiyonel - uyarı olarak)"""
    warnings = []
    
    explore_dirs = [
        "explore/all-articles",
        "explore/categories",
        "explore/category-archive"
    ]
    
    for d in explore_dirs:
        if not os.path.exists(d):
            warnings.append(f"{d}/ klasörü yok (Librarian çalışınca oluşacak)")
    
    return warnings

def check_pending_tasks():
    """tasks.json'da pending görev var mı kontrol eder"""
    if not os.path.exists("tasks.json"):
        print("⚠️ tasks.json bulunamadı, yeni task eklenmemiş olabilir.")
        return 0
    
    with open("tasks.json", "r", encoding='utf-8') as f:
        tasks = json.load(f)
    
    pending = [t for t in tasks if t.get("status") == "pending"]
    
    if not pending:
        print("❌ BEKLEYEN GÖREV YOK! Önce 'Add New Task' workflow'u ile task ekleyin.")
        return 0
    
    print(f"✅ {len(pending)} pending görev bulundu.")
    return len(pending)

def starter():
    print("\n" + "=" * 60)
    print("🔍 STARTER BOT - TEMPLATE, CSS, STATİK SAYFA VE TASK KONTROLÜ")
    print("=" * 60 + "\n")
    
    all_errors = []
    all_warnings = []
    
    # 1. Template kontrolü
    print("📁 Template'ler kontrol ediliyor...")
    template_errors = test_templates()
    if template_errors:
        all_errors.extend(template_errors)
    else:
        print("   ✅ Tüm template'ler doğru görünüyor.")
    
    # 2. CSS kontrolü
    print("\n🎨 CSS dosyası kontrol ediliyor...")
    css_errors = test_css()
    if css_errors:
        all_errors.extend(css_errors)
    else:
        print("   ✅ style.css doğru görünüyor.")
    
    # 3. Statik sayfa kontrolü
    print("\n📄 Statik sayfalar kontrol ediliyor...")
    static_errors = test_static_pages()
    if static_errors:
        all_errors.extend(static_errors)
    else:
        print("   ✅ Statik sayfalar doğru görünüyor.")
    
    # 4. Hero.json kontrolü
    print("\n🎯 hero.json kontrol ediliyor...")
    hero_errors = test_hero_json()
    if hero_errors:
        all_errors.extend(hero_errors)
    else:
        print("   ✅ hero.json doğru görünüyor.")
    
    # 5. Explore klasörü uyarıları (opsiyonel)
    print("\n📂 Explore klasörü kontrol ediliyor...")
    explore_warnings = test_explore_folder()
    if explore_warnings:
        all_warnings.extend(explore_warnings)
    else:
        print("   ✅ Explore klasör yapısı tamam.")
    
    # 6. Pending task kontrolü
    print("\n📋 Task'ler kontrol ediliyor...")
    pending_count = check_pending_tasks()
    
    # Hata varsa göster ve dur
    if all_errors:
        print("\n" + "=" * 60)
        print("❌ HATALAR TESPİT EDİLDİ:")
        print("=" * 60)
        for err in all_errors:
            print(f"   {err}")
        
        if all_warnings:
            print("\n⚠️ UYARILAR:")
            for warn in all_warnings:
                print(f"   {warn}")
        
        print("\n🚨 Workflow durduruluyor. Önce hataları düzeltin.")
        sys.exit(1)
    
    # Uyarıları göster (workflow devam eder)
    if all_warnings:
        print("\n⚠️ UYARILAR (workflow devam ediyor):")
        for warn in all_warnings:
            print(f"   {warn}")
    
    # Pending task yoksa dur
    if pending_count == 0:
        print("\n🚨 Workflow durduruluyor. Önce 'Add New Task' ile task ekleyin.")
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("✅ TÜM KONTROLLER GEÇTİ. CREATOR BAŞLAYABİLİR.")
    print("=" * 60 + "\n")

if __name__ == "__main__":
    starter()
