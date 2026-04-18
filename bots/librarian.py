import os
import json
import sys
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

# Dil konfigürasyonu
LANGUAGES = ['en', 'es', 'de', 'fr']
LANG_NAMES = {
    'en': 'English', 'es': 'Español', 'de': 'Deutsch', 'fr': 'Français'
}
LANG_FLAGS = {
    'en': '🇺🇸', 'es': '🇪🇸', 'de': '🇩🇪', 'fr': '🇫🇷'
}

CATEGORIES = {
    'tech': {'en': 'Technology & AI', 'es': 'Tecnología & IA', 'de': 'Technologie & KI', 'fr': 'Technologie & IA'},
    'wellness': {'en': 'Wellness', 'es': 'Bienestar', 'de': 'Wohlbefinden', 'fr': 'Bien-être'},
    'future-economy': {'en': 'Future Economy', 'es': 'Economía Futura', 'de': 'ZukunftsWirtschaft', 'fr': 'Économie Future'},
    'eco': {'en': 'Eco & Sustainable', 'es': 'Eco & Sostenible', 'de': 'Öko & Nachhaltig', 'fr': 'Éco & Durable'},
    'elearning': {'en': 'E-Learning', 'es': 'E-Aprendizaje', 'de': 'E-Learning', 'fr': 'E-Apprentissage'}
}

# ================= R2 YARDIMCI FONKSİYONLAR =================

def list_all_files(prefix):
    """R2'deki tüm dosyaları listeler"""
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
            print(f"   ❌ Listeleme hatası: {e}")
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
    """R2'de klasör var mı (içinde en az 1 dosya var mı)"""
    try:
        response = s3.list_objects_v2(Bucket=R2_BUCKET, Prefix=prefix, MaxKeys=1)
        return 'Contents' in response
    except:
        return False

def delete_folder(prefix):
    """R2'de bir klasörün içindeki tüm dosyaları sil"""
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
            print(f"   ❌ Listeleme hatası: {e}")
            raise
        
        if 'Contents' not in response:
            break
        
        objects_to_delete = [{'Key': obj['Key']} for obj in response['Contents']]
        try:
            s3.delete_objects(Bucket=R2_BUCKET, Delete={'Objects': objects_to_delete})
            deleted_count += len(objects_to_delete)
        except Exception as e:
            print(f"   ❌ Silme hatası: {e}")
            raise
        
        if response.get('IsTruncated'):
            continuation_token = response.get('NextContinuationToken')
        else:
            break
    
    if deleted_count > 0:
        print(f"   🗑️ {deleted_count} dosya silindi: {prefix}")

def copy_and_overwrite(source_key, dest_key):
    """Tek bir dosyayı üzerine yazar (parallel için)"""
    try:
        response = s3.get_object(Bucket=R2_BUCKET, Key=source_key)
        content = response['Body'].read()
        s3.put_object(Bucket=R2_BUCKET, Key=dest_key, Body=content, ContentType='text/html')
        return True
    except Exception as e:
        print(f"   ⚠️ {source_key} -> {dest_key} yazılamadı: {e}")
        return False

# ================= ATOMIC SWAP =================

def atomic_swap():
    """
    articles_ready/ → articles/ OPTİMİZE swap
    """
    print("\n" + "=" * 40)
    print("🔄 ATOMIC SWAP: articles_ready/ → articles/")
    print("=" * 40)
    
    if not folder_exists('articles_ready/'):
        print("❌ articles_ready/ bulunamadı! Swap iptal.")
        return False
    
    print("📁 articles_ready/ içindeki dosyalar listeleniyor...")
    source_files = list_all_files('articles_ready/')
    
    if not source_files:
        print("⚠️ articles_ready/ boş, swap iptal.")
        return False
    
    print(f"   📄 {len(source_files)} dosya bulundu.")
    print(f"🚀 {len(source_files)} dosya parallel yazılıyor (10 thread)...")
    
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
    
    print(f"   ✅ {success_count}/{len(source_files)} dosya başarıyla yazıldı")
    
    if success_count < len(source_files) * 0.9:
        print(f"❌ Çok fazla hata ({success_count}/{len(source_files)} başarılı)")
        return False
    
    print("🗑️ articles_ready/ siliniyor...")
    delete_folder('articles_ready/')
    
    print("✅ Swap tamamlandı!")
    return True

# ================= JSON ÜRETİMİ =================

def get_articles_from_r2():
    """articles.json'u okur"""
    try:
        response = s3.get_object(Bucket=R2_BUCKET, Key='articles.json')
        return json.loads(response['Body'].read().decode('utf-8'))
    except Exception as e:
        print(f"⚠️ articles.json okunamadı: {e}")
        return []

def generate_explorer_json(articles):
    """Sadece JSON verisi üretir"""
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
    print(f"   ✅ explore/explorer.json oluşturuldu ({len(articles)} articles)")

# ================= YENİ: HERO TICKER GÜNCELLEME =================

def shorten_title(title, max_length=55):
    """Başlığı kısalt, son kelimeyi bozma"""
    if len(title) <= max_length:
        return title
    shortened = title[:max_length]
    last_space = shortened.rfind(' ')
    if last_space > 0:
        shortened = shortened[:last_space]
    return shortened + "..."

def update_hero_ticker():
    """
    articles.json'dan son 6 makaleyi al,
    hero.json'daki news_ticker items'larını günceller
    """
    print("\n" + "=" * 40)
    print("🔄 HERO TICKER GÜNCELLENİYOR...")
    print("=" * 40)
    
    articles = get_articles_from_r2()
    if not articles:
        print("   ⚠️ articles.json okunamadı, ticker güncellenemedi.")
        return False
    
    new_ticker_items = {}
    
    for lang in LANGUAGES:
        lang_articles = [a for a in articles if a.get('lang') == lang]
        
        def get_sort_key(article):
            return article.get('datetime', article.get('date', ''))
        
        sorted_articles = sorted(lang_articles, key=get_sort_key, reverse=True)
        latest = sorted_articles[:6]
        
        items = []
        for a in latest:
            title = a.get('title', 'Untitled')
            short_title = shorten_title(title, 55)
            url = a.get('url', '#')
            items.append(f"{short_title} → {url}")
        
        new_ticker_items[lang] = items
        print(f"   📝 {lang.upper()}: {len(items)} makale eklendi")
    
    try:
        response = s3.get_object(Bucket=R2_BUCKET, Key='templates/hero.json')
        hero_data = json.loads(response['Body'].read().decode('utf-8'))
    except Exception as e:
        print(f"   ❌ hero.json okunamadı: {e}")
        return False
    
    for lang in LANGUAGES:
        try:
            blocks = hero_data['pages']['home'][lang].get('blocks', [])
            blocks = [block for block in blocks if block.get('type') != 'news_ticker']
            blocks.append({
                "type": "news_ticker",
                "items": new_ticker_items.get(lang, []),
                "grid": "full"
            })
            hero_data['pages']['home'][lang]['blocks'] = blocks
        except KeyError:
            print(f"   ⚠️ {lang.upper()} için home bloğu bulunamadı, atlanıyor.")
            continue
    
    hero_data['last_updated'] = datetime.now().isoformat()
    
    try:
        s3.put_object(
            Bucket=R2_BUCKET,
            Key='templates/hero.json',
            Body=json.dumps(hero_data, indent=2, ensure_ascii=False).encode('utf-8'),
            ContentType='application/json'
        )
        print("   ✅ hero.json güncellendi (ticker items yenilendi)")
        return True
    except Exception as e:
        print(f"   ❌ hero.json kaydedilemedi: {e}")
        return False

# ================= YENİ: HERO STATS GÜNCELLEME =================

def update_hero_stats():
    """
    articles.json'dan toplam makale sayısını al,
    hero.json'daki description içindeki makale sayısını günceller
    """
    print("\n" + "=" * 40)
    print("🔄 HERO STATS GÜNCELLENİYOR...")
    print("=" * 40)
    
    articles = get_articles_from_r2()
    if not articles:
        print("   ⚠️ articles.json okunamadı, stats güncellenemedi.")
        return False
    
    # Her dil için toplam makale sayısını hesapla
    lang_counts = {}
    for lang in LANGUAGES:
        count = len([a for a in articles if a.get('lang') == lang])
        lang_counts[lang] = count
    
    try:
        response = s3.get_object(Bucket=R2_BUCKET, Key='templates/hero.json')
        hero_data = json.loads(response['Body'].read().decode('utf-8'))
    except Exception as e:
        print(f"   ❌ hero.json okunamadı: {e}")
        return False
    
    # Her dil için description'ı güncelle
    for lang in LANGUAGES:
        try:
            blocks = hero_data['pages']['home'][lang].get('blocks', [])
            total_articles = lang_counts.get(lang, 0)
            
            # Yeni description metni
            new_description = f"Tech & AI · Future Economy\nWellness · Eco & Sustainable\nE-Learning\n📚 {total_articles}+ Articles in 5 languages"
            
            # Description bloğunu bul ve güncelle
            for block in blocks:
                if block.get('type') == 'description':
                    block['content'] = new_description
                    break
            
            hero_data['pages']['home'][lang]['blocks'] = blocks
            print(f"   📝 {lang.upper()}: {total_articles} makale")
            
        except KeyError:
            print(f"   ⚠️ {lang.upper()} için home bloğu bulunamadı, atlanıyor.")
            continue
    
    hero_data['last_updated'] = datetime.now().isoformat()
    
    try:
        s3.put_object(
            Bucket=R2_BUCKET,
            Key='templates/hero.json',
            Body=json.dumps(hero_data, indent=2, ensure_ascii=False).encode('utf-8'),
            ContentType='application/json'
        )
        print("   ✅ hero.json güncellendi (stats yenilendi)")
        return True
    except Exception as e:
        print(f"   ❌ hero.json kaydedilemedi: {e}")
        return False

# ================= ANA LİBRARIAN =================

def librarian():
    print("\n" + "=" * 60)
    print("📚 KÜTÜPHANECİ BOT (Librarian)")
    print("   ✅ explore/explorer.json oluşturuluyor")
    print("   ✅ hero.json ticker güncelleniyor")
    print("   ✅ hero.json stats güncelleniyor")
    print("   ✅ Atomic swap: articles_ready/ → articles/")
    print("=" * 60)
    
    # 1. explore/explorer.json oluştur
    articles = get_articles_from_r2()
    if articles:
        print(f"\n📊 Toplam {len(articles)} makale bulundu.")
        generate_explorer_json(articles)
    else:
        print("\n⚠️ articles.json okunamadı, explorer.json atlanıyor.")
    
    # 2. hero.json'daki ticker items'larını güncelle
    update_hero_ticker()
    
    # 3. hero.json'daki stats (makale sayısı) güncelle
    update_hero_stats()
    
    # 4. Atomic swap yap
    try:
        swap_success = atomic_swap()
        if swap_success:
            print("\n✅ SWAP BAŞARILI! Site yeni içerikle yayında.")
        else:
            print("\n❌ SWAP BAŞARISIZ! Site eski içerikle devam ediyor.")
            sys.exit(1)
    except Exception as e:
        print(f"\n❌ KRİTİK HATA: {e}")
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("🏁 KÜTÜPHANECİ BOT TAMAMLANDI!")
    print("   ✅ explore/explorer.json güncellendi")
    print("   ✅ hero.json ticker güncellendi")
    print("   ✅ hero.json stats güncellendi")
    print("   ✅ Atomic swap tamamlandı")
    print("=" * 60)

if __name__ == "__main__":
    librarian()
