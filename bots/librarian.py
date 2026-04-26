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
MIN_SIZE_KB = 51

s3 = boto3.client(
    's3',
    endpoint_url=f'https://{R2_ID}.r2.cloudflarestorage.com',
    aws_access_key_id=R2_ACCESS_KEY,
    aws_secret_access_key=R2_SECRET_KEY,
    config=Config(signature_version='s3v4'),
    region_name='auto'
)

LANGUAGES = ['en', 'es', 'de', 'fr']

def list_all_files(prefix):
    files = []
    continuation_token = None
    while True:
        try:
            if continuation_token:
                response = s3.list_objects_v2(Bucket=R2_BUCKET, Prefix=prefix, ContinuationToken=continuation_token)
            else:
                response = s3.list_objects_v2(Bucket=R2_BUCKET, Prefix=prefix)
        except Exception as e:
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

def delete_file(key):
    try:
        s3.delete_object(Bucket=R2_BUCKET, Key=key)
        return True
    except Exception as e:
        print(f"   Silme hatasi {key}: {e}")
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
    except Exception as e:
        return False

def log_size_report(entries, report_type="librarian"):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_key = f"reports/size_report_{report_type}_{timestamp}.json"
    report = {
        "generated": datetime.now().isoformat(),
        "type": report_type,
        "min_size_kb": MIN_SIZE_KB,
        "entries": entries
    }
    try:
        s3.put_object(Bucket=R2_BUCKET, Key=report_key,
                      Body=json.dumps(report, indent=2, ensure_ascii=False).encode('utf-8'),
                      ContentType='application/json')
        print(f"   📊 Rapor kaydedildi: {report_key}")
        return report_key
    except Exception as e:
        print(f"   ⚠️ Rapor kaydedilemedi: {e}")
        return None

def check_existing_articles():
    """Mevcut articles/ klasöründeki dosyaları kontrol et, küçükleri sil (yayından kaldır)"""
    print("\n" + "=" * 40)
    print("🔍 MEVCUT ARTICLES/ KONTROLÜ (51 KB altı silinecek)")
    print("=" * 40)
    
    articles_files = list_all_files('articles/')
    if not articles_files:
        print("   articles/ klasörü boş veya yok.")
        return []
    
    small_files = []
    for key in articles_files:
        if not key.endswith('.html'):
            continue
        try:
            response = s3.head_object(Bucket=R2_BUCKET, Key=key)
            size_kb = response['ContentLength'] / 1024
            if size_kb < MIN_SIZE_KB:
                small_files.append({
                    "timestamp": datetime.now().isoformat(),
                    "source": "librarian_existing",
                    "status": "DELETED_FROM_ARTICLES",
                    "key": key,
                    "size_kb": round(size_kb, 2),
                    "min_required_kb": MIN_SIZE_KB
                })
                delete_file(key)
                print(f"   🗑️ Yayından kaldırıldı: {key} ({size_kb:.1f} KB)")
        except Exception as e:
            print(f"   ⚠️ {key} okunamadı: {e}")
    
    if small_files:
        log_size_report(small_files, "librarian_existing")
        print(f"   🗑️ Toplam {len(small_files)} hatalı makale yayından kaldırıldı")
    else:
        print("   ✅ Mevcut tüm makaleler 51 KB üzerinde")
    
    return small_files

def atomic_swap():
    """Swap öncesi kontrol + swap + sonrası rapor"""
    print("\n" + "=" * 40)
    print("ATOMIC SWAP: articles_ready/ -> articles/ (51 KB KONTROLLÜ)")
    print("=" * 40)
    
    if not folder_exists('articles_ready/'):
        print("articles_ready/ bulunamadi! Swap iptal.")
        return False
    
    source_files = list_all_files('articles_ready/')
    if not source_files:
        print("articles_ready/ bos, swap iptal.")
        return False
    
    print(f"   {len(source_files)} dosya bulundu.")
    
    # 1. KONTROL: articles_ready/ içindeki dosyaları boyut kontrolü yap
    small_in_ready = []
    valid_files = []
    
    for key in source_files:
        if not key.endswith('.html'):
            valid_files.append(key)
            continue
        try:
            response = s3.head_object(Bucket=R2_BUCKET, Key=key)
            size_kb = response['ContentLength'] / 1024
            if size_kb < MIN_SIZE_KB:
                small_in_ready.append({
                    "timestamp": datetime.now().isoformat(),
                    "source": "librarian_swap_precheck",
                    "status": "REJECTED_FROM_SWAP",
                    "key": key,
                    "size_kb": round(size_kb, 2),
                    "min_required_kb": MIN_SIZE_KB
                })
                print(f"   ⚠️ SWAP DIŞI: {key} ({size_kb:.1f} KB) - Yayınlanmayacak")
            else:
                valid_files.append(key)
        except Exception as e:
            print(f"   ⚠️ {key} okunamadı: {e}")
            valid_files.append(key)
    
    # Rapor kaydet (swap öncesi)
    if small_in_ready:
        log_size_report(small_in_ready, "librarian_swap_precheck")
        print(f"   ⚠️ {len(small_in_ready)} dosya swap DIŞI bırakıldı (51 KB altı)")
    
    if not valid_files:
        print("   ❌ Swap için geçerli dosya kalmadı!")
        return False
    
    print(f"   ✅ {len(valid_files)} dosya swap için uygun (≥{MIN_SIZE_KB} KB)")
    
    # 2. SWAP İŞLEMİ (sadece valid_files)
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
    
    # 3. TEMİZLİK: articles_ready/ SİL
    print("   articles_ready/ siliniyor...")
    delete_folder('articles_ready/')
    
    print("   ✅ Swap tamamlandi!")
    return True

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
    
    new_ticker_items = {}
    for lang in LANGUAGES:
        lang_articles = [a for a in articles if a.get('lang') == lang and a.get('cover_image')]
        lang_articles.sort(key=lambda x: x.get('datetime', x.get('date', '')), reverse=True)
        latest = lang_articles[:6]
        items = []
        for a in latest:
            title = a.get('title', 'Untitled')
            title = title[:55] + "..." if len(title) > 55 else title
            title = title.replace('ı', 'i').replace('ğ', 'g').replace('ü', 'u').replace('ş', 's').replace('ö', 'o').replace('ç', 'c')
            url = a.get('url', '#')
            items.append(f"{title} -> {url}")
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
    s3.put_object(Bucket=R2_BUCKET, Key='assets/hero.json',
                  Body=json.dumps(hero_data, indent=2, ensure_ascii=False).encode('utf-8'),
                  ContentType='application/json')
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
                    break
            hero_data['pages']['home'][lang]['blocks'] = blocks
        except KeyError:
            continue
    
    s3.put_object(Bucket=R2_BUCKET, Key='assets/hero.json',
                  Body=json.dumps(hero_data, indent=2, ensure_ascii=False).encode('utf-8'),
                  ContentType='application/json')
    print("   hero.json stats guncellendi")
    return True

def analyze_r2_storage():
    print("\n" + "=" * 40)
    print("R2 BUCKET ANALIZI")
    print("=" * 40)
    stats = {'html': {'count': 0, 'size': 0}, 'svg': {'count': 0, 'size': 0},
             'webp': {'count': 0, 'size': 0}, 'jpg': {'count': 0, 'size': 0},
             'png': {'count': 0, 'size': 0}, 'json': {'count': 0, 'size': 0},
             'css': {'count': 0, 'size': 0}, 'js': {'count': 0, 'size': 0},
             'other': {'count': 0, 'size': 0}}
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
                if ext in ['html', 'htm']: stats['html']['count'] += 1; stats['html']['size'] += size
                elif ext == 'svg': stats['svg']['count'] += 1; stats['svg']['size'] += size
                elif ext == 'webp': stats['webp']['count'] += 1; stats['webp']['size'] += size
                elif ext in ['jpg', 'jpeg']: stats['jpg']['count'] += 1; stats['jpg']['size'] += size
                elif ext == 'png': stats['png']['count'] += 1; stats['png']['size'] += size
                elif ext == 'json': stats['json']['count'] += 1; stats['json']['size'] += size
                elif ext == 'css': stats['css']['count'] += 1; stats['css']['size'] += size
                elif ext == 'js': stats['js']['count'] += 1; stats['js']['size'] += size
                else: stats['other']['count'] += 1; stats['other']['size'] += size
            if response.get('IsTruncated'): continuation_token = response.get('NextContinuationToken')
            else: break
    except Exception as e:
        print(f"Analiz hatasi: {e}")
        return False
    print(f"\nToplam dosya: {total_files}")
    print(f"Toplam boyut: {total_size / (1024*1024):.2f} MB")
    return True

def librarian():
    print("\n" + "=" * 60)
    print("📚 KUTUPHANECI BOT v20 - 51 KB KONTROLLÜ")
    print("   🔍 Mevcut articles/ kontrolü (küçükler SİLİNECEK)")
    print("   🛡️ Swap öncesi articles_ready/ kontrolü (küçükler YAYINLANMAYACAK)")
    print("   📊 Detaylı rapor (R2/reports/)")
    print("=" * 60)
    
    analyze_r2_storage()
    
    # 1. MEVCUT ARTICLES/ KONTROLÜ (Yayından kaldır)
    deleted_articles = check_existing_articles()
    
    # 2. HERO GÜNCELLEMELERİ
    update_hero_ticker()
    update_hero_stats()
    
    # 3. ATOMIC SWAP (Kontrollü)
    try:
        swap_success = atomic_swap()
        if swap_success:
            print("\n✅ SWAP BASARILI! Site yeni icerikle yayinda.")
        else:
            print("\n⚠️ SWAP BASARISIZ! Site eski icerikle devam ediyor.")
    except Exception as e:
        print(f"\n❌ KRITIK HATA: {e}")
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("🏁 KUTUPHANECI BOT v20 TAMAMLANDI!")
    if deleted_articles:
        print(f"   🗑️ Yayından kaldırılan: {len(deleted_articles)} makale")
    print("=" * 60)

if __name__ == "__main__":
    librarian()
