import os
import json
import sys
import boto3
from collections import defaultdict
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

# ================= ORTAK HTML BİLEŞENLERİ =================

def get_side_menu_html(lang):
    """Side menu HTML'ini oluşturur"""
    return f'''<div class="side-menu" id="sideMenu">
    <div class="close-menu" onclick="toggleMenu()">&times;</div>
    <div class="dark-mode-toggle">
        <span>🌓 Dark Mode</span>
        <div class="toggle-switch" id="darkModeToggle"></div>
    </div>
    <div class="lang-section">
        <div class="lang-title">READ IN</div>
        <div class="flags">
            <a href="/" class="flag-link">🇺🇸 EN</a>
            <a href="/es/" class="flag-link">🇪🇸 ES</a>
            <a href="/de/" class="flag-link">🇩🇪 DE</a>
            <a href="/fr/" class="flag-link">🇫🇷 FR</a>
        </div>
    </div>
    <div class="nav-links">
        <a href="/{lang}/">HOME</a>
        <a href="/{lang}/wellness/">WELLNESS</a>
        <a href="/{lang}/tech/">TECH & AI</a>
        <a href="/{lang}/future-economy/">FUTURE ECONOMY</a>
        <a href="/{lang}/eco/">ECO & SUSTAINABLE</a>
        <a href="/{lang}/elearning/">E-LEARNING</a>
    </div>
    <div class="footer-links">
        <a href="/about-us.html">About Gatemirror</a>
        <a href="/privacy-policy.html">Privacy Policy</a>
        <a href="/contact.html">Contact Us</a>
        <p>&copy; 2026 Gatemirror Media</p>
    </div>
</div>'''

def get_nav_html(lang):
    """Navigasyon HTML'ini oluşturur"""
    return f'''<nav>
    <button class="menu-btn" onclick="toggleMenu()" aria-label="Menu">
        <i class="fas fa-bars"></i>
    </button>
    <a href="/" class="logo">GATE<span>MIRROR</span></a>
    <div class="nav-links">
        <a href="/{lang}/">HOME</a>
        <a href="/{lang}/wellness/">WELLNESS</a>
        <a href="/{lang}/tech/">TECH & AI</a>
        <a href="/{lang}/future-economy/">FUTURE ECONOMY</a>
        <a href="/{lang}/eco/">ECO & SUSTAINABLE</a>
        <a href="/{lang}/elearning/">E-LEARNING</a>
    </div>
</nav>'''

def get_footer_html():
    """Footer HTML'ini oluşturur"""
    return '''<footer>
    <div class="footer-content">
        <div class="footer-column">
            <h4>Gatemirror</h4>
            <a href="/about-us.html">About Us</a>
            <a href="/contact.html">Contact</a>
            <a href="/privacy-policy.html">Privacy Policy</a>
        </div>
        <div class="footer-column">
            <h4>Categories</h4>
            <a href="/en/tech/">TECH & AI</a>
            <a href="/en/future-economy/">FUTURE ECONOMY</a>
            <a href="/en/wellness/">WELLNESS</a>
            <a href="/en/eco/">ECO & SUSTAINABLE</a>
            <a href="/en/elearning/">E-LEARNING</a>
        </div>
        <div class="footer-column">
            <h4>Read in</h4>
            <a href="/">🇺🇸 English</a>
            <a href="/es/">🇪🇸 Español</a>
            <a href="/de/">🇩🇪 Deutsch</a>
            <a href="/fr/">🇫🇷 Français</a>
        </div>
    </div>
    <div class="footer-copyright">
        <p>&copy; 2026 Gatemirror Media Group. All rights reserved.</p>
    </div>
</footer>'''

def get_hero_html(title, description):
    """Hero HTML'ini oluşturur"""
    return f'''<div class="hero">
    <h1 class="hero-title">{title}</h1>
    <p class="hero-description">{description}</p>
</div>'''

def get_base_js():
    """Base JavaScript (side menu, dark mode)"""
    return '''<script>
    function toggleMenu() { document.getElementById('sideMenu').classList.toggle('active'); }
    document.addEventListener('click', function(e) {
        const menu = document.getElementById('sideMenu');
        const btn = document.querySelector('.menu-btn');
        if (menu && menu.classList.contains('active') && !menu.contains(e.target) && !btn.contains(e.target)) menu.classList.remove('active');
    });
    const toggle = document.getElementById('darkModeToggle');
    if (toggle) {
        toggle.addEventListener('click', () => document.body.classList.toggle('dark'));
        if (localStorage.getItem('darkMode') === 'enabled') document.body.classList.add('dark');
        const observer = new MutationObserver(() => localStorage.setItem('darkMode', document.body.classList.contains('dark') ? 'enabled' : 'disabled'));
        observer.observe(document.body, { attributes: true, attributeFilter: ['class'] });
    }
</script>'''

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

# ================= OPTİMİZE ATOMIC SWAP =================

def atomic_swap():
    """
    articles_ready/ → articles/ OPTİMİZE swap
    - Backup YOK (üzerine yaz)
    - Parallel copy (10 thread)
    """
    print("\n" + "=" * 40)
    print("🔄 ATOMIC SWAP: articles_ready/ → articles/ (Üzerine Yaz + Parallel)")
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
            if success_count % 50 == 0:
                print(f"   📊 {success_count}/{len(source_files)} dosya yazıldı...")
    
    print(f"   ✅ {success_count}/{len(source_files)} dosya başarıyla yazıldı")
    
    if success_count < len(source_files) * 0.9:
        print(f"❌ Çok fazla hata ({success_count}/{len(source_files)} başarılı)")
        print("   SEIÇARIZ! Manuel müdahale gerekli.")
        return False
    
    print("🗑️ articles_ready/ siliniyor...")
    delete_folder('articles_ready/')
    
    print("✅ Swap tamamlandı!")
    return True

# ================= LİBRARIAN FONKSİYONLARI =================

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
    """Tüm makaleleri listeleyen statik sayfa - ORTAK CSS + Side menu + Hero ile"""
    lang_articles = [a for a in articles if a.get('lang') == lang]
    lang_articles.sort(key=lambda x: x.get('sort_date', ''), reverse=True)
    lang_name = LANG_NAMES.get(lang, 'English')
    
    # Dil geçiş bağlantıları
    lang_switch = ''
    for l in LANGUAGES:
        active_class = 'active' if l == lang else ''
        lang_switch += f'<a href="/explore/all-articles/{l}.html" class="lang-btn {active_class}">{LANG_FLAGS.get(l, "")} {LANG_NAMES[l]}</a>'
    
    hero_title = f"All Articles ({lang_name})"
    hero_description = f"Browse all {len(lang_articles)} articles in {lang_name}. Find the content that matters to you."
    
    html = f'''<!DOCTYPE html>
<html lang="{lang}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
    <title>All Articles | Gatemirror ({lang_name})</title>
    <meta name="description" content="Browse all articles on Gatemirror in {lang_name}. Global insights on technology, wellness, future economy, sustainability and e-learning.">
    <link rel="canonical" href="{R2_PUBLIC_URL}/explore/all-articles/{lang}.html">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css">
    <link rel="stylesheet" href="{R2_PUBLIC_URL}/assets/css/style.css">
</head>
<body>
{get_side_menu_html(lang)}
{get_nav_html(lang)}
<main>
    {get_hero_html(hero_title, hero_description)}
    <div class="page-container">
        <div class="lang-switch" style="display: flex; gap: 1rem; flex-wrap: wrap; margin-bottom: 2rem;">
            {lang_switch}
        </div>
        <ul class="article-list" style="list-style: none; padding: 0;">
'''
    for article in lang_articles:
        html += f'''
            <li class="article-item" style="background: var(--gray); margin-bottom: 1rem; border-radius: 0.5rem; transition: transform 0.2s;">
                <a href="{article.get('url', '#')}" class="article-link" style="display: block; padding: 1rem; text-decoration: none; color: inherit;">
                    <div class="article-title" style="font-size: 1.1rem; font-weight: 600; margin-bottom: 0.25rem;">{article.get('title', 'Untitled')}</div>
                    <div class="article-meta" style="font-size: 0.8rem; color: var(--text-light);">
                        <span>📅 {article.get('date', '')}</span>
                        <span>⏱️ {article.get('reading_time', '')} min read</span>
                        <span>👁️ {article.get('views', '')} views</span>
                    </div>
                </a>
            </li>
'''
    html += f'''
        </ul>
    </div>
</main>
{get_footer_html()}
{get_base_js()}
</body>
</html>'''
    
    s3.put_object(Bucket=R2_BUCKET, Key=f"explore/all-articles/{lang}.html", Body=html.encode('utf-8'), ContentType='text/html')
    print(f"   ✅ explore/all-articles/{lang}.html ({len(lang_articles)} articles)")

def generate_categories_page(articles, lang):
    """Kategori listesi sayfası - ORTAK CSS + Side menu + Hero ile"""
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
        lang_switch += f'<a href="/explore/categories/{l}.html" class="lang-btn {active_class}">{LANG_FLAGS.get(l, "")} {LANG_NAMES[l]}</a>'
    
    hero_title = f"Categories ({lang_name})"
    hero_description = "Browse articles by category. Find the content that matters to you."
    
    html = f'''<!DOCTYPE html>
<html lang="{lang}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
    <title>Categories | Gatemirror ({lang_name})</title>
    <meta name="description" content="Browse all categories on Gatemirror in {lang_name}. Technology, Wellness, Future Economy, Eco & Sustainable, E-Learning.">
    <link rel="canonical" href="{R2_PUBLIC_URL}/explore/categories/{lang}.html">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css">
    <link rel="stylesheet" href="{R2_PUBLIC_URL}/assets/css/style.css">
</head>
<body>
{get_side_menu_html(lang)}
{get_nav_html(lang)}
<main>
    {get_hero_html(hero_title, hero_description)}
    <div class="page-container">
        <div class="lang-switch" style="display: flex; gap: 1rem; flex-wrap: wrap; margin-bottom: 2rem;">
            {lang_switch}
        </div>
'''
    for cat_key, cat_names in CATEGORIES.items():
        cat_name = cat_names.get(lang, cat_names['en'])
        cat_arts = category_articles.get(cat_key, [])
        html += f'''
        <div class="category-section" style="margin-bottom: 3rem;">
            <h2 class="category-title" style="font-size: 1.8rem; color: var(--primary); margin-bottom: 1rem; border-left: 4px solid var(--primary); padding-left: 1rem;">{cat_name}</h2>
            <ul class="article-list" style="list-style: none; padding: 0;">
'''
        if cat_arts:
            for article in cat_arts[:8]:
                html += f'''
                <li class="article-item" style="background: var(--gray); margin-bottom: 0.75rem; border-radius: 0.5rem;">
                    <a href="{article.get('url', '#')}" class="article-link" style="display: block; padding: 0.75rem 1rem; text-decoration: none; color: inherit;">
                        <div class="article-title" style="font-size: 1rem; font-weight: 500;">{article.get('title', 'Untitled')}</div>
                        <div class="article-meta" style="font-size: 0.75rem; color: var(--text-light); margin-top: 0.25rem;">📅 {article.get('date', '')}</div>
                    </a>
                </li>
'''
            if len(cat_arts) > 8:
                html += f'''
                <div class="more-link" style="margin-top: 0.5rem; text-align: right;">
                    <a href="/explore/category-archive/{lang}/{cat_key}/" style="color: var(--primary);">+ {len(cat_arts) - 8} more in {cat_name} →</a>
                </div>
'''
        else:
            html += '<div class="empty-category" style="background: var(--gray); padding: 1rem; border-radius: 0.5rem; text-align: center; color: var(--text-light);">No articles yet</div>'
        html += '''
            </ul>
        </div>
'''
    html += f'''
    </div>
</main>
{get_footer_html()}
{get_base_js()}
</body>
</html>'''
    
    s3.put_object(Bucket=R2_BUCKET, Key=f"explore/categories/{lang}.html", Body=html.encode('utf-8'), ContentType='text/html')
    print(f"   ✅ explore/categories/{lang}.html")

def generate_category_archives(articles, lang):
    """Her kategori için ayrı arşiv sayfası - ORTAK CSS + Side menu + Hero ile"""
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
            lang_switch += f'<a href="/explore/category-archive/{l}/{cat_key}/" class="lang-btn {active_class}">{LANG_FLAGS.get(l, "")} {LANG_NAMES[l]}</a>'
        
        hero_title = f"{cat_name}"
        hero_description = f"All articles in {cat_name} category ({len(cat_arts)} articles)."
        
        if cat_arts:
            html = f'''<!DOCTYPE html>
<html lang="{lang}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
    <title>{cat_name} Archive | Gatemirror ({lang_name})</title>
    <meta name="description" content="Browse all {cat_name} articles on Gatemirror in {lang_name}. {len(cat_arts)} articles available.">
    <link rel="canonical" href="{R2_PUBLIC_URL}/explore/category-archive/{lang}/{cat_key}/">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css">
    <link rel="stylesheet" href="{R2_PUBLIC_URL}/assets/css/style.css">
</head>
<body>
{get_side_menu_html(lang)}
{get_nav_html(lang)}
<main>
    {get_hero_html(hero_title, hero_description)}
    <div class="page-container">
        <div class="lang-switch" style="display: flex; gap: 1rem; flex-wrap: wrap; margin-bottom: 2rem;">
            {lang_switch}
        </div>
        <ul class="article-list" style="list-style: none; padding: 0;">
'''
            for article in cat_arts:
                html += f'''
            <li class="article-item" style="background: var(--gray); margin-bottom: 1rem; border-radius: 0.5rem;">
                <a href="{article.get('url', '#')}" class="article-link" style="display: block; padding: 1rem; text-decoration: none; color: inherit;">
                    <div class="article-title" style="font-size: 1.1rem; font-weight: 600; margin-bottom: 0.25rem;">{article.get('title', 'Untitled')}</div>
                    <div class="article-meta" style="font-size: 0.8rem; color: var(--text-light);">
                        <span>📅 {article.get('date', '')}</span>
                        <span>⏱️ {article.get('reading_time', '')} min read</span>
                        <span>👁️ {article.get('views', '')} views</span>
                    </div>
                </a>
            </li>
'''
            html += f'''
        </ul>
    </div>
</main>
{get_footer_html()}
{get_base_js()}
</body>
</html>'''
            
            s3.put_object(Bucket=R2_BUCKET, Key=f"explore/category-archive/{lang}/{cat_key}/index.html", Body=html.encode('utf-8'), ContentType='text/html')
            print(f"   ✅ explore/category-archive/{lang}/{cat_key}/index.html ({len(cat_arts)} articles)")

# ================= ANA LİBRARIAN =================

def librarian():
    print("\n" + "=" * 60)
    print("📚 KÜTÜPHANECİ BOT (Librarian) - OPTİMİZE")
    print("   ✅ explore/ klasörü oluşturuluyor")
    print("   ✅ Ortak CSS + Side menu + Hero kullanıyor")
    print("   ✅ Atomic swap: Üzerine Yaz + Parallel (10 thread)")
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
