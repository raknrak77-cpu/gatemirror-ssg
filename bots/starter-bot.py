import os
import sys
import json

def test_templates():
    """TÃ¼m template'leri kontrol eder, hata varsa workflow durur"""
    templates_dir = "templates"
    errors = []
    
    if not os.path.exists(templates_dir):
        print("âŒ templates/ klasÃ¶rÃ¼ bulunamadÄ±!")
        sys.exit(1)
    
    for file in os.listdir(templates_dir):
        if not file.endswith('.html'):
            continue
        
        path = os.path.join(templates_dir, file)
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 1. Lang deÄŸiÅŸkeni kontrolÃ¼
        if '/en/' in content and '{{ lang }}' not in content:
            if file in ['home.html', 'list.html', 'single.html']:
                errors.append(f"{file}: /en/ var ama {{ lang }} yok (dil yÃ¶nlendirme hatasÄ±)")
        
        # 2. Side menu link kontrolÃ¼
        if 'href="{{ lang }}"' in content or 'href="{{ lang }}/"' in content:
            errors.append(f"{file}: href baÅŸÄ±nda / eksik (href=\"/{{ lang }}/\" olmalÄ±)")
        
        # 3. Dark mode toggle kontrolÃ¼
        if 'darkModeToggle' not in content:
            errors.append(f"{file}: Dark mode butonu yok")
        
        # 4. Toggle switch kontrolÃ¼
        if 'toggle-switch' not in content:
            errors.append(f"{file}: toggle-switch sÄ±nÄ±fÄ± yok")
    
    return errors

def check_pending_tasks():
    """tasks.json'da pending gÃ¶rev var mÄ± kontrol eder"""
    if not os.path.exists("tasks.json"):
        print("âš ï¸ tasks.json bulunamadÄ±, yeni task eklenmemiÅŸ olabilir.")
        return 0
    
    with open("tasks.json", "r", encoding="utf-8") as f:
        tasks = json.load(f)
    
    pending = [t for t in tasks if t.get("status") == "pending"]
    
    if not pending:
        print("âŒ BEKLEYEN GÃ–REV YOK! Ã–nce 'Add New Task' workflow'u ile task ekleyin.")
        return 0
    
    print(f"âœ… {len(pending)} pending gÃ¶rev bulundu.")
    return len(pending)

if __name__ == "__main__":
    print("\n" + "="*50)
    print("ğŸ” STARTER BOT - TEMPLATE VE TASK KONTROLÃœ")
    print("="*50 + "\n")
    
    # 1. Template kontrolÃ¼
    print("ğŸ“ Template'ler kontrol ediliyor...")
    template_errors = test_templates()
    
    if template_errors:
        print("âŒ TEMPLATE HATALARI:")
        for err in template_errors:
            print(f"   {err}")
        print("\nğŸš¨ Workflow durduruluyor. Ã–nce template'leri dÃ¼zeltin.")
        sys.exit(1)
    else:
        print("âœ… TÃ¼m template'ler doÄŸru gÃ¶rÃ¼nÃ¼yor.\n")
    
    # 2. Pending task kontrolÃ¼
    print("ğŸ“‹ Task'ler kontrol ediliyor...")
    pending_count = check_pending_tasks()
    
    if pending_count == 0:
        print("\nğŸš¨ Workflow durduruluyor. Ã–nce 'Add New Task' ile task ekleyin.")
        sys.exit(1)
    
    print("\n" + "="*50)
    print("âœ… TÃœM KONTROLLER GEÃ‡TÄ°. CREATOR BAÅLAYABÄ°LÄ°R.")
    print("="*50 + "\n")            print(f"   {err}")
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
