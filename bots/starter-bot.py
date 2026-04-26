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
    """Bir dosyayı hemen commit et ve pushla"""
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
            print(f"   📝 Değişiklik yok veya commit gerekmiyor")
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

# ================= TEST FONKSİYONLARI (aynı) =================
# ... (test_templates, test_css, test_static_pages, test_hero_json, test_explore_folder aynı)

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
    
    valid_tasks = []
    skipped_tasks = []
    
    for task in pending_tasks:
        task_id = task.get('task_id')
        hash_id = task.get('hash')
        status = task.get('status', 'pending')
        
        if hash_id and status == "pending":
            print(f"   ⚠️ Task {task_id}: hash={hash_id} var ama pending = HATALI ÜRETİM")
            task["skipped_at"] = datetime.now().isoformat()
            task["skip_reason"] = "hash_exists_but_pending"
            skipped_tasks.append(task)
            continue
        
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
        
        # ========== KRİTİK: ACİL COMMIT ==========
        git_commit_file(skipped_path, f"chore: move {len(skipped_tasks)} hatalı task to skipped")
        git_commit_file(tasks_path, "chore: remove hatalı tasks from tasks.json")
    
    if not valid_tasks:
        print("❌ İŞLENECEK GEÇERLİ GÖREV YOK!")
        return 0
    
    print(f"✅ {len(valid_tasks)} geçerli pending görev bulundu ( {len(skipped_tasks)} görev atlandı).")
    return len(valid_tasks)

def starter():
    print("\n" + "=" * 60)
    print("🔍 STARTER BOT v10 - ACİL COMMIT")
    print("   ✅ task/tasks.json oku")
    print("   ✅ Hash kontrolü yap")
    print("   ✅ Hatalıları task/skipped.json'a TAŞI")
    print("   ✅ ACİL COMMIT YAP")
    print("=" * 60 + "\n")
    
    # ... (testler aynı)
    
    pending_count = check_pending_tasks()
    
    if pending_count == 0:
        print("\n🚨 Workflow durduruluyor. Geçerli pending görev yok.")
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("✅ TÜM KONTROLLER GEÇTİ. CREATOR BAŞLAYABİLİR.")
    print("=" * 60 + "\n")

if __name__ == "__main__":
    starter()
