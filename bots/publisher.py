import os
import random
import json
import boto3
import requests
from datetime import datetime, timedelta
from botocore.client import Config
from jinja2 import Template
from concurrent.futures import ThreadPoolExecutor, as_completed

# Import from makeup
from makeup import (
    get_all_raw_articles,
    build_alternate_langs_dict,
    get_menu_texts,
    get_category_name,
    get_category_description,
    generate_sitemap,
    generate_robots_txt
)

# Import from hero_bot
from hero_bot import render_hero

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

# ================= CACHE MEKANİZMALARI =================
hero_cache = {}
template_cache = {}
template_raw_cache = {}
_articles_json_cache = None
_articles_json_time = None

def get_articles_from_r2_cached():
    """articles.json'u cache'le (30 saniye geçerli)"""
    global _articles_json_cache, _articles_json_time
    
    now = datetime.now()
    if _articles_json_cache and _articles_json_time and (now - _articles_json_time).seconds < 30:
        return _articles_json_cache
    
    try:
        response = s3.get_object(Bucket=R2_BUCKET, Key='articles.json')
        _articles_json_cache = json.loads(response['Body'].read().decode('utf-8'))
        _articles_json_time = now
        return _articles_json_cache
    except:
        return []

def get_cached_hero(page_type, lang, category=None):
    cache_key = f"{page_type}_{lang}_{category or ''}"
    if cache_key not in hero_cache:
        hero_cache[cache_key] = render_hero(page_type, lang, category)
        print(f"   🚀 Hero cache: {cache_key}")
    return hero_cache[cache_key]

def get_cached_template(template_str, template_name):
    if template_name not in template_cache:
        template_cache[template_name] = Template(template_str)
        print(f"   🚀 Template cache: {template_name}")
    return template_cache[template_name]

# ================= TEMPLATE YÖNETİMİ =================

def upload_templates_to_r2():
    templates_dir = "templates"
    if not os.path.exists(templates_dir):
        print("⚠️ templates/ klasörü bulunamadı.")
        return
    for file in os.listdir(templates_dir):
        if file.endswith('.html'):
            local_path = os.path.join(templates_dir, file)
            r2_key = f"templates/{file}"
            try:
                s3.upload_file(local_path, R2_BUCKET, r2_key)
                print(f"✅ Template yüklendi: {r2_key}")
            except Exception as e:
                print(f"⚠️ Template yüklenemedi {file}: {e}")

def get_template_from_r2(template_name):
    if template_name in template_raw_cache:
        return template_raw_cache[template_name]
    
    try:
        url = f"{R2_PUBLIC_URL}/templates/{template_name}"
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            template_raw_cache[template_name] = resp.text
            return resp.text
    except:
        pass
    
    local_path = os.path.join("templates", template_name)
    if os.path.exists(local_path):
        with open(local_path, 'r', encoding='utf-8') as f:
            content = f.read()
            template_raw_cache[template_name] = content
            return content
    
    return None

# ================= RENDER FONKSİYONLARI =================

def render_single_page(article, alt_langs, template_str, menu_texts, related_articles):
    tmpl = get_cached_template(template_str, 'single')
    parsed = article['parsed']
    canonical = f"{R2_PUBLIC_URL}{article['url']}"
    
    author_name = article.get('author_name', parsed.get('author', 'Gatemirror Expert'))
    author_title = article.get('author_title', '')
    author_bio = article.get('author_bio', '')
    author_avatar = article.get('author_avatar', '')
    
    hero_html = get_cached_hero('article', article['lang'])
    
    # Kategori adını al (breadcrumb için)
    category_name = get_category_name(article['lang'], article['category'])
    
    return tmpl.render(
        lang=article['lang'],
        R2_PUBLIC_URL=R2_PUBLIC_URL,
        title=parsed['title'],
        description=parsed['description'],
        canonical_url=canonical,
        author_name=author_name,
        author_title=author_title,
        author_bio=author_bio,
        author_avatar=author_avatar,
        date=parsed['date'],
        editors_note=parsed['editors_note'],
        summary=parsed['summary'],
        content=parsed['content'],
        content_part1=parsed.get('content_part1', ''),
        content_part2=parsed.get('content_part2', ''),
        content_part3=parsed.get('content_part3', ''),
        sources=parsed['sources'],
        cover_image=parsed['cover_image'],
        content_image_1=parsed['content_image_1'],
        content_image_2=parsed['content_image_2'],
        reading_time=parsed['reading_time'],
        view_count=parsed['views'],
        alternate_langs=alt_langs,
        menu=menu_texts,
        related_articles=related_articles,
        hero={'html': hero_html, 'show': False},
        category=article['category'],
        category_name=category_name
    )

def render_home_page(lang, articles, featured_article, template_str, menu_texts, alternate_langs):
    tmpl = get_cached_template(template_str, 'home')
    canonical = f"{R2_PUBLIC_URL}/{lang}/"
    og_image = articles[0]['image'] if articles else ""
    
    hero_html = get_cached_hero('home', lang)
    
    return tmpl.render(
        lang=lang,
        R2_PUBLIC_URL=R2_PUBLIC_URL,
        menu=menu_texts,
        articles=articles,
        featured_article=featured_article,
        canonical_url=canonical,
        og_image=og_image,
        alternate_langs=alternate_langs,
        hero={'html': hero_html, 'show': True}
    )

def render_list_page(lang, category, cat_articles, featured_article, trending_articles, template_str, menu_texts, alternate_langs):
    tmpl = get_cached_template(template_str, 'list')
    category_name = get_category_name(lang, category)
    category_description = get_category_description(lang, category)
    category_url = f"{R2_PUBLIC_URL}/{lang}/{category}/"
    og_image = cat_articles[0]['image'] if cat_articles else ""
    
    hero_html = get_cached_hero('category', lang, category)
    
    return tmpl.render(
        lang=lang,
        R2_PUBLIC_URL=R2_PUBLIC_URL,
        menu=menu_texts,
        category_name=category_name,
        category_description=category_description,
        category_url=category_url,
        og_image=og_image,
        articles=cat_articles,
        featured_article=featured_article,
        trending_articles=trending_articles,
        pagination=None,
        guide_articles=[],
        alternate_langs=alternate_langs,
        hero={'html': hero_html, 'show': True}
    )

# ================= YENİ: EXPLORE SAYFALARI RENDER =================

def render_all_articles_page(lang, all_articles, featured_article, template_str, menu_texts, alternate_langs):
    """Tüm makaleleri listeleyen sayfa (all-articles.html template'i ile)"""
    tmpl = get_cached_template(template_str, 'all-articles')
    canonical = f"{R2_PUBLIC_URL}/explore/all-articles/{lang}.html"
    og_image = all_articles[0]['image'] if all_articles else ""
    
    hero_html = get_cached_hero('special', lang, 'all-articles')
    
    # Makaleleri hazırla
    articles_for_template = []
    for a in all_articles:
        articles_for_template.append({
            'url': a['url'],
            'image': a['parsed']['cover_image'],
            'title': a['parsed']['title'],
            'reading_time': a['parsed']['reading_time'],
            'views': a['parsed']['views'],
            'excerpt': a['parsed']['description'],
            'category_name': get_category_name(lang, a['category'])
        })
    
    featured_for_template = None
    if featured_article:
        featured_for_template = {
            'url': featured_article['url'],
            'image': featured_article['parsed']['cover_image'],
            'title': featured_article['parsed']['title'],
            'date': featured_article['parsed']['date'],
            'reading_time': featured_article['parsed']['reading_time'],
            'views': featured_article['parsed']['views'],
            'excerpt': featured_article['parsed']['description']
        }
    
    return tmpl.render(
        lang=lang,
        R2_PUBLIC_URL=R2_PUBLIC_URL,
        menu=menu_texts,
        articles=articles_for_template,
        featured_article=featured_for_template,
        canonical_url=canonical,
        og_image=og_image,
        alternate_langs=alternate_langs,
        hero={'html': hero_html, 'show': True}
    )

# ================= PARALEL YAZMA =================

def write_single_article(article, alt_langs, single_tpl, menu_texts, related_for_template):
    """Tek bir makaleyi render et ve yaz (parallel için)"""
    try:
        single_html = render_single_page(article, alt_langs, single_tpl, menu_texts, related_for_template)
        if single_html:
            target_key = article['url'].lstrip('/').replace('articles/', 'articles_ready/', 1)
            s3.put_object(Bucket=R2_BUCKET, Key=target_key, Body=single_html.encode('utf-8'), ContentType='text/html')
            return target_key
    except Exception as e:
        print(f"   ⚠️ {article.get('url', 'unknown')} yazılamadı: {e}")
    return None

# ================= ARTICLES.JSON ÜRETİMİ =================

def generate_articles_json(all_articles):
    articles_list = []
    for article in all_articles:
        articles_list.append({
            'url': article['url'],
            'lang': article['lang'],
            'category': article['category'],
            'title': article['parsed']['title'],
            'date': article['parsed']['date'],
            'reading_time': article['parsed']['reading_time'],
            'views': article['parsed']['views'],
            'cover_image': article['parsed']['cover_image'],
            'description': article['parsed']['description'],
            'slug': article.get('slug', ''),
            'hash': article.get('hash', '')
        })
    
    articles_json = json.dumps(articles_list, indent=2, ensure_ascii=False)
    s3.put_object(
        Bucket=R2_BUCKET,
        Key='articles.json',
        Body=articles_json.encode('utf-8'),
        ContentType='application/json'
    )
    print("   ✅ articles.json oluşturuldu")

# ================= ANA PUBLISHER =================

def publisher():
    print("=" * 60)
    print("🚀 PUBLISHER BOT - OPTİMİZE")
    print("   ✅ Hero Bot entegre (cache'li)")
    print("   ✅ Makale 3 parçaya bölünüyor")
    print("   ✅ Parallel yazma (5 thread)")
    print("   ✅ Explore sayfaları (all-articles)")
    print("=" * 60)
    
    upload_templates_to_r2()
    
    print("\n📄 Template'ler yükleniyor...")
    single_tpl = get_template_from_r2("single.html")
    home_tpl = get_template_from_r2("home.html")
    list_tpl = get_template_from_r2("list.html")
    all_articles_tpl = get_template_from_r2("all-articles.html")
    
    if not single_tpl or not home_tpl or not list_tpl:
        print("❌ Template'ler alınamadı.")
        return
    
    # raw-articles/ dan oku (değişen yok, aynı sistem)
    all_articles = get_all_raw_articles()
    if not all_articles:
        print("❌ Hiç makale bulunamadı (raw-articles/ boş).")
        return
    
    print(f"\n📊 Toplam {len(all_articles)} makale bulundu.")
    
    alt_dict = build_alternate_langs_dict(all_articles)
    languages = ['en', 'es', 'de', 'fr']
    total_pages = 0
    
    for lang in languages:
        print(f"\n{'=' * 40}")
        print(f"🌍 {lang.upper()} işleniyor...")
        print(f"{'=' * 40}")
        
        lang_articles = [a for a in all_articles if a['lang'] == lang]
        if not lang_articles:
            print(f"   ⚠️ {lang.upper()} için makale bulunamadı.")
            continue
        
        lang_articles.sort(key=lambda x: x['sort_datetime'], reverse=True)
        menu_texts = get_menu_texts(lang)
        
        # 1. MAKALELERİ PARALEL YAZ
        print(f"\n📝 Makaleler parallel işleniyor (5 thread)...")
        
        articles_to_write = []
        for article in lang_articles:
            key = (article['category'], article['hash'])
            alt_langs = alt_dict.get(key, [])
            
            same_cluster = [a for a in lang_articles if a.get('cluster_id') == article.get('cluster_id') and a['hash'] != article['hash']]
            if same_cluster:
                related = random.sample(same_cluster, min(3, len(same_cluster)))
            else:
                same_cat = [a for a in lang_articles if a['category'] == article['category'] and a['hash'] != article['hash']]
                related = random.sample(same_cat, min(3, len(same_cat))) if same_cat else []
            
            related_for_template = [{'url': r['url'], 'image': r['parsed']['cover_image'], 'title': r['parsed']['title']} for r in related]
            articles_to_write.append((article, alt_langs, related_for_template))
        
        # Parallel yaz
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = []
            for article, alt_langs, related_for_template in articles_to_write:
                future = executor.submit(write_single_article, article, alt_langs, single_tpl, menu_texts, related_for_template)
                futures.append(future)
            
            for future in as_completed(futures):
                result = future.result()
                if result:
                    print(f"   ✅ {result}")
                    total_pages += 1
        
        # 2. ANA SAYFA (HOME)
        print(f"\n🏠 Ana sayfa oluşturuluyor...")
        featured = lang_articles[0] if lang_articles else None
        featured_for_home = None
        if featured:
            featured_for_home = {
                'url': featured['url'],
                'image': featured['parsed']['cover_image'],
                'title': featured['parsed']['title'],
                'date': featured['parsed']['date'],
                'reading_time': featured['parsed']['reading_time'],
                'views': featured['parsed']['views'],
                'excerpt': featured['parsed']['description']
            }
        
        articles_for_home = []
        for a in lang_articles[:12]:
            articles_for_home.append({
                'url': a['url'],
                'image': a['parsed']['cover_image'],
                'title': a['parsed']['title'],
                'reading_time': a['parsed']['reading_time'],
                'views': a['parsed']['views'],
                'excerpt': a['parsed']['description']
            })
        
        home_alt_langs = [{'lang': l, 'url': f"{R2_PUBLIC_URL}/{l}/"} for l in languages if l != lang]
        
        home_html = render_home_page(lang, articles_for_home, featured_for_home, home_tpl, menu_texts, home_alt_langs)
        if home_html:
            s3.put_object(Bucket=R2_BUCKET, Key=f"articles_ready/{lang}/index.html", Body=home_html.encode('utf-8'), ContentType='text/html')
            print(f"   ✅ articles_ready/{lang}/index.html")
            total_pages += 1
        
        # 3. KATEGORİ SAYFALARI
        print(f"\n📂 Kategori sayfaları oluşturuluyor...")
        categories = ['wellness', 'tech', 'future-economy', 'eco', 'elearning']
        
        for category in categories:
            cat_articles = [a for a in lang_articles if a['category'] == category]
            if not cat_articles:
                continue
            
            cat_articles.sort(key=lambda x: x['sort_datetime'], reverse=True)
            
            featured_cat = cat_articles[0] if cat_articles else None
            featured_for_cat = None
            if featured_cat:
                featured_for_cat = {
                    'url': featured_cat['url'],
                    'image': featured_cat['parsed']['cover_image'],
                    'title': featured_cat['parsed']['title'],
                    'date': featured_cat['parsed']['date'],
                    'reading_time': featured_cat['parsed']['reading_time'],
                    'views': featured_cat['parsed']['views'],
                    'excerpt': featured_cat['parsed']['description']
                }
            
            trending = []
            for a in cat_articles[1:4]:
                trending.append({
                    'url': a['url'],
                    'image': a['parsed']['cover_image'],
                    'title': a['parsed']['title'],
                    'reading_time': a['parsed']['reading_time'],
                    'views': a['parsed']['views'],
                    'excerpt': a['parsed']['description']
                })
            
            articles_for_list = []
            for a in cat_articles:
                articles_for_list.append({
                    'url': a['url'],
                    'image': a['parsed']['cover_image'],
                    'title': a['parsed']['title'],
                    'reading_time': a['parsed']['reading_time'],
                    'views': a['parsed']['views'],
                    'excerpt': a['parsed']['description']
                })
            
            cat_alt_langs = []
            for other_lang in languages:
                if other_lang == lang:
                    continue
                cat_alt_langs.append({'lang': other_lang, 'url': f"{R2_PUBLIC_URL}/{other_lang}/{category}/"})
            
            list_html = render_list_page(lang, category, articles_for_list, featured_for_cat, trending, list_tpl, menu_texts, cat_alt_langs)
            if list_html:
                s3.put_object(Bucket=R2_BUCKET, Key=f"articles_ready/{lang}/{category}/index.html", Body=list_html.encode('utf-8'), ContentType='text/html')
                print(f"   ✅ articles_ready/{lang}/{category}/index.html ({len(cat_articles)} makale)")
                total_pages += 1
        
        # 4. YENİ: TÜM MAKALELER SAYFASI (EXPLORE)
        if all_articles_tpl:
            print(f"\n📚 Tüm makaleler sayfası oluşturuluyor...")
            
            explore_alt_langs = [{'lang': l, 'url': f"{R2_PUBLIC_URL}/explore/all-articles/{l}.html"} for l in languages if l != lang]
            
            featured_all = lang_articles[0] if lang_articles else None
            
            all_articles_html = render_all_articles_page(lang, lang_articles, featured_all, all_articles_tpl, menu_texts, explore_alt_langs)
            if all_articles_html:
                s3.put_object(Bucket=R2_BUCKET, Key=f"articles_ready/explore/all-articles/{lang}.html", Body=all_articles_html.encode('utf-8'), ContentType='text/html')
                print(f"   ✅ articles_ready/explore/all-articles/{lang}.html ({len(lang_articles)} makale)")
                total_pages += 1
        else:
            print(f"\n⚠️ all-articles.html template'i bulunamadı, explore sayfası atlanıyor.")
    
    print(f"\n{'=' * 40}")
    print("📊 Sitemap ve robots.txt oluşturuluyor...")
    print(f"{'=' * 40}")
    
    sitemap_xml = generate_sitemap(all_articles, alt_dict)
    s3.put_object(Bucket=R2_BUCKET, Key='sitemap.xml', Body=sitemap_xml.encode('utf-8'), ContentType='application/xml')
    print("   ✅ sitemap.xml yüklendi")
    
    robots_txt = generate_robots_txt()
    s3.put_object(Bucket=R2_BUCKET, Key='robots.txt', Body=robots_txt.encode('utf-8'), ContentType='text/plain')
    print("   ✅ robots.txt yüklendi")
    
    generate_articles_json(all_articles)
    
    print(f"\n{'=' * 40}")
    print("🏁 PUBLISHER TAMAMLANDI!")
    print(f"   ✅ Tüm içerik articles_ready/ klasörüne yazıldı")
    print(f"   ✅ Toplam sayfa: {total_pages}")
    print(f"   ✅ Hero cache: {len(hero_cache)} benzersiz hero")
    print(f"   ✅ Template cache: {len(template_cache)} template")
    print(f"   ✅ R2_PUBLIC_URL template'lere gönderildi")
    print(f"{'=' * 40}")

if __name__ == "__main__":
    publisher()
        
        
