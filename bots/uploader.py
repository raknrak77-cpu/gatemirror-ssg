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

# ================= YARDIMCI FONKSİYONLAR =================

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

def get_hash_from_content():
    """content/ klasöründeki en son dosyadan hash'i al"""
    content_base = "content"
    
    if not os.path.exists(content_base):
        print("❌ content/ klasörü yok! Önce Creator'ı çalıştırın.")
        return None, None
    
    latest_file = None
    latest_time = 0
    latest_hash = None
    
    for root, dirs, files in os.walk(content_base):
        for file in files:
            if not file.endswith('.html'):
                continue
            filepath = os.path.join(root, file)
            mtime = os.path.getmtime(filepath)
            if mtime > latest_time:
                latest_time = mtime
                latest_file = filepath
                # Dosya adından hash al (format: hash-slug.html)
                filename = os.path.basename(filepath)
                if '-' in filename:
                    latest_hash = filename.split('-')[0]
                else:
                    latest_hash = filename.replace('.html', '')
    
    if not latest_hash:
        print("❌ content/ klasöründe hash bulunamadı!")
        return None, None
    
    print(f"   📄 En son dosya: {latest_file}")
    print(f"   🔑 Hash: {latest_hash}")
    return latest_hash, latest_file

def update_pending_task_with_hash(hash_id):
    """task/tasks.json'daki ilk pending task'e hash ve status yazar"""
    tasks_path = "task/tasks.json"
    
    if not os.path.exists(tasks_path):
        print("❌ task/tasks.json bulunamadı!")
        return None
    
    with open(tasks_path, "r", encoding="utf-8") as f:
        tasks = json.load(f)
    
    if not tasks:
        print("❌ task/tasks.json boş!")
        return None
    
    # İlk task'i güncelle
    task = tasks[0]
    task["hash"] = hash_id
    task["status"] = "uploaded"
    task["uploaded_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Güncellenen task'i kaydet
    with open(tasks_path, "w", encoding="utf-8") as f:
        json.dump(tasks, f, indent=4, ensure_ascii=False)
    
    print(f"   ✅ Task {task.get('task_id')} güncellendi: hash={hash_id}, status=uploaded")
    return task

def move_to_processed(task):
    """Task'i task/tasks.json'dan sil, task/processed.json'a ekle"""
    tasks_path = "task/tasks.json"
    processed_path = "task/processed.json"
    
    if not os.path.exists(tasks_path):
        return False
    
    with open(tasks_path, "r", encoding="utf-8") as f:
        tasks = json.load(f)
    
    if not tasks:
        return False
    
    # İlk task'i al ve sil
    removed_task = tasks.pop(0)
    
    # Kalanları kaydet
    with open(tasks_path, "w", encoding="utf-8") as f:
        json.dump(tasks, f, indent=4, ensure_ascii=False)
    
    # Processed.json'a ekle
    append_to_json(processed_path, [removed_task])
    
    print(f"   ✅ Task {removed_task.get('task_id')} task/tasks.json'dan silindi, processed.json'a eklendi")
    return True

# ================= YÜKLEME FONKSİYONLARI =================

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
    print("📤 UPLOADER BOT v26 - task/ klasörü")
    print("   ✅ content/ klasöründen hash al")
    print("   ✅ task/tasks.json'a hash yaz")
    print("   ✅ R2'ye yükle")
    print("   ✅ Task'i processed.json'a taşı")
    print("=" * 60)
    
    # ========== 1. ADIM: Hash'i bul ==========
    print("\n📝 1. ADIM: Hash bulunuyor...")
    hash_id, latest_file = get_hash_from_content()
    if not hash_id:
        print("❌ Hash bulunamadı! Önce Creator'ı çalıştırın.")
        sys.exit(1)
    
    # ========== 2. ADIM: tasks.json'a hash yaz ==========
    print("\n📝 2. ADIM: tasks.json güncelleniyor...")
    task = update_pending_task_with_hash(hash_id)
    if not task:
        print("❌ tasks.json güncellenemedi!")
        sys.exit(1)
    
    # ========== 3. ADIM: TEMPLATE ve ASSETS yükle ==========
    print("\n📁 3. ADIM: Template ve Assets yükleniyor...")
    upload_templates()
    upload_css_to_assets()
    upload_svg_patterns()
    upload_manifesto_images()
    
    # ========== 4. ADIM: İÇERİK YÜKLE ==========
    print("\n📁 4. ADIM: İçerik yükleniyor (raw-articles/)")
    content_base = "content"
    
    if not os.path.exists(content_base):
        print(f"❌ {content_base} klasörü yok!")
        sys.exit(1)
    
    uploaded_files = []
    for root, dirs, files in os.walk(content_base):
        for file in files:
            if not file.endswith('.html'):
                continue
            local_path = os.path.join(root, file)
            r2_key = local_path.replace("content/", "raw-articles/")
            if upload_file_to_r2(local_path, r2_key):
                uploaded_files.append(local_path)
    
    # ========== 5. ADIM: LOCAL TEMİZLİK ==========
    print("\n🗑️ 5. ADIM: Local temizlik")
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
    
    # ========== 6. ADIM: Task'i processed.json'a TAŞI ==========
    print("\n📝 6. ADIM: Task processed.json'a taşınıyor...")
    move_to_processed(task)
    
    # ========== 7. ADIM: TEMİZLİK ==========
    print("\n🗑️ 7. ADIM: current_hash.txt temizleniyor...")
    if os.path.exists("task/current_hash.txt"):
        os.remove("task/current_hash.txt")
        print("   🗑️ Silindi: task/current_hash.txt")
    
    print("\n" + "=" * 60)
    print("🏁 UPLOADER v26 TAMAMLANDI!")
    print(f"   🔑 Hash: {hash_id}")
    print("   ✅ tasks.json güncellendi (status=uploaded)")
    print("   ✅ Task processed.json'a taşındı")
    print("=" * 60)

if __name__ == "__main__":
    uploader()
