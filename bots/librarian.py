import os
import json
import sys
import re
import boto3
from datetime import datetime
from botocore.client import Config
from concurrent.futures import ThreadPoolExecutor, as_completed

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

LANGUAGES = ['en', 'es', 'de', 'fr']


# ================= GÖRSEL KONTROLÜ (KALDIRILDI - Publisher parse kontrolü yeterli) =================
# Artık görsel kontrolü YAPILMAYACAK. Publisher parse edebildiyse yayınlanır.


# ================= TASK TAŞIMA =================

def get_current_hash():
    """current_hash.txt'den hash'i okur ve siler"""
    hash_file = "task/current_hash.txt"
    if os.path.exists(hash_file):
        with open(hash_file, "r") as f:
            hash_id = f.read().strip()
        os.remove(hash_file)
        print(f"   📖 current_hash.txt okundu: {hash_id}")
        return hash_id
    return None


def get_task_by_hash(target_hash):
    """tasks.json'dan hash'e göre task'i bulur"""
    tasks_path = "task/tasks.json"
    if not os.path.exists(tasks_path):
        return None
    
    with open(tasks_path, "r", encoding="utf-8") as f:
        tasks = json.load(f)
    
    for task in tasks:
        if task.get("hash") == target_hash:
            return task
    return None


def move_task_to_skipped(target_hash, reason):
    """Task'i skipped.json'a taşır ve tasks.json'dan siler"""
    tasks_path = "task/tasks.json"
    skipped_path = "task/skipped.json"
    
    if not os.path.exists(tasks_path):
        return False
    
    with open(tasks_path, "r", encoding="utf-8") as f:
        tasks = json.load(f)
    
    target_task = None
    target_index = None
    for i, task in enumerate(tasks):
        if task.get("hash") == target_hash:
            target_task = task
            target_index = i
            break
    
    if not target_task:
        print(f"   ⚠️ Hash {target_hash} tasks.json'da bulunamadı")
        return False
    
    target_task["skipped_at"] = datetime.now().isoformat()
    target_task["skip_reason"] = reason
    
    if os.path.exists(skipped_path):
        with open(skipped_path, "r", encoding="utf-8") as f:
            skipped = json.load(f)
    else:
        skipped = []
    
    skipped.append(target_task)
    
    with open(skipped_path, "w", encoding="utf-8") as f:
        json.dump(skipped, f, indent=4, ensure_ascii=False)
    
    tasks.pop(target_index)
    
    with open(tasks_path, "w", encoding="utf-8") as f:
        json.dump(tasks, f, indent=4, ensure_ascii=False)
        f.flush()
        os.fsync(f.fileno())
    
    print(f"   ❌ Task {target_task.get('task_id')} (hash={target_hash}) SKIPPED: {reason}")
    return True


def move_task_to_processed(target_hash):
    """Task'i processed.json'a taşır (görsel kontrolü YOK)"""
    tasks_path = "task/tasks.json"
    processed_path = "task/processed.json"
    
    if not os.path.exists(tasks_path):
        print("   ⚠️ task/tasks.json bulunamadı")
        return False
    
    with open(tasks_path, "r", encoding="utf-8") as f:
        tasks = json.load(f)
    
    if not tasks:
        print("   ⚠️ task/tasks.json boş")
        return False
    
    target_index = None
    target_task = None
    
    for i, task in enumerate(tasks):
        if task.get("hash") == target_hash:
            target_index = i
            target_task = task
            break
    
    if target_index is None:
        print(f"   ⚠️ Hash {target_hash} ile task bulunamadı")
        return False
    
    if os.path.exists(processed_path):
        with open(processed_path, "r", encoding="utf-8") as f:
            processed = json.load(f)
    else:
        processed = []
    
    target_task["status"] = "processed"
    target_task["processed_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    processed.insert(0, target_task)
    
    with open(processed_path, "w", encoding="utf-8") as f:
        json.dump(processed, f, indent=4, ensure_ascii=False)
    
    print(f"   ✅ Task {target_task.get('task_id')} (hash={target_hash}) processed.json'a EKLENDI (en basa)")
    
    tasks.pop(target_index)
    
    with open(tasks_path, "w", encoding="utf-8") as f:
        json.dump(tasks, f, indent=4, ensure_ascii=False)
        f.flush()
        os.fsync(f.fileno())
    
    with open(tasks_path, "r", encoding="utf-8") as f:
        verify_tasks = json.load(f)
    
    for task in verify_tasks:
        if task.get("hash") == target_hash:
            print(f"   ❌ SILINEMEDI! Hash {target_hash} hala tasks.json'da!")
            return False
    
    print(f"   ✅ Task {target_task.get('task_id')} tasks.json'dan SILINDI")
    return True


# ================= YARDIMCI FONKSİYONLAR =================

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


def delete_file(key):
    try:
        s3.delete_object(Bucket=R2_BUCKET, Key=key)
        return True
    except:
        return False


def delete_folder(prefix):
    files = list_all_files(prefix)
    if not files:
        return
    for f in files:
        delete_file(f)
    print(f"   {len(files)} dosya silindi: {prefix}")


def copy_file(source_key, dest_key):
    try:
        response = s3.get_object(Bucket=R2_BUCKET, Key=source_key)
        content = response['Body'].read()
        s3.put_object(Bucket=R2_BUCKET, Key=dest_key, Body=content, ContentType='text/html')
        return True
    except:
        return False


def folder_exists(prefix):
    try:
        response = s3.list_objects_v2(Bucket=R2_BUCKET, Prefix=prefix, MaxKeys=1)
        return 'Contents' in response
    except:
        return False


# ================= MEVCUT ARTICLES/ KONTROLÜ (KALDIRILDI - Publisher yönetiyor) =================

def check_existing_articles():
    """Mevcut articles/ kontrolü - SADECE LİSTELEME, SİLME YOK"""
    print("\n" + "=" * 40)
    print("🔍 MEVCUT ARTICLES/ KONTROLÜ")
    print("   ⚠️ Tüm kontroller KALDIRILDI (Publisher V50 parse kontrolü yapıyor)")
    print("   🛡️ index.html KORUNACAK")
    print("=" * 40)
    
    articles_files = list_all_files('articles/')
    if not articles_files:
        print("   articles/ klasörü boş veya yok.")
        return []
    
    html_count = 0
    for key in articles_files:
        if key.endswith('.html') and not key.endswith('/index.html'):
            html_count += 1
    
    print(f"   📄 Toplam {html_count} makale dosyası mevcut (hepsi korunuyor)")
    print("   ✅ Hiçbir dosya silinmedi (Publisher V50'ye güveniyoruz)")
    return []


# ================= ATOMIC SWAP (KONTROLSÜZ) =================

def atomic_swap():
    print("\n" + "=" * 40)
    print("ATOMIC SWAP: articles_ready/ -> articles/ (KONTROLSÜZ)")
    print("   ⚠️ Publisher V50 parse kontrolü yaptı, tüm dosyalar güvenli")
    print("=" * 40)
    
    if not folder_exists('articles_ready/'):
        print("articles_ready/ bulunamadi! Swap iptal.")
        return False
    
    source_files = list_all_files('articles_ready/')
    if not source_files:
        print("articles_ready/ bos, swap iptal.")
        return False
    
    print(f"   {len(source_files)} dosya bulundu (hepsi swap edilecek)")
    
    valid_files = source_files
    
    if not valid_files:
        print("   ❌ Swap için dosya kalmadı!")
        return False
    
    print(f"   ✅ {len(valid_files)} dosya swap için uygun")
    
    success_count = 0
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {}
        for source_key in valid_files:
            dest_key = source_key.replace('articles_ready/', 'articles/', 1)
            future = executor.submit(copy_file, source_key, dest_key)
            futures[future] = source_key
        for future in as_completed(futures):
            if future.result():
                success_count += 1
    
    print(f"   {success_count}/{len(valid_files)} dosya basariyla yazildi")
    
    if success_count < len(valid_files) * 0.9:
        print(f"   ⚠️ Çok fazla hata ({success_count}/{len(valid_files)} basarili)")
        return False
    
    print("   articles_ready/ siliniyor...")
    delete_folder('articles_ready/')
    
    print("   ✅ Swap tamamlandi!")
    return True


# ================= HERO GÜNCELLEMELERİ =================

def update_hero_ticker():
    print("\n" + "=" * 40)
    print("HERO TICKER GUNCELLENIYOR")
    print("=" * 40)
    try:
        response = s3.get_object(Bucket=R2_BUCKET, Key='articles.json')
        data = json.loads(response['Body'].read().decode('utf-8'))
        articles = data['articles'] if isinstance(data, dict) and 'articles' in data else data
    except:
        print("   articles.json okunamadi")
        return False
    
    def shorten_title(title, max_length=55):
        if len(title) <= max_length:
            return title
        shortened = title[:max_length]
        last_space = shortened.rfind(' ')
        if last_space > 0:
            shortened = shortened[:last_space]
        return shortened + "..."
    
    def sanitize_text(text):
        text = text.replace('ı', 'i').replace('ğ', 'g').replace('ü', 'u')
        text = text.replace('ş', 's').replace('ö', 'o').replace('ç', 'c')
        text = text.replace('İ', 'I').replace('Ğ', 'G').replace('Ü', 'U')
        text = text.replace('Ş', 'S').replace('Ö', 'O').replace('Ç', 'C')
        return text
    
    new_ticker_items = {}
    for lang in LANGUAGES:
        lang_articles = [a for a in articles if a.get('lang') == lang and a.get('cover_image')]
        lang_articles.sort(key=lambda x: x.get('datetime', x.get('date', '')), reverse=True)
        latest = lang_articles[:6]
        items = []
        for a in latest:
            title = a.get('title', 'Untitled')
            short_title = shorten_title(title, 55)
            short_title = sanitize_text(short_title)
            url = a.get('url', '#')
            items.append(f"{short_title} -> {url}")
        new_ticker_items[lang] = items
        print(f"   {lang.upper()}: {len(items)} makale")
    
    try:
        hero_response = s3.get_object(Bucket=R2_BUCKET, Key='assets/hero.json')
        hero_data = json.loads(hero_response['Body'].read().decode('utf-8'))
    except:
        return False
    
    for lang in LANGUAGES:
        try:
            blocks = hero_data['pages']['home'][lang].get('blocks', [])
            mevcut_hide_on = None
            for i, block in enumerate(blocks):
                if block.get('type') == 'news_ticker':
                    mevcut_hide_on = block.get('hide_on')
                    blocks.pop(i)
                    break
            new_ticker = {"type": "news_ticker", "items": new_ticker_items.get(lang, []), "grid": "full"}
            if mevcut_hide_on:
                new_ticker["hide_on"] = mevcut_hide_on
            blocks.append(new_ticker)
            hero_data['pages']['home'][lang]['blocks'] = blocks
        except KeyError:
            continue
    
    hero_data['last_updated'] = datetime.now().isoformat()
    s3.put_object(
        Bucket=R2_BUCKET,
        Key='assets/hero.json',
        Body=json.dumps(hero_data, indent=2, ensure_ascii=False).encode('utf-8'),
        ContentType='application/json'
    )
    print("   hero.json guncellendi")
    return True


def update_hero_stats():
    print("\n" + "=" * 40)
    print("HERO STATS GUNCELLENIYOR")
    print("=" * 40)
    try:
        response = s3.get_object(Bucket=R2_BUCKET, Key='articles.json')
        data = json.loads(response['Body'].read().decode('utf-8'))
        articles = data['articles'] if isinstance(data, dict) and 'articles' in data else data
    except:
        return False
    
    lang_counts = {}
    for lang in LANGUAGES:
        lang_counts[lang] = len([a for a in articles if a.get('lang') == lang])
        print(f"   {lang.upper()}: {lang_counts[lang]} makale")
    
    try:
        hero_response = s3.get_object(Bucket=R2_BUCKET, Key='assets/hero.json')
        hero_data = json.loads(hero_response['Body'].read().decode('utf-8'))
    except:
        return False
    
    for lang in LANGUAGES:
        try:
            blocks = hero_data['pages']['home'][lang].get('blocks', [])
            for block in blocks:
                if block.get('type') == 'description':
                    mevcut = block.get('content', '')
                    if '[' in mevcut and 'Articles' in mevcut:
                        yeni = re.sub(r'\[[0-9]+ Articles', f'[{lang_counts[lang]} Articles', mevcut)
                        block['content'] = yeni
                        print(f"   {lang.upper()}: makale sayisi guncellendi ({lang_counts[lang]})")
                    break
            hero_data['pages']['home'][lang]['blocks'] = blocks
        except KeyError:
            continue
    
    s3.put_object(
        Bucket=R2_BUCKET,
        Key='assets/hero.json',
        Body=json.dumps(hero_data, indent=2, ensure_ascii=False).encode('utf-8'),
        ContentType='application/json'
    )
    print("   hero.json stats guncellendi")
    return True


def analyze_r2_storage():
    print("\n" + "=" * 40)
    print("R2 BUCKET ANALIZI")
    print("=" * 40)
    stats = {
        'html': 0, 'svg': 0, 'webp': 0, 'jpg': 0,
        'png': 0, 'json': 0, 'css': 0, 'js': 0, 'other': 0
    }
    total_files = 0
    total_size = 0
    continuation_token = None
    try:
        while True:
            if continuation_token:
                response = s3.list_objects_v2(Bucket=R2_BUCKET, ContinuationToken=continuation_token)
            else:
                response = s3.list_objects_v2(Bucket=R2_BUCKET)
            if 'Contents' not in response:
                break
            for obj in response['Contents']:
                key = obj['Key']
                size = obj['Size']
                total_files += 1
                total_size += size
                ext = key.split('.')[-1].lower() if '.' in key else 'other'
                if ext in ['html', 'htm']:
                    stats['html'] += 1
                elif ext == 'svg':
                    stats['svg'] += 1
                elif ext == 'webp':
                    stats['webp'] += 1
                elif ext in ['jpg', 'jpeg']:
                    stats['jpg'] += 1
                elif ext == 'png':
                    stats['png'] += 1
                elif ext == 'json':
                    stats['json'] += 1
                elif ext == 'css':
                    stats['css'] += 1
                elif ext == 'js':
                    stats['js'] += 1
                else:
                    stats['other'] += 1
            if response.get('IsTruncated'):
                continuation_token = response.get('NextContinuationToken')
            else:
                break
    except Exception as e:
        print(f"Analiz hatasi: {e}")
        return False
    
    print(f"\n📊 Toplam dosya: {total_files}")
    print(f"📦 Toplam boyut: {total_size / (1024*1024):.2f} MB")
    print("\n📁 Dosya türlerine göre dağılım:")
    for k, v in sorted(stats.items(), key=lambda x: -x[1]):
        if v > 0:
            print(f"   .{k}: {v} dosya")
    return True


# ================= ANA LIBRARIAN =================

def librarian():
    print("\n" + "=" * 60)
    print("📚 KUTUPHANECI BOT v34 - SADECE SWAP + TASK TAŞIMA")
    print("   🔍 Mevcut articles/ kontrolü (SADECE LİSTELEME, SİLME YOK)")
    print("   🛡️ index.html KORUNACAK")
    print("   ❌ Görsel kontrolü KALDIRILDI (Publisher V50 parse kontrolü yeterli)")
    print("   ❌ Karakter kontrolü KALDIRILDI")
    print("   ✅ Sadece swap ve task taşıma yapılır")
    print("=" * 60)
    
    analyze_r2_storage()
    check_existing_articles()
    update_hero_ticker()
    update_hero_stats()
    
    try:
        swap_success = atomic_swap()
        if swap_success:
            print("\n✅ SWAP BASARILI! Site yeni icerikle yayinda.")
            
            current_hash = get_current_hash()
            if current_hash:
                print(f"   📝 İşlenen hash: {current_hash}")
                
                task = get_task_by_hash(current_hash)
                if task:
                    move_task_to_processed(current_hash)
                else:
                    print(f"   ⚠️ Hash {current_hash} için task bulunamadı, işlem atlanıyor")
            else:
                print("   ⚠️ current_hash.txt bulunamadı, task taşınamadı")
        else:
            print("\n⚠️ SWAP BASARISIZ! Site eski icerikle devam ediyor.")
            
            current_hash = get_current_hash()
            if current_hash:
                print(f"   🗑️ Swap başarısız, current_hash.txt silindi: {current_hash}")
    except Exception as e:
        print(f"\n❌ KRITIK HATA: {e}")
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("🏁 KUTUPHANECI BOT v34 TAMAMLANDI!")
    print("   ✅ index.html koruması AKTIF")
    print("   ✅ Atomic swap KONTROLSÜZ (Publisher'a güveniyor)")
    print("   ❌ Görsel ve karakter kontrolleri KALDIRILDI")
    print("   ✅ Processed sıralaması: en son görev en üstte")
    print("=" * 60)


if __name__ == "__main__":
    librarian()
