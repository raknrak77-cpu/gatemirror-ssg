import os
import json
import sys
import boto3
from collections import defaultdict
from datetime import datetime
from botocore.client import Config

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

CATEGORIES = {
    'tech': {'en': 'Technology & AI', 'es': 'Tecnología & IA', 'de': 'Technologie & KI', 'fr': 'Technologie & IA'},
    'wellness': {'en': 'Wellness', 'es': 'Bienestar', 'de': 'Wohlbefinden', 'fr': 'Bien-être'},
    'future-economy': {'en': 'Future Economy', 'es': 'Economía Futura', 'de': 'ZukunftsWirtschaft', 'fr': 'Économie Future'},
    'eco': {'en': 'Eco & Sustainable', 'es': 'Eco & Sostenible', 'de': 'Öko & Nachhaltig', 'fr': 'Éco & Durable'},
    'elearning': {'en': 'E-Learning', 'es': 'E-Aprendizaje', 'de': 'E-Learning', 'fr': 'E-Apprentissage'}
}

# ================= R2 YARDIMCI FONKSİYONLAR =================

def folder_exists(prefix):
    """R2'de klasör var mı (içinde en az 1 dosya var mı)"""
    try:
        response = s3.list_objects_v2(Bucket=R2_BUCKET, Prefix=prefix, MaxKeys=1)
        return 'Contents' in response
    except:
        return False

def copy_folder(source_prefix, dest_prefix):
    """R2'de bir klasörün içindeki tüm dosyaları başka klasöre kopyala"""
    continuation_token = None
    copied_count = 0
    
    while True:
        try:
            if continuation_token:
                response = s3.list_objects_v2(
                    Bucket=R2_BUCKET, 
                    Prefix=source_prefix,
                    ContinuationToken=continuation_token
                )
            else:
                response = s3.list_objects_v2(Bucket=R2_BUCKET, Prefix=source_prefix)
        except Exception as e:
            print(f"   ❌ Listeleme hatası: {e}")
            raise
        
        if 'Contents' not in response:
            break
        
        for obj in response['Contents']:
            source_key = obj['Key']
            dest_key = source_key.replace(source_prefix, dest_prefix, 1)
            
            try:
                copy_source = {'Bucket': R2_BUCKET, 'Key': source_key}
                s3.copy_object(CopySource=copy_source, Bucket=R2_BUCKET, Key=dest_key)
                copied_count += 1
            except Exception as e:
                print(f"   ❌ Kopyalama hatası: {source_key} -> {dest_key}: {e}")
                raise
        
        if response.get('IsTruncated'):
            continuation_token = response.get('NextContinuationToken')
        else:
            break
    
    print(f"   📁 {copied_count} dosya kopyalandı: {source_prefix} → {dest_prefix}")

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
    
    print(f"   🗑️ {deleted_count} dosya silindi: {prefix}")

def atomic_swap():
    """
    articles_ready/ → articles/ atomik swap işlemi
    Eğer başarısız olursa hata fırlatır (SEIÇARIZ)
    """
    print("\n" + "=" * 40)
    print("🔄 ATOMIC SWAP: articles_ready/ → articles/")
    print("=" * 40)
    
    # 1. articles_ready/ var mı kontrol et
    if not folder_exists('articles_ready/'):
        print("❌ articles_ready/ bulunamadı! Swap iptal.")
        return False
    
    # 2. articles/ varsa backup al
    if folder_exists('articles/'):
        print("📦 articles/ → articles_backup/ kopyalanıyor...")
        copy_folder('articles/', 'articles_backup/')
        print("✅ Backup alındı")
    
    # 3. articles_ready/ → articles/ kopyala
    print("🚀 articles_ready/ → articles/ kopyalanıyor...")
    copy_folder('articles_ready/', 'articles/')
    print("✅ Yeni sürüm aktif!")
    
    # 4. Backup'ı sil
    if folder_exists('articles_backup/'):
        print("🗑️ articles_backup/ siliniyor...")
        delete_folder('articles_backup/')
        print("✅ Backup temizlendi")
    
    # 5. articles_ready/ temizle
    print("🗑️ articles_ready/ siliniyor...")
    delete_folder('articles_ready/')
    print("✅ Swap tamamlandı!")
    
    return True

# ================= MEVCUT LİBRARIAN FONKSİYONLARI =================

def get_articles_from_r2():
    try:
        response = s3.get_object(Bucket=R2_BUCKET, Key='articles.json')
        return json.loads(response['Body'].read().decode('utf-8'))
    except Exception as e:
        print(f"⚠️ articles.json okunamadı: {e}")
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
    print(f"   ✅ explore/explorer.json oluşturuldu ({len(articles)} articles)")

def generate_all_articles_page(articles, lang):
    lang_articles = [a for a in articles if a.get('lang') == lang]
    lang_articles.sort(key=lambda x: x.get('sort_date', ''), reverse=True)
    lang_name = LANG_NAMES.get(lang, 'English')
    
    lang_switch = ''
    for l in LANGUAGES:
        active_class = 'active' if l == lang else ''
        lang_switch += f'<a href="/explore/all-articles/{l}.html" class="lang-btn {active_class}">{"🇺🇸 " + LANG_NAMES[l] if l == "en" else " " + LANG_NAMES[l]}</a>'
    
    html = f'''<!DOCTYPE html>
<html lang="{lang}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>All Articles | Gatemirror ({lang_name})</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0a0a0a; color: #e0e0e0; line-height: 1.6; padding: 2rem; }}
        .container {{ max-width: 800px; margin: 0 auto; }}
        h1 {{ color: #2ecc71; margin-bottom: 0.5rem; }}
        .subtitle {{ color: #888; margin-bottom: 2rem; border-bottom: 1px solid #333; padding-bottom: 1rem; }}
        .back-link {{ display: inline-block; margin-bottom: 2rem; color: #2ecc71; text-decoration: none; }}
        .back-link:hover {{ text-decoration: underline; }}
        .lang-switch {{ margin-bottom: 2rem; display: flex; gap: 1rem; flex-wrap: wrap; }}
        .lang-btn {{ background: #1a1a1a; padding: 0.25rem 0.75rem; border-radius: 1rem; color: #888; text-decoration: none; font-size: 0.8rem; }}
        .lang-btn.active {{ background: #2ecc71; color: #0a0a0a; }}
        .article-list {{ list-style: none; }}
        .article-item {{ background: #1a1a1a; margin-bottom: 1rem; border-radius: 0.5rem; transition: transform 0.2s; }}
        .article-item:hover {{ transform: translateX(4px); }}
        .article-link {{ display: block; padding: 1rem; text-decoration: none; color: inherit; }}
        .article-title {{ font-size: 1.1rem; font-weight: 600; margin-bottom: 0.25rem; color: #fff; }}
        .article-meta {{ font-size: 0.8rem; color: #888; }}
        .article-meta span {{ margin-right: 1rem; }}
        footer {{ margin-top: 3rem; text-align: center; color: #555; font-size: 0.8rem; }}
        a {{ color: #2ecc71; }}
    </style>
</head>
<body>
    <div class="container">
        <a href="/" class="back-link">← Home</a>
        <h1>📚 All Articles ({lang_name})</h1>
        <div class="lang-switch">{lang_switch}</div>
        <div class="subtitle">{len(lang_articles)} articles</div>
        <ul class="article-list">
'''
    for article in lang_articles:
        html += f'''
            <li class="article-item">
                <a href="{article.get('url', '#')}" class="article-link">
                    <div class="article-title">{article.get('title', 'Untitled')}</div>
                    <div class="article-meta">
                        <span>📅 {article.get('date', '')}</span>
                        <span>⏱️ {article.get('reading_time', '')} min read</span>
                        <span>👁️ {article.get('views', '')} views</span>
                    </div>
                </a>
            </li>
'''
    html += '''
        </ul>
        <footer>
            <p>Gatemirror — Global insights on Tech, Wellness & Future Economy</p>
        </footer>
    </div>
</body>
</html>'''
    
    s3.put_object(Bucket=R2_BUCKET, Key=f"explore/all-articles/{lang}.html", Body=html.encode('utf-8'), ContentType='text/html')
    print(f"   ✅ explore/all-articles/{lang}.html ({len(lang_articles)} articles)")

def generate_categories_page(articles, lang):
    lang_articles = [a for a in articles if a.get('lang') == lang]
    category_articles = {cat: [] for cat in CATEGORIES}
    for article in lang_articles:
        cat = article.get('category', '')
        if cat in category_articles:
            category_articles[cat].append(article)
    
    for cat in category_articles:
        category_articles[cat].sort(key=lambda x: x.get('sort_date', ''), reverse=True)
    
    lang_name = LANG_NAMES.get(lang, 'English')
    
    lang_switch = ''
    for l in LANGUAGES:
        active_class = 'active' if l == lang else ''
        lang_switch += f'<a href="/explore/categories/{l}.html" class="lang-btn {active_class}">{"🇺🇸 " + LANG_NAMES[l] if l == "en" else " " + LANG_NAMES[l]}</a>'
    
    html = f'''<!DOCTYPE html>
<html lang="{lang}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Categories | Gatemirror ({lang_name})</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0a0a0a; color: #e0e0e0; line-height: 1.6; padding: 2rem; }}
        .container {{ max-width: 1000px; margin: 0 auto; }}
        h1 {{ color: #2ecc71; margin-bottom: 0.5rem; }}
        .subtitle {{ color: #888; margin-bottom: 2rem; border-bottom: 1px solid #333; padding-bottom: 1rem; }}
        .back-link {{ display: inline-block; margin-bottom: 2rem; color: #2ecc71; text-decoration: none; }}
        .back-link:hover {{ text-decoration: underline; }}
        .lang-switch {{ margin-bottom: 2rem; display: flex; gap: 1rem; flex-wrap: wrap; }}
        .lang-btn {{ background: #1a1a1a; padding: 0.25rem 0.75rem; border-radius: 1rem; color: #888; text-decoration: none; font-size: 0.8rem; }}
        .lang-btn.active {{ background: #2ecc71; color: #0a0a0a; }}
        .category-section {{ margin-bottom: 3rem; }}
        .category-title {{ font-size: 1.8rem; color: #2ecc71; margin-bottom: 1rem; border-left: 4px solid #2ecc71; padding-left: 1rem; }}
        .article-list {{ list-style: none; }}
        .article-item {{ background: #1a1a1a; margin-bottom: 0.75rem; border-radius: 0.5rem; transition: transform 0.2s; }}
        .article-item:hover {{ transform: translateX(4px); }}
        .article-link {{ display: block; padding: 0.75rem 1rem; text-decoration: none; color: inherit; }}
        .article-title {{ font-size: 1rem; font-weight: 500; color: #fff; }}
        .article-meta {{ font-size: 0.75rem; color: #888; margin-top: 0.25rem; }}
        .empty-category {{ background: #1a1a1a; padding: 1rem; border-radius: 0.5rem; text-align: center; color: #666; }}
        .more-link {{ margin-top: 0.5rem; text-align: right; }}
        .more-link a {{ color: #2ecc71; font-size: 0.85rem; text-decoration: none; }}
        footer {{ margin-top: 3rem; text-align: center; color: #555; font-size: 0.8rem; }}
        a {{ color: #2ecc71; }}
    </style>
</head>
<body>
    <div class="container">
        <a href="/" class="back-link">← Home</a>
        <h1>📂 Categories ({lang_name})</h1>
        <div class="lang-switch">{lang_switch}</div>
        <div class="subtitle">Browse articles by category</div>
'''
    for cat_key, cat_names in CATEGORIES.items():
        cat_name = cat_names.get(lang, cat_names['en'])
        cat_arts = category_articles.get(cat_key, [])
        html += f'''
        <div class="category-section">
            <h2 class="category-title">{cat_name}</h2>
            <ul class="article-list">
'''
        if cat_arts:
            for article in cat_arts[:8]:
                html += f'''
                <li class="article-item">
                    <a href="{article.get('url', '#')}" class="article-link">
                        <div class="article-title">{article.get('title', 'Untitled')}</div>
                        <div class="article-meta">📅 {article.get('date', '')}</div>
                    </a>
                </li>
'''
            if len(cat_arts) > 8:
                html += f'''
                <div class="more-link">
                    <a href="/explore/category-archive/{lang}/{cat_key}/">+ {len(cat_arts) - 8} more in {cat_name} →</a>
                </div>
'''
        else:
            html += '<div class="empty-category">No articles yet</div>'
        html += '''
            </ul>
        </div>
'''
    html += '''
        <footer>
            <p>Gatemirror — Global insights on Tech, Wellness & Future Economy</p>
        </footer>
    </div>
</body>
</html>'''
    
    s3.put_object(Bucket=R2_BUCKET, Key=f"explore/categories/{lang}.html", Body=html.encode('utf-8'), ContentType='text/html')
    print(f"   ✅ explore/categories/{lang}.html")

def generate_category_archives(articles, lang):
    lang_articles = [a for a in articles if a.get('lang') == lang]
    category_articles = {cat: [] for cat in CATEGORIES}
    for article in lang_articles:
        cat = article.get('category', '')
        if cat in category_articles:
            category_articles[cat].append(article)
    
    for cat_key, cat_names in CATEGORIES.items():
        cat_arts = category_articles.get(cat_key, [])
        cat_arts.sort(key=lambda x: x.get('sort_date', ''), reverse=True)
        cat_name = cat_names.get(lang, cat_names['en'])
        lang_name = LANG_NAMES.get(lang, 'English')
        
        lang_switch = ''
        for l in LANGUAGES:
            active_class = 'active' if l == lang else ''
            lang_switch += f'<a href="/explore/category-archive/{l}/{cat_key}/" class="lang-btn {active_class}">{"🇺🇸 " + LANG_NAMES[l] if l == "en" else " " + LANG_NAMES[l]}</a>'
        
        if cat_arts:
            html = f'''<!DOCTYPE html>
<html lang="{lang}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{cat_name} Archive | Gatemirror ({lang_name})</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0a0a0a; color: #e0e0e0; line-height: 1.6; padding: 2rem; }}
        .container {{ max-width: 800px; margin: 0 auto; }}
        h1 {{ color: #2ecc71; margin-bottom: 0.5rem; }}
        .subtitle {{ color: #888; margin-bottom: 2rem; border-bottom: 1px solid #333; padding-bottom: 1rem; }}
        .back-link {{ display: inline-block; margin-bottom: 2rem; color: #2ecc71; text-decoration: none; }}
        .back-link:hover {{ text-decoration: underline; }}
        .lang-switch {{ margin-bottom: 2rem; display: flex; gap: 1rem; flex-wrap: wrap; }}
        .lang-btn {{ background: #1a1a1a; padding: 0.25rem 0.75rem; border-radius: 1rem; color: #888; text-decoration: none; font-size: 0.8rem; }}
        .lang-btn.active {{ background: #2ecc71; color: #0a0a0a; }}
        .article-list {{ list-style: none; }}
        .article-item {{ background: #1a1a1a; margin-bottom: 1rem; border-radius: 0.5rem; transition: transform 0.2s; }}
        .article-item:hover {{ transform: translateX(4px); }}
        .article-link {{ display: block; padding: 1rem; text-decoration: none; color: inherit; }}
        .article-title {{ font-size: 1.1rem; font-weight: 600; margin-bottom: 0.25rem; color: #fff; }}
        .article-meta {{ font-size: 0.8rem; color: #888; }}
        .article-meta span {{ margin-right: 1rem; }}
        footer {{ margin-top: 3rem; text-align: center; color: #555; font-size: 0.8rem; }}
        a {{ color: #2ecc71; }}
    </style>
</head>
<body>
    <div class="container">
        <a href="/" class="back-link">← Home</a>
        <a href="/explore/categories/{lang}.html" class="back-link" style="margin-left: 1rem;">← Categories</a>
        <h1>📚 {cat_name}</h1>
        <div class="lang-switch">{lang_switch}</div>
        <div class="subtitle">All articles ({len(cat_arts)} articles)</div>
        <ul class="article-list">
'''
            for article in cat_arts:
                html += f'''
            <li class="article-item">
                <a href="{article.get('url', '#')}" class="article-link">
                    <div class="article-title">{article.get('title', 'Untitled')}</div>
                    <div class="article-meta">
                        <span>📅 {article.get('date', '')}</span>
                        <span>⏱️ {article.get('reading_time', '')} min read</span>
                        <span>👁️ {article.get('views', '')} views</span>
                    </div>
                </a>
            </li>
'''
            html += '''
        </ul>
        <footer>
            <p>Gatemirror — Global insights on Tech, Wellness & Future Economy</p>
        </footer>
    </div>
</body>
</html>'''
            
            s3.put_object(Bucket=R2_BUCKET, Key=f"explore/category-archive/{lang}/{cat_key}/index.html", Body=html.encode('utf-8'), ContentType='text/html')
            print(f"   ✅ explore/category-archive/{lang}/{cat_key}/index.html ({len(cat_arts)} articles)")

# ================= ANA LİBRARIAN =================

def librarian():
    print("\n" + "=" * 60)
    print("📚 KÜTÜPHANECİ BOT (Librarian)")
    print("   ✅ explore/ klasörü oluşturuluyor")
    print("   ✅ Atomic swap: articles_ready/ → articles/")
    print("=" * 60)
    
    # 1. Önce explore/ sayfalarını oluştur
    articles = get_articles_from_r2()
    if articles:
        print(f"\n📊 Toplam {len(articles)} makale bulundu.")
        
        print("\n📄 Statik sayfalar oluşturuluyor...")
        generate_explorer_json(articles)
        
        for lang in LANGUAGES:
            print(f"\n   🌍 {lang.upper()} işleniyor...")
            generate_all_articles_page(articles, lang)
            generate_categories_page(articles, lang)
            generate_category_archives(articles, lang)
    else:
        print("⚠️ articles.json okunamadı, explore/ sayfaları atlanıyor.")
    
    # 2. Atomic swap yap (articles_ready/ → articles/)
    try:
        swap_success = atomic_swap()
        if swap_success:
            print("\n✅ SWAP BAŞARILI! Site yeni içerikle yayında.")
        else:
            print("\n❌ SWAP BAŞARISIZ! Site eski içerikle devam ediyor.")
            print("   Lütfen manuel müdahale gerekebilir.")
            sys.exit(1)
    except Exception as e:
        print(f"\n❌ KRİTİK HATA: {e}")
        print("   SEIÇARIZ! Manuel müdahale gerekli.")
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("🏁 KÜTÜPHANECİ BOT TAMAMLANDI!")
    print("   ✅ explore/ klasörü güncellendi")
    print("   ✅ Atomic swap tamamlandı")
    print("=" * 60)

if __name__ == "__main__":
    librarian()

