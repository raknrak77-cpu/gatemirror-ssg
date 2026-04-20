import os
import json
import sys
import re
import boto3
from datetime import datetime
from botocore.client import Config
from concurrent.futures import ThreadPoolExecutor, as_completed

# ================= KONFIGURASYON =================
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

# Dil konfigurasyonu
LANGUAGES = ['en', 'es', 'de', 'fr']
LANG_NAMES = {
    'en': 'English', 'es': 'Espanol', 'de': 'Deutsch', 'fr': 'Francais'
}
LANG_FLAGS = {
    'en': 'US', 'es': 'ES', 'de': 'DE', 'fr': 'FR'
}

CATEGORIES = {
    'tech': {'en': 'Technology and AI', 'es': 'Tecnologia y IA', 'de': 'Technologie und KI', 'fr': 'Technologie et IA'},
    'wellness': {'en': 'Wellness', 'es': 'Bienestar', 'de': 'Wohlbefinden', 'fr': 'Bien-etre'},
    'future-economy': {'en': 'Future Economy', 'es': 'Economia Futura', 'de': 'ZukunftsWirtschaft', 'fr': 'Economie Future'},
    'eco': {'en': 'Eco and Sustainable', 'es': 'Eco y Sostenible', 'de': 'Oko und Nachhaltig', 'fr': 'Eco et Durable'},
    'elearning': {'en': 'E-Learning', 'es': 'E-Aprendizaje', 'de': 'E-Learning', 'fr': 'E-Apprentissage'}
}

# ================= R2 YARDIMCI FONKSIYONLAR =================

def list_all_files(prefix):
    files = []
    continuation_token = None
    
    while True:
        try:
            if continuation_token:
                response = s3.list_objects_v2(
                    Bucket=R2_BUCKET,
                    Prefix=prefix,
                    ContinuationToken=continuation_token
                )
            else:
                response = s3.list_objects_v2(Bucket=R2_BUCKET, Prefix=prefix)
        except Exception as e:
            print(f"   Listeleme hatasi: {e}")
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

def folder_exists(prefix):
    try:
        response = s3.list_objects_v2(Bucket=R2_BUCKET, Prefix=prefix, MaxKeys=1)
        return 'Contents' in response
    except:
        return False

def delete_folder(prefix):
    continuation_token = None
    deleted_count = 0
    
    while True:
        try:
            if continuation_token:
                response = s3.list_objects_v2(
                    Bucket=R2_BUCKET,
                    Prefix=prefix,
                    ContinuationToken=continuation_token
                )
            else:
                response = s3.list_objects_v2(Bucket=R2_BUCKET, Prefix=prefix)
        except Exception as e:
            print(f"   Listeleme hatasi: {e}")
            raise
        
        if 'Contents' not in response:
            break
        
        objects_to_delete = [{'Key': obj['Key']} for obj in response['Contents']]
        try:
            s3.delete_objects(Bucket=R2_BUCKET, Delete={'Objects': objects_to_delete})
            deleted_count += len(objects_to_delete)
        except Exception as e:
            print(f"   Silme hatasi: {e}")
            raise
        
        if response.get('IsTruncated'):
            continuation_token = response.get('NextContinuationToken')
        else:
            break
    
    if deleted_count > 0:
        print(f"   {deleted_count} dosya silindi: {prefix}")

def copy_and_overwrite(source_key, dest_key):
    try:
        response = s3.get_object(Bucket=R2_BUCKET, Key=source_key)
        content = response['Body'].read()
        s3.put_object(Bucket=R2_BUCKET, Key=dest_key, Body=content, ContentType='text/html')
        return True
    except Exception as e:
        print(f"   {source_key} -> {dest_key} yazilamadi: {e}")
        return False

# ================= ATOMIC SWAP =================

def atomic_swap():
    print("\n" + "=" * 40)
    print("ATOMIC SWAP: articles_ready/ -> articles/")
    print("=" * 40)
    
    if not folder_exists('articles_ready/'):
        print("articles_ready/ bulunamadi! Swap iptal.")
        return False
    
    print("articles_ready/ icindeki dosyalar listeleniyor...")
    source_files = list_all_files('articles_ready/')
    
    if not source_files:
        print("articles_ready/ bos, swap iptal.")
        return False
    
    print(f"   {len(source_files)} dosya bulundu.")
    print(f"{len(source_files)} dosya parallel yaziliyor (10 thread)...")
    
    success_count = 0
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {}
        for source_key in source_files:
            dest_key = source_key.replace('articles_ready/', 'articles/', 1)
            future = executor.submit(copy_and_overwrite, source_key, dest_key)
            futures[future] = source_key
        
        for future in as_completed(futures):
            if future.result():
                success_count += 1
    
    print(f"   {success_count}/{len(source_files)} dosya basariyla yazildi")
    
    if success_count < len(source_files) * 0.9:
        print(f"Cok fazla hata ({success_count}/{len(source_files)} basarili)")
        return False
    
    print("articles_ready/ siliniyor...")
    delete_folder('articles_ready/')
    
    print("Swap tamamlandi!")
    return True

# ================= JSON URETIMI =================

def get_articles_from_r2():
    try:
        response = s3.get_object(Bucket=R2_BUCKET, Key='articles.json')
        return json.loads(response['Body'].read().decode('utf-8'))
    except Exception as e:
        print(f"articles.json okunamadi: {e}")
        return []

def generate_explorer_json(articles):
    explorer_data = {
        "version": "1.0",
        "generated": datetime.now().isoformat(),
        "total_articles": len(articles),
        "languages": LANGUAGES,
        "categories": list(CATEGORIES.keys()),
        "articles": []
    }
    
    for article in articles:
        explorer_data["articles"].append({
            "url": article.get('url', '#'),
            "lang": article.get('lang', 'en'),
            "category": article.get('category', ''),
            "title": article.get('title', 'Untitled'),
            "description": article.get('description', ''),
            "date": article.get('date', ''),
            "sort_date": article.get('sort_date', ''),
            "reading_time": article.get('reading_time', 0),
            "views": article.get('views', 0),
            "cover_image": article.get('cover_image', ''),
            "slug": article.get('slug', '')
        })
    
    explorer_json = json.dumps(explorer_data, indent=2, ensure_ascii=False)
    s3.put_object(
        Bucket=R2_BUCKET,
        Key='explore/explorer.json',
        Body=explorer_json.encode('utf-8'),
        ContentType='application/json'
    )
    print(f"   explore/explorer.json olusturuldu ({len(articles)} articles)")

# ================= YARDIMCI FONKSIYONLAR =================

def shorten_title(title, max_length=55):
    if len(title) <= max_length:
        return title
    shortened = title[:max_length]
    last_space = shortened.rfind(' ')
    if last_space > 0:
        shortened = shortened[:last_space]
    return shortened + "..."

def sanitize_text(text):
    text = text.replace('ı', 'i')
    text = text.replace('ğ', 'g')
    text = text.replace('ü', 'u')
    text = text.replace('ş', 's')
    text = text.replace('ö', 'o')
    text = text.replace('ç', 'c')
    text = text.replace('İ', 'I')
    text = text.replace('Ğ', 'G')
    text = text.replace('Ü', 'U')
    text = text.replace('Ş', 'S')
    text = text.replace('Ö', 'O')
    text = text.replace('Ç', 'C')
    return text

# ================= HERO TICKER GUNCELLEME (MERGE MANTIGI) =================

def update_hero_ticker():
    print("\n" + "=" * 40)
    print("HERO TICKER GUNCELLENIYOR (MERGE)...")
    print("=" * 40)
    
    articles = get_articles_from_r2()
    if not articles:
        print("   articles.json okunamadi, ticker guncellenemedi.")
        return False
    
    new_ticker_items = {}
    for lang in LANGUAGES:
        lang_articles = [a for a in articles if a.get('lang') == lang]
        sorted_articles = sorted(lang_articles, key=lambda x: x.get('datetime', x.get('date', '')), reverse=True)
        latest = sorted_articles[:6]
        
        items = []
        for a in latest:
            title = a.get('title', 'Untitled')
            short_title = shorten_title(title, 55)
            short_title = sanitize_text(short_title)
            url = a.get('url', '#')
            items.append(f"{short_title} -> {url}")
        
        new_ticker_items[lang] = items
        print(f"   {lang.upper()}: {len(items)} makale hazirlandi")
    
    try:
        response = s3.get_object(Bucket=R2_BUCKET, Key='assets/hero.json')
        hero_data = json.loads(response['Body'].read().decode('utf-8'))
    except Exception as e:
        print(f"   hero.json okunamadi: {e}")
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
            
            new_ticker = {
                "type": "news_ticker",
                "items": new_ticker_items.get(lang, []),
                "grid": "full"
            }
            
            if mevcut_hide_on:
                new_ticker["hide_on"] = mevcut_hide_on
                print(f"   {lang.upper()}: hide_on korundu: {mevcut_hide_on}")
            
            blocks.append(new_ticker)
            hero_data['pages']['home'][lang]['blocks'] = blocks
            
        except KeyError:
            print(f"   {lang.upper()} icin home blogu bulunamadi.")
            continue
    
    hero_data['last_updated'] = datetime.now().isoformat()
    
    try:
        s3.put_object(
            Bucket=R2_BUCKET,
            Key='assets/hero.json',
            Body=json.dumps(hero_data, indent=2, ensure_ascii=False).encode('utf-8'),
            ContentType='application/json'
        )
        print("   hero.json guncellendi (ticker items yenilendi, hide_on korundu)")
        return True
    except Exception as e:
        print(f"   hero.json kaydedilemedi: {e}")
        return False

# ================= HERO STATS GUNCELLEME (MERGE MANTIGI) =================

def update_hero_stats():
    print("\n" + "=" * 40)
    print("HERO STATS GUNCELLENIYOR (MERGE)...")
    print("=" * 40)
    
    articles = get_articles_from_r2()
    if not articles:
        print("   articles.json okunamadi, stats guncellenemedi.")
        return False
    
    lang_counts = {}
    for lang in LANGUAGES:
        count = len([a for a in articles if a.get('lang') == lang])
        lang_counts[lang] = count
        print(f"   {lang.upper()}: {count} makale")
    
    try:
        response = s3.get_object(Bucket=R2_BUCKET, Key='assets/hero.json')
        hero_data = json.loads(response['Body'].read().decode('utf-8'))
    except Exception as e:
        print(f"   hero.json okunamadi: {e}")
        return False
    
    for lang in LANGUAGES:
        try:
            blocks = hero_data['pages']['home'][lang].get('blocks', [])
            total_articles = lang_counts.get(lang, 0)
            
            for block in blocks:
                if block.get('type') == 'description':
                    mevcut_content = block.get('content', '')
                    
                    if '[' in mevcut_content and 'Articles' in mevcut_content:
                        yeni_content = re.sub(r'\[[0-9]+ Articles', f'[{total_articles} Articles', mevcut_content)
                        block['content'] = yeni_content
                        print(f"   {lang.upper()}: makale sayisi guncellendi ({total_articles})")
                    else:
                        print(f"   {lang.upper()}: manuel description korundu")
                    break
            
            hero_data['pages']['home'][lang]['blocks'] = blocks
            
        except KeyError:
            print(f"   {lang.upper()} icin home blogu bulunamadi.")
            continue
    
    hero_data['last_updated'] = datetime.now().isoformat()
    
    try:
        s3.put_object(
            Bucket=R2_BUCKET,
            Key='assets/hero.json',
            Body=json.dumps(hero_data, indent=2, ensure_ascii=False).encode('utf-8'),
            ContentType='application/json'
        )
        print("   hero.json guncellendi (stats yenilendi, manuel description korundu)")
        return True
    except Exception as e:
        print(f"   hero.json kaydedilemedi: {e}")
        return False

# ================= R2 BUCKET ANALIZI =================

def analyze_r2_storage():
    print("\n" + "=" * 40)
    print("R2 BUCKET ANALIZI")
    print("=" * 40)
    
    stats = {
        'html': {'count': 0, 'size': 0},
        'svg': {'count': 0, 'size': 0},
        'webp': {'count': 0, 'size': 0},
        'jpg': {'count': 0, 'size': 0},
        'png': {'count': 0, 'size': 0},
        'json': {'count': 0, 'size': 0},
        'css': {'count': 0, 'size': 0},
        'js': {'count': 0, 'size': 0},
        'other': {'count': 0, 'size': 0}
    }
    
    total_files = 0
    total_size = 0
    continuation_token = None
    
    try:
        while True:
            if continuation_token:
                response = s3.list_objects_v2(
                    Bucket=R2_BUCKET,
                    ContinuationToken=continuation_token
                )
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
                    stats['html']['count'] += 1
                    stats['html']['size'] += size
                elif ext == 'svg':
                    stats['svg']['count'] += 1
                    stats['svg']['size'] += size
                elif ext == 'webp':
                    stats['webp']['count'] += 1
                    stats['webp']['size'] += size
                elif ext in ['jpg', 'jpeg']:
                    stats['jpg']['count'] += 1
                    stats['jpg']['size'] += size
                elif ext == 'png':
                    stats['png']['count'] += 1
                    stats['png']['size'] += size
                elif ext == 'json':
                    stats['json']['count'] += 1
                    stats['json']['size'] += size
                elif ext == 'css':
                    stats['css']['count'] += 1
                    stats['css']['size'] += size
                elif ext == 'js':
                    stats['js']['count'] += 1
                    stats['js']['size'] += size
                else:
                    stats['other']['count'] += 1
                    stats['other']['size'] += size
            
            if response.get('IsTruncated'):
                continuation_token = response.get('NextContinuationToken')
            else:
                break
                
    except Exception as e:
        print(f"Analiz hatasi: {e}")
        return False
    
    print(f"\nToplam dosya: {total_files}")
    print(f"Toplam boyut: {total_size / (1024*1024):.2f} MB")
    print("\n" + "-" * 45)
    print("Dosya turlerine gore dagilim:")
    print("-" * 45)
    
    sorted_stats = sorted(stats.items(), key=lambda x: x[1]['size'], reverse=True)
    
    for type_name, data in sorted_stats:
        if data['count'] > 0:
            mb = data['size'] / (1024*1024)
            percent = (data['size'] / total_size * 100) if total_size > 0 else 0
            print(f"   {type_name.upper():8} | {data['count']:6} dosya | {mb:8.2f} MB | %{percent:5.1f}")
    
    print("-" * 45)
    
    return True

# ================= ANA LIBRARIAN =================

def librarian():
    print("\n" + "=" * 60)
    print("KUTUPHANECI BOT (Librarian) - MERGE MANTIGI")
    print("   explore/explorer.json olusturuluyor")
    print("   hero.json ticker guncelleniyor (hide_on korunuyor)")
    print("   hero.json stats guncelleniyor (manuel description korunuyor)")
    print("   Atomic swap: articles_ready/ -> articles/")
    print("=" * 60)
    
    analyze_r2_storage()
    
    articles = get_articles_from_r2()
    if articles:
        print(f"\nToplam {len(articles)} makale bulundu.")
        generate_explorer_json(articles)
    else:
        print("\narticles.json okunamadi, explorer.json atlaniyor.")
    
    update_hero_ticker()
    update_hero_stats()
    
    try:
        swap_success = atomic_swap()
        if swap_success:
            print("\nSWAP BASARILI! Site yeni icerikle yayinda.")
        else:
            print("\nSWAP BASARISIZ! Site eski icerikle devam ediyor.")
            sys.exit(1)
    except Exception as e:
        print(f"\nKRITIK HATA: {e}")
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("KUTUPHANECI BOT TAMAMLANDI!")
    print("   explore/explorer.json guncellendi")
    print("   hero.json ticker guncellendi (hide_on korundu)")
    print("   hero.json stats guncellendi (manuel description korundu)")
    print("   Atomic swap tamamlandi")
    print("=" * 60)

if __name__ == "__main__":
    librarian()
