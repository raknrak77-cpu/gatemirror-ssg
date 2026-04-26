import os
import sys
import json
import boto3
from botocore.client import Config
from datetime import datetime

# R2 Secrets
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

# ================= TASK GÜNCELLEME (SADECE HASH + FSYNC) =================

def get_hash_from_content():
    """content/ klasöründeki en son dosyadan hash'i al"""
    content_base = "content"
    if not os.path.exists(content_base):
        return None
    
    latest_hash = None
    latest_time = 0
    
    for root, dirs, files in os.walk(content_base):
        for file in files:
            if not file.endswith('.html'):
                continue
            filepath = os.path.join(root, file)
            mtime = os.path.getmtime(filepath)
            if mtime > latest_time:
                latest_time = mtime
                filename = os.path.basename(filepath)
                if '-' in filename:
                    hash_id = filename.split('-')[0]
                    if len(hash_id) == 8:
                        latest_hash = hash_id
                else:
                    latest_hash = filename.replace('.html', '')
    
    return latest_hash

def update_task_with_hash_only(hash_id):
    """task/tasks.json'daki ilk task'e SADECE hash ekler, status DEĞİŞMEZ"""
    tasks_path = "task/tasks.json"
    
    print(f"   📂 HEDEF DOSYA: {os.path.abspath(tasks_path)}")
    
    if not os.path.exists(tasks_path):
        print(f"   ❌ DOSYA YOK: {tasks_path}")
        return False
    
    with open(tasks_path, "r", encoding="utf-8") as f:
        tasks = json.load(f)
    
    if not tasks:
        print("   ⚠️ task/tasks.json boş")
        return False
    
    # İlk task'i güncelle (sadece hash ekle, status DOKUNMA)
    task = tasks[0]
    old_hash = task.get("hash")
    task["hash"] = hash_id
    task["hash_updated_at"] = datetime.now().isoformat()
    # status değişmiyor! "pending" kalıyor
    
    # YAZ ve ZORLA DISKE YAZ (fsync)
    with open(tasks_path, "w", encoding="utf-8") as f:
        json.dump(tasks, f, indent=4, ensure_ascii=False)
        f.flush()
        os.fsync(f.fileno())
    
    # DOĞRULA (GERÇEKTEN YAZILDI MI?)
    with open(tasks_path, "r", encoding="utf-8") as f:
        verify_tasks = json.load(f)
    
    if verify_tasks[0].get("hash") == hash_id:
        print(f"   ✅ Task {task.get('task_id')}: hash eklendi {old_hash} → {hash_id} (status: {task.get('status')})")
        print(f"   📄 DOSYA BOYUTU: {os.path.getsize(tasks_path)} bytes")
        return True
    else:
        print(f"   ❌ DOĞRULAMA BAŞARISIZ! {verify_tasks[0].get('hash')} != {hash_id}")
        return False

# ================= MEVCUT YÜKLEME FONKSİYONLARI =================

def upload_file_to_r2(local_path, r2_key, content_type=None):
    if os.path.exists(local_path):
        print(f"🚀 Yükleniyor: {local_path} -> {r2_key}")
        extra_args = {}
        if content_type:
            extra_args['ContentType'] = content_type
        s3.upload_file(local_path, R2_BUCKET, r2_key, ExtraArgs=extra_args)
        print(f"✅ Yüklendi: {r2_key}")
        return True
    return False

def convert_to_webp(input_path, output_path):
    try:
        from PIL import Image
        with Image.open(input_path) as img:
            if img.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = background
            img.save(output_path, 'WEBP', quality=85)
        return True
    except Exception as e:
        print(f"⚠️ WebP dönüşüm hatası: {e}")
        return False

def upload_templates():
    templates_dir = "templates"
    if not os.path.exists(templates_dir):
        return
    for file in os.listdir(templates_dir):
        if file.endswith('.html'):
            local_path = os.path.join(templates_dir, file)
            if os.path.isfile(local_path):
                upload_file_to_r2(local_path, f"templates/{file}")

def upload_css_to_assets():
    local_path = "templates/css/style.css"
    if os.path.exists(local_path):
        upload_file_to_r2(local_path, "assets/css/style.css", content_type='text/css')

def upload_svg_patterns():
    svg_files = [
        ("assets/all-patterns/spiral_out/spiral_circular_basic_18.svg", "assets/svg1.svg"),
        ("assets/all-patterns/spiral_out/spiral_circular_medium_09.svg", "assets/svg2.svg"),
        ("assets/all-patterns/breath_wave/breath_wave_basic_02.svgq", "assets/svg3.svg"),
    ]
    for local_path, r2_key in svg_files:
        if os.path.exists(local_path):
            upload_file_to_r2(local_path, r2_key, content_type='image/svg+xml')

def upload_manifesto_images():
    local_dir = "assets/manifesto"
    if not os.path.exists(local_dir):
        return
    for file in os.listdir(local_dir):
        if file.endswith(('.jpg', '.jpeg', '.png')):
            local_path = os.path.join(local_dir, file)
            name = os.path.splitext(file)[0]
            webp_file = f"{name}.webp"
            webp_path = os.path.join(local_dir, webp_file)
            if convert_to_webp(local_path, webp_path):
                upload_file_to_r2(webp_path, f"assets/manifesto/{webp_file}", content_type='image/webp')
                os.remove(webp_path)

# ================= ANA UPLOADER =================

def uploader():
    print("\n" + "=" * 60)
    print("📤 UPLOADER BOT v30 - SADECE HASH EKLER + FSYNC")
    print("   ✅ content/ hash al, tasks.json'a SADECE HASH EKLE")
    print("   ✅ status DOKUNMA (pending kalır)")
    print("   ✅ fsync ile zorla diske yaz")
    print("   ✅ Doğrulama yap")
    print("=" * 60)
    
    # ========== 1. ADIM: Hash'i bul ve tasks.json'a SADECE HASH yaz ==========
    print("\n📝 1. ADIM: Hash bulunuyor...")
    hash_id = get_hash_from_content()
    if hash_id:
        print(f"   🔑 Hash bulundu: {hash_id}")
        success = update_task_with_hash_only(hash_id)
        if success:
            print("   ✅ Hash eklendi, status değişmedi")
        else:
            print("   ❌ Hash eklenemedi!")
    else:
        print("   ⚠️ Hash bulunamadı, task güncelleme atlanıyor")
    
    # ========== 2. ADIM: NORMAL YÜKLEME ==========
    print("\n📁 2. ADIM: Template ve Assets yükleniyor...")
    upload_templates()
    upload_css_to_assets()
    upload_svg_patterns()
    upload_manifesto_images()
    
    # ========== 3. ADIM: İÇERİK YÜKLEME ==========
    content_base = "content"
    if not os.path.exists(content_base):
        print(f"❌ {content_base} klasörü yok!")
        return
    
    print("\n📁 3. ADIM: İÇERİK YÜKLEME (raw-articles/)")
    uploaded_files = []
    
    for root, dirs, files in os.walk(content_base):
        for file in files:
            if not file.endswith('.html'):
                continue
            local_path = os.path.join(root, file)
            r2_key = local_path.replace("content/", "raw-articles/")
            if upload_file_to_r2(local_path, r2_key):
                uploaded_files.append(local_path)
    
    # ========== 4. ADIM: LOCAL TEMİZLİK ==========
    print("\n🗑️ 4. ADIM: LOCAL TEMİZLİK")
    for file_path in uploaded_files:
        try:
            os.remove(file_path)
            print(f"   🗑️ Silindi: {file_path}")
        except Exception as e:
            print(f"   ⚠️ Silinemedi: {file_path} - {e}")
    
    for root, dirs, files in os.walk(content_base, topdown=False):
        for dir_name in dirs:
            dir_path = os.path.join(root, dir_name)
            try:
                if not os.listdir(dir_path):
                    os.rmdir(dir_path)
                    print(f"   🗑️ Boş klasör silindi: {dir_path}")
            except:
                pass
    
    # ========== 5. ADIM: current_hash.txt KORU (SİLME) ==========
    print("\n📝 5. ADIM: current_hash.txt korunuyor...")
    if os.path.exists("task/current_hash.txt"):
        print("   🛡️ current_hash.txt KORUNDU (Librarian kullanacak)")
    
    # ========== 6. ADIM: DOĞRULAMA RAPORU ==========
    print("\n📋 6. ADIM: DOĞRULAMA")
    if os.path.exists("task/tasks.json"):
        with open("task/tasks.json", "r") as f:
            tasks = json.load(f)
        if tasks and tasks[0].get("hash"):
            print(f"   ✅ İLK TASK HASH: {tasks[0].get('hash')}")
            print(f"   ✅ İLK TASK STATUS: {tasks[0].get('status')} (DEĞİŞMEMİŞ OLMALI)")
        else:
            print("   ❌ İLK TASK'TA HASH YOK!")
    
    print("\n" + "=" * 60)
    print("🏁 UPLOADER v30 TAMAMLANDI!")
    print("   ✅ SADECE HASH EKLENDİ, STATUS DEĞİŞMEDİ")
    print("   ✅ current_hash.txt KORUNDU")
    print("=" * 60)

if __name__ == "__main__":
    uploader()
