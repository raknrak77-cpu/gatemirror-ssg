import os
import sys
import json
import re

def test_templates():
    """Tüm template'leri kontrol eder, hata varsa workflow durur"""
    templates_dir = "templates"
    errors = []
    
    # Atlanacak dosyalar (içerik parçaları, tam HTML değil)
    skip_files = ['manifesto.html', 'hero.html']
    
    if not os.path.exists(templates_dir):
        print("❌ templates/ klasörü bulunamadı!")
        sys.exit(1)
    
    for file in os.listdir(templates_dir):
        if not file.endswith('.html'):
            continue
        
        # Atlanacak dosyaları kontrol et
        if file in skip_files:
            print(f"   ⏭️ {file} atlandı (içerik dosyası)")
            continue
        
        path = os.path.join(templates_dir, file)
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # hero.html özel kontroller (artık kullanılmıyor ama kalsın)
        if file == 'hero.html':
            if 'class="hero"' not in content:
                errors.append(f"{file}: .hero sınıfı yok")
            if 'hero-title' not in content:
                errors.append(f"{file}: hero-title sınıfı yok")
            if 'hero-description' not in content:
                errors.append(f"{file}: hero-description sınıfı yok")
            continue
        
        # Diğer template'ler (home, list, single, all-articles)
        # 1. Lang değişkeni kontrolü
        if '/en/' in content and '{{ lang }}' not in content:
            errors.append(f"{file}: /en/ var ama {{ lang }} yok (dil yönlendirme hatası)")
        
        # 2. Side menu link kontrolü
        if 'href="{{ lang }}"' in content or 'href="{{ lang }}/"' in content:
            errors.append(f"{file}: href başında / eksik (href=\"/{{ lang }}/\" olmalı)")
        
        # 3. Dark mode toggle kontrolü (gömülü JS'de var)
        if 'darkModeToggle' not in content and 'toggle-switch' not in content:
            errors.append(f"{file}: Dark mode toggle butonu yok")
        
        # 4. CSS linki kontrolü - style.css ARANMAZ (gömülü CSS var)
        # Sadece font-awesome var mı kontrol et
        if 'font-awesome' not in content and 'fa-bars' not in content:
            errors.append(f"{file}: Font Awesome linki yok")
        
        # 5. Hero include kontrolü
        if '{% include "hero.html"' in content:
            errors.append(f"{file}: include hero.html kullanılıyor, hero.html safe ile değiştirin")
        
        # 6. Gömülü CSS kontrolü (style etiketi var mı?)
        if '<style>' not in content:
            errors.append(f"{file}: Gömülü CSS (<style> etiketi) bulunamadı")
    
    return errors

def test_css():
    """CSS dosyasını kontrol et - ARTIK ZORUNLU DEĞİL (gömülü CSS var)"""
    css_path = "templates/css/style.css"
    warnings = []
    
    if not os.path.exists(css_path):
        warnings.append("style.css dosyası bulunamadı (gömülü CSS kullanılıyor, bu normal)")
        return [], warnings
    
    with open(css_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    errors = []
    required_classes = [
        '.hero', '.hero-title', '.hero-description',
        '.side-menu', '.nav-links', '.dark-mode-toggle', '.toggle-switch',
        '.article-grid', '.article-card', '.footer-content'
    ]
    
    for cls in required_classes:
        if cls not in content:
            errors.append(f"CSS: {cls} sınıfı bulunamadı")
    
    if 'body.dark' not in content:
        errors.append("CSS: Dark mode stilleri (body.dark) bulunamadı")
    
    if '@media (max-width: 768px)' not in content:
        errors.append("CSS: Responsive stiller (@media) bulunamadı")
    
    if ':root' not in content:
        errors.append("CSS: :root değişkenleri bulunamadı")
    
    return errors, warnings

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
        
        # CSS linki kontrolü - style.css ARANMAZ (gömülü CSS var)
        if 'font-awesome' not in content:
            errors.append(f"{page}: Font Awesome linki yok")
        
        # Gömülü CSS kontrolü
        if '<style>' not in content:
            errors.append(f"{page}: Gömülü CSS (<style> etiketi) bulunamadı")
        
        # Hero kontrolü
        if 'class="hero"' not in content:
            errors.append(f"{page}: Hero bileşeni yok")
        
        # Side menu kontrolü
        if 'side-menu' not in content:
            errors.append(f"{page}: Side menu yok")
        
        # Dark mode kontrolü (gömülü JS'de var)
        if 'darkModeToggle' not in content and 'toggle-switch' not in content:
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
        
        if 'pages' not in hero_data:
            errors.append("hero.json: 'pages' alanı yok")
        
        if 'home' not in hero_data.get('pages', {}):
            errors.append("hero.json: 'pages.home' alanı yok")
        
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
    print("   ✅ Gömülü CSS sistemi için güncellendi")
    print("   ✅ İçerik dosyaları (manifesto.html, hero.html) atlanıyor")
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
    
    # 2. CSS kontrolü (artık zorunlu değil)
    print("\n🎨 CSS dosyası kontrol ediliyor...")
    css_errors, css_warnings = test_css()
    if css_errors:
        all_errors.extend(css_errors)
    if css_warnings:
        all_warnings.extend(css_warnings)
    if not css_errors and not css_warnings:
        print("   ✅ style.css doğru görünüyor.")
    elif css_warnings and not css_errors:
        print(f"   ⚠️ {css_warnings[0]}")
    
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
    
    # 5. Explore klasörü uyarıları
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
