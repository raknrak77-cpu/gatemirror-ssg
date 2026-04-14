import os
import json
import boto3
from collections import defaultdict
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

def get_articles_from_r2():
    try:
        response = s3.get_object(Bucket=R2_BUCKET, Key='articles.json')
        return json.loads(response['Body'].read().decode('utf-8'))
    except Exception as e:
        print(f"⚠️ articles.json okunamadı: {e}")
        return []

def generate_all_articles_page(articles, lang):
    """Tüm makaleleri listeleyen statik sayfa oluşturur - explore/all-explore/{lang}/index.html"""
    
    lang_articles = [a for a in articles if a.get('lang') == lang]
    lang_articles.sort(key=lambda x: x.get('sort_date', ''), reverse=True)
    
    lang_name = LANG_NAMES.get(lang, 'English')
    
    # Dil geçiş bağlantıları
    lang_switch = ''
    for l in LANGUAGES:
        active_class = 'active' if l == lang else ''
        lang_switch += f'<a href="/explore/all-explore/{l}/index.html" class="lang-btn {active_class}">🇺🇸 {LANG_NAMES[l]}</a>' if l == 'en' else f'<a href="/explore/all-explore/{l}/index.html" class="lang-btn {active_class}"> {LANG_NAMES[l]}</a>'
    
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
        <div class="subtitle">''' + str(len(lang_articles)) + ''' articles</div>
        <ul class="article-list">
'''
    
    for article in lang_articles:
        title = article.get('title', 'Untitled')
        date = article.get('date', '')
        url = article.get('url', '#')
        reading_time = article.get('reading_time', '')
        views = article.get('views', '')
        
        html += f'''
            <li class="article-item">
                <a href="{url}" class="article-link">
                    <div class="article-title">{title}</div>
                    <div class="article-meta">
                        <span>📅 {date}</span>
                        <span>⏱️ {reading_time} min read</span>
                        <span>👁️ {views} views</span>
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
    
    key = f"explore/all-explore/{lang}/index.html"
    s3.put_object(
        Bucket=R2_BUCKET,
        Key=key,
        Body=html.encode('utf-8'),
        ContentType='text/html'
    )
    print(f"   ✅ {key} oluşturuldu ({len(lang_articles)} articles)")

def generate_categories_page(articles, lang):
    """Kategori listesi sayfası oluşturur - explore/category-explore/{lang}/index.html"""
    
    lang_articles = [a for a in articles if a.get('lang') == lang]
    
    category_articles = {cat: [] for cat in CATEGORIES}
    for article in lang_articles:
        cat = article.get('category', '')
        if cat in category_articles:
            category_articles[cat].append(article)
    
    for cat in category_articles:
        category_articles[cat].sort(key=lambda x: x.get('sort_date', ''), reverse=True)
    
    lang_name = LANG_NAMES.get(lang, 'English')
    
    # Dil geçiş bağlantıları
    lang_switch = ''
    for l in LANGUAGES:
        active_class = 'active' if l == lang else ''
        lang_switch += f'<a href="/explore/category-explore/{l}/index.html" class="lang-btn {active_class}">🇺🇸 {LANG_NAMES[l]}</a>' if l == 'en' else f'<a href="/explore/category-explore/{l}/index.html" class="lang-btn {active_class}"> {LANG_NAMES[l]}</a>'
    
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
                title = article.get('title', 'Untitled')
                date = article.get('date', '')
                url = article.get('url', '#')
                html += f'''
                <li class="article-item">
                    <a href="{url}" class="article-link">
                        <div class="article-title">{title}</div>
                        <div class="article-meta">📅 {date}</div>
                    </a>
                </li>
'''
            if len(cat_arts) > 8:
                archive_url = f"/explore/category-explore/{lang}/{cat_key}/"
                html += f'''
                <div class="more-link">
                    <a href="{archive_url}">+ {len(cat_arts) - 8} more in {cat_name} →</a>
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
    
    key = f"explore/category-explore/{lang}/index.html"
    s3.put_object(
        Bucket=R2_BUCKET,
        Key=key,
        Body=html.encode('utf-8'),
        ContentType='text/html'
    )
    print(f"   ✅ {key} oluşturuldu")

def generate_category_archives(articles, lang):
    """Her kategori için ayrı arşiv sayfası oluşturur - explore/category-explore/{lang}/{category}/index.html"""
    
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
        
        # Dil geçiş bağlantıları
        lang_switch = ''
        for l in LANGUAGES:
            active_class = 'active' if l == lang else ''
            lang_switch += f'<a href="/explore/category-explore/{l}/{cat_key}/" class="lang-btn {active_class}">🇺🇸 {LANG_NAMES[l]}</a>' if l == 'en' else f'<a href="/explore/category-explore/{l}/{cat_key}/" class="lang-btn {active_class}"> {LANG_NAMES[l]}</a>'
        
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
        <a href="/explore/category-explore/{lang}/" class="back-link" style="margin-left: 1rem;">← Categories</a>
        <h1>📚 {cat_name}</h1>
        <div class="lang-switch">{lang_switch}</div>
        <div class="subtitle">All articles ({len(cat_arts)} articles)</div>
        <ul class="article-list">
'''
            for article in cat_arts:
                title = article.get('title', 'Untitled')
                date = article.get('date', '')
                reading_time = article.get('reading_time', '')
                views = article.get('views', '')
                url = article.get('url', '#')
                html += f'''
            <li class="article-item">
                <a href="{url}" class="article-link">
                    <div class="article-title">{title}</div>
                    <div class="article-meta">
                        <span>📅 {date}</span>
                        <span>⏱️ {reading_time} min read</span>
                        <span>👁️ {views} views</span>
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
            
            key = f"explore/category-explore/{lang}/{cat_key}/index.html"
            s3.put_object(
                Bucket=R2_BUCKET,
                Key=key,
                Body=html.encode('utf-8'),
                ContentType='text/html'
            )
            print(f"   ✅ {key} oluşturuldu ({len(cat_arts)} articles)")

def librarian():
    print("\n" + "="*60)
    print("📚 KÜTÜPHANECİ BOT (Librarian) - Yeni Klasör Yapısı")
    print("   explore/all-explore/{lang}/index.html")
    print("   explore/category-explore/{lang}/index.html")
    print("   explore/category-explore/{lang}/{category}/index.html")
    print("="*60)
    
    articles = get_articles_from_r2()
    if not articles:
        print("❌ Hiç makale bulunamadı (articles.json boş veya yok)")
        return
    
    print(f"📊 Toplam {len(articles)} makale bulundu.")
    
    # Dil bazlı istatistik
    lang_counts = {}
    for article in articles:
        lang = article.get('lang', 'unknown')
        lang_counts[lang] = lang_counts.get(lang, 0) + 1
    
    for lang in LANGUAGES:
        print(f"   📊 {lang.upper()}: {lang_counts.get(lang, 0)} makale")
    
    print("\n📄 Statik sayfalar oluşturuluyor...")
    
    # Her dil için sayfaları oluştur
    for lang in LANGUAGES:
        print(f"\n   🌍 {lang.upper()} işleniyor...")
        generate_all_articles_page(articles, lang)
        generate_categories_page(articles, lang)
        generate_category_archives(articles, lang)
    
    print("\n" + "="*60)
    print("🏁 Kütüphaneci Bot tamamlandı.")
    print("   ✅ explore/all-explore/{lang}/index.html")
    print("   ✅ explore/category-explore/{lang}/index.html")
    print("   ✅ explore/category-explore/{lang}/{category}/index.html")
    print("="*60)

if __name__ == "__main__":
    librarian()
