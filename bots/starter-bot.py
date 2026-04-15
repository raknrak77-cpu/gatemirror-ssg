import os
import sys
import json

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
    
    return errors

def check_pending_tasks():
    """tasks.json'da pending görev var mı kontrol eder"""
    if not os.path.exists("tasks.json"):
        print("⚠️ tasks.json bulunamadı, yeni task eklenmemiş olabilir.")
        return 0
    
    with open("tasks.json", "r", encoding="utf-8") as f:
        tasks = json.load(f)
    
    pending = [t for t in tasks if t.get("status") == "pending"]
    
    if not pending:
        print("❌ BEKLEYEN GÖREV YOK! Önce 'Add New Task' workflow'u ile task ekleyin.")
        return 0
    
    print(f"✅ {len(pending)} pending görev bulundu.")
    return len(pending)

def starter():
    print("\n" + "="*50)
    print("🔍 STARTER BOT - TEMPLATE VE TASK KONTROLÜ")
    print("="*50 + "\n")
    
    # 1. Template kontrolü
    print("📁 Template'ler kontrol ediliyor...")
    template_errors = test_templates()
    
    if template_errors:
        print("❌ TEMPLATE HATALARI:")
        for err in template_errors:
            print(f"   {err}")
        print("\n🚨 Workflow durduruluyor. Önce template'leri düzeltin.")
        sys.exit(1)
    else:
        print("✅ Tüm template'ler doğru görünüyor.\n")
    
    # 2. Pending task kontrolü
    print("📋 Task'ler kontrol ediliyor...")
    pending_count = check_pending_tasks()
    
    if pending_count == 0:
        print("\n🚨 Workflow durduruluyor. Önce 'Add New Task' ile task ekleyin.")
        sys.exit(1)
    
    print("\n" + "="*50)
    print("✅ TÜM KONTROLLER GEÇTİ. CREATOR BAŞLAYABİLİR.")
    print("="*50 + "\n")

if __name__ == "__main__":
    starter()
