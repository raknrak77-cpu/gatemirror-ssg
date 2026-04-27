import os
import sys
import json
import re
import subprocess
import boto3
from botocore.client import Config
from datetime import datetime

# ================= R2 BAĞLANTISI =================
R2_ID = os.getenv('R2_ACCOUNT_ID')
R2_ACCESS_KEY = os.getenv('R2_ACCESS_KEY_ID')
R2_SECRET_KEY = os.getenv('R2_SECRET_ACCESS_KEY')
R2_BUCKET = os.getenv('R2_BUCKET_NAME')
R2_PUBLIC_URL = os.getenv('R2_PUBLIC_URL', '').rstrip('/')

s3 = boto3.client(
    's3',
    endpoint_url=f'https://{R2_ID}.r2.cloudflarestorage.com',
    aws_access_key_id=R2_ACCESS_KEY,
    aws_secret_access_key=R2_SECRET_KEY,
    config=Config(signature_version='s3v4'),
    region_name='auto'
)

def git_commit_file(filepath, commit_msg):
    try:
        subprocess.run(["git", "config", "user.email", "action@github.com"], capture_output=True)
        subprocess.run(["git", "config", "user.name", "GitHub Action"], capture_output=True)
        subprocess.run(["git", "pull", "--rebase", "origin", "main"], capture_output=True)
        subprocess.run(["git", "add", filepath], capture_output=True)
        result = subprocess.run(["git", "commit", "-m", commit_msg, "--allow-empty"], capture_output=True)
        if result.returncode == 0:
            subprocess.run(["git", "push", "origin", "main"], capture_output=True)
            print(f"   ✅ Git commit yapıldı: {filepath}")
            return True
        else:
            print(f"   📝 Değişiklik yok")
            return True
    except Exception as e:
        print(f"   ⚠️ Git commit hatası: {e}")
        return False

def list_all_files(prefix):
    files = []
    continuation_token = None
    while True:
        try:
            if continuation_token:
                response = s3.list_objects_v2(Bucket=R2_BUCKET, Prefix=prefix, ContinuationToken=continuation_token)
            else:
                response = s3.list_objects_v2(Bucket=R2_BUCKET, Prefix=prefix)
        except:
            return []
        if 'Contents' not in response:
            break
        for obj in response['Contents']:
            files.append(obj['Key'])
        if response.get('IsTruncated'):
            continuation_token = response.get('NextContinuationToken')
        else:
            break
    return files

def hash_exists_in_raw_articles(hash_id):
    for lang in ['en', 'es', 'de', 'fr']:
        prefix = f"raw-articles/{lang}/"
        try:
            files = list_all_files(prefix)
            for key in files:
                if hash_id in key and key.endswith('.html'):
                    return True
        except:
            continue
    return False

def load_json(filepath):
    if not os.path.exists(filepath):
        return []
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(filepath, data):
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def append_to_json(filepath, new_items):
    existing = load_json(filepath)
    existing.extend(new_items)
    save_json(filepath, existing)

def load_processed_tasks():
    processed_path = "task/processed.json"
    if not os.path.exists(processed_path):
        return []
    with open(processed_path, "r", encoding="utf-8") as f:
        return json.load(f)

# ================= TEST FONKSİYONLARI =================
def test_templates():
    templates_dir = "templates"
    errors = []
    skip_files = ['manifesto.html', 'hero.html']
    if not os.path.exists(templates_dir):
        print("❌ templates/ klasörü bulunamadı!")
        sys.exit(1)
    for file in os.listdir(templates_dir):
        if not file.endswith('.html'):
            continue
        if file in skip_files:
            print(f"   ⏭️ {file} atlandı")
            continue
        path = os.path.join(templates_dir, file)
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        if '/en/' in content and '{{ lang }}' not in content:
            errors.append(f"{file}: /en/ var ama {{ lang }} yok")
        if 'href="{{ lang }}"' in content or 'href="{{ lang }}/"' in content:
            errors.append(f"{file}: href başında / eksik")
        if 'darkModeToggle' not in content and 'toggle-switch' not in content:
            errors.append(f"{file}: Dark mode toggle butonu yok")
        if 'font-awesome' not in content and 'fa-bars' not in content:
            errors.append(f"{file}: Font Awesome linki yok")
        if '{% include "hero.html"' in content:
            errors.append(f"{file}: include hero.html kullanılıyor")
        if '<style>' not in content:
            errors.append(f"{file}: Gömülü CSS bulunamadı")
    return errors

def test_css():
    css_path = "templates/css/style.css"
    warnings = []
    if not os.path.exists(css_path):
        warnings.append("style.css dosyası bulunamadı (gömülü CSS kullanılıyor)")
        return [], warnings
    return [], warnings

def test_static_pages():
    static_pages = ['about-us.html', 'contact.html', 'privacy-policy.html']
    errors = []
    for page in static_pages:
        path = os.path.join(".", page)
        if not os.path.exists(path):
            errors.append(f"Statik sayfa bulunamadı: {page}")
            continue
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        if 'font-awesome' not in content:
            errors.append(f"{page}: Font Awesome linki yok")
        if '<style>' not in content:
            errors.append(f"{page}: Gömülü CSS bulunamadı")
        if 'class="hero"' not in content:
            errors.append(f"{page}: Hero bileşeni yok")
        if 'side-menu' not in content:
            errors.append(f"{page}: Side menu yok")
        if 'darkModeToggle' not in content and 'toggle-switch' not in content:
            errors.append(f"{page}: Dark mode butonu yok")
    return errors

def test_hero_json():
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
    warnings = []
    explore_dirs = ["explore/all-articles", "explore/categories", "explore/category-archive"]
    for d in explore_dirs:
        if not os.path.exists(d):
            warnings.append(f"{d}/ klasörü yok (Librarian çalışınca oluşacak)")
    return warnings

# ================= ANA FUNC =================

def check_pending_tasks():
    tasks_path = "task/tasks.json"
    skipped_path = "task/skipped.json"
    
    if not os.path.exists(tasks_path):
        print("⚠️ task/tasks.json bulunamadı!")
        return 0
    
    pending_tasks = load_json(tasks_path)
    
    if not pending_tasks:
        print("❌ BEKLEYEN GÖREV YOK! task/tasks.json boş.")
        return 0
    
    # processed.json'daki hash'leri al
    processed_tasks = load_processed_tasks()
    processed_hashes = {task.get("hash") for task in processed_tasks if task.get("hash")}
    
    valid_tasks = []
    skipped_tasks = []
    deleted_from_tasks = []
    
    for task in pending_tasks:
        task_id = task.get('task_id')
        hash_id = task.get('hash')
        status = task.get('status', 'pending')
        
        # ========== YENİ: HASH VAR + PROCESSED.JSON'DA VAR = SİL ==========
        if hash_id and hash_id in processed_hashes:
            print(f"   🗑️ Task {task_id}: hash={hash_id} zaten processed.json'da! tasks.json'dan SİLİNİYOR.")
            deleted_from_tasks.append(task)
            continue
        
        # HASH VAR + PENDING = hatalı üretim
        if hash_id and status == "pending":
            print(f"   ⚠️ Task {task_id}: hash={hash_id} var ama pending = HATALI ÜRETİM")
            task["skipped_at"] = datetime.now().isoformat()
            task["skip_reason"] = "hash_exists_but_pending"
            skipped_tasks.append(task)
            continue
        
        # HASH VAR + raw-articles/ var mı kontrol et
        if hash_id and hash_exists_in_raw_articles(hash_id):
            print(f"   ⚠️ Task {task_id}: hash={hash_id} zaten raw-articles/'de var! ATLANIYOR.")
            task["skipped_at"] = datetime.now().isoformat()
            task["skip_reason"] = "hash_already_in_raw_articles"
            skipped_tasks.append(task)
            continue
        
        valid_tasks.append(task)
    
    # valid olanları geri yaz
    save_json(tasks_path, valid_tasks)
    
    # skipped olanları ekle ve ACİL COMMIT YAP
    if skipped_tasks:
        append_to_json(skipped_path, skipped_tasks)
        print(f"   📝 {len(skipped_tasks)} görev 'skipped' olarak işaretlendi.")
        git_commit_file(skipped_path, f"chore: move {len(skipped_tasks)} hatalı task to skipped")
        git_commit_file(tasks_path, "chore: remove hatalı tasks from tasks.json")
    
    # silinenler varsa ACİL COMMIT YAP
    if deleted_from_tasks:
        print(f"   🗑️ {len(deleted_from_tasks)} görev processed.json'da olduğu için tasks.json'dan silindi.")
        git_commit_file(tasks_path, f"chore: remove {len(deleted_from_tasks)} already processed tasks from tasks.json")
    
    if not valid_tasks:
        print("❌ İŞLENECEK GEÇERLİ GÖREV YOK!")
        return 0
    
    print(f"✅ {len(valid_tasks)} geçerli pending görev bulundu ( {len(skipped_tasks)} görev atlandı, {len(deleted_from_tasks)} görev silindi).")
    return len(valid_tasks)

def starter():
    print("\n" + "=" * 60)
    print("🔍 STARTER BOT v11 - ACİL SİLEN")
    print("   ✅ task/tasks.json oku")
    print("   ✅ Hash kontrolü yap")
    print("   ✅ Processed.json'da varsa tasks.json'dan SİL")
    print("   ✅ Hatalıları task/skipped.json'a TAŞI")
    print("   ✅ ACİL COMMIT YAP")
    print("=" * 60 + "\n")
    
    all_errors = []
    all_warnings = []
    
    print("📁 Template'ler kontrol ediliyor...")
    template_errors = test_templates()
    if template_errors:
        all_errors.extend(template_errors)
    else:
        print("   ✅ Tüm template'ler doğru görünüyor.")
    
    print("\n🎨 CSS dosyası kontrol ediliyor...")
    css_errors, css_warnings = test_css()
    if css_errors:
        all_errors.extend(css_errors)
    if css_warnings:
        all_warnings.extend(css_warnings)
    
    print("\n📄 Statik sayfalar kontrol ediliyor...")
    static_errors = test_static_pages()
    if static_errors:
        all_errors.extend(static_errors)
    else:
        print("   ✅ Statik sayfalar doğru görünüyor.")
    
    print("\n🎯 hero.json kontrol ediliyor...")
    hero_errors = test_hero_json()
    if hero_errors:
        all_errors.extend(hero_errors)
    else:
        print("   ✅ hero.json doğru görünüyor.")
    
    print("\n📂 Explore klasörü kontrol ediliyor...")
    explore_warnings = test_explore_folder()
    if explore_warnings:
        all_warnings.extend(explore_warnings)
    else:
        print("   ✅ Explore klasör yapısı tamam.")
    
    print("\n📋 Task'ler kontrol ediliyor (HASH KONTROLLÜ + PROCESSED KONTROLÜ)...")
    pending_count = check_pending_tasks()
    
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
    
    if all_warnings:
        print("\n⚠️ UYARILAR (workflow devam ediyor):")
        for warn in all_warnings:
            print(f"   {warn}")
    
    if pending_count == 0:
        print("\n🚨 Workflow durduruluyor. Geçerli pending görev yok.")
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("✅ TÜM KONTROLLER GEÇTİ. CREATOR BAŞLAYABİLİR.")
    print("=" * 60 + "\n")

if __name__ == "__main__":
    starter()
