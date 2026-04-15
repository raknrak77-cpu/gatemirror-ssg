import os

def check_templates():
    """Template dosyalarının varlığını ve gerekli elementleri kontrol eder"""
    templates_dir = "templates"
    errors = []
    
    if not os.path.exists(templates_dir):
        print(f"❌ {templates_dir} klasörü yok!")
        return False
    
    required_templates = ['home.html', 'list.html', 'single.html', 'hero.html']
    for template in required_templates:
        if not os.path.exists(os.path.join(templates_dir, template)):
            errors.append(f"{template}: Dosya yok")
    
    # hero.html kontrolü (sadece hero bileşeni, side menu vs. aranmaz)
    hero_path = os.path.join(templates_dir, 'hero.html')
    if os.path.exists(hero_path):
        with open(hero_path, 'r', encoding='utf-8') as f:
            content = f.read()
            # Sadece kritik hero elementlerini kontrol et
            if 'class="hero"' not in content:
                errors.append("hero.html: .hero sınıfı yok")
            if 'hero-title' not in content:
                errors.append("hero.html: hero-title sınıfı yok")
            if 'hero-description' not in content:
                errors.append("hero.html: hero-description sınıfı yok")
    else:
        errors.append("hero.html: Dosya yok")
    
    return errors

def check_tasks():
    """tasks.json kontrolü"""
    if not os.path.exists('tasks.json'):
        print("⚠️ tasks.json yok, oluşturulacak.")
        return True
    
    import json
    with open('tasks.json', 'r', encoding='utf-8') as f:
        tasks = json.load(f)
    
    pending = [t for t in tasks if t.get('status') == 'pending']
    if not pending:
        print("✅ Bekleyen görev yok.")
        return True
    
    print(f"📋 {len(pending)} bekleyen görev var.")
    return True

def starter():
    print("=" * 60)
    print("🔍 STARTER BOT - TEMPLATE VE TASK KONTROLÜ")
    print("=" * 60)
    
    print("\n📁 Template'ler kontrol ediliyor...")
    errors = check_templates()
    
    if errors:
        print("❌ TEMPLATE HATALARI:")
        for err in errors:
            print(f"   {err}")
        print("\n🚨 Workflow durduruluyor. Önce template'leri düzeltin.")
        exit(1)
    else:
        print("✅ Tüm template'ler geçerli.")
    
    print("\n📋 Task kontrolü...")
    if not check_tasks():
        print("❌ Task hatası!")
        exit(1)
    
    print("\n✅ STARTER BOT BAŞARILI - Workflow devam edebilir.")

if __name__ == "__main__":
    starter()    
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
