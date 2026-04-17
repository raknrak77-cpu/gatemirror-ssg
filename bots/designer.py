import os
import json
import time
import random
import boto3
import requests
import fnmatch
from datetime import datetime
from botocore.client import Config
from jinja2 import Template
from concurrent.futures import ThreadPoolExecutor, as_completed

from makeup import (
    build_alternate_langs_dict,
    get_menu_texts,
    get_category_name,
    get_category_description,
    generate_sitemap,
    generate_robots_txt
)
from hero_bot import render_hero

# ================= KONFIG =================
R2_ID = os.getenv('R2_ACCOUNT_ID')
R2_ACCESS_KEY = os.getenv('R2_ACCESS_KEY_ID')
R2_SECRET_KEY = os.getenv('R2_SECRET_ACCESS_KEY')
R2_BUCKET = os.getenv('R2_BUCKET_NAME')
R2_PUBLIC_URL = os.getenv('R2_PUBLIC_URL', '').rstrip('/')

s3 = boto3.client('s3',
    endpoint_url=f'https://{R2_ID}.r2.cloudflarestorage.com',
    aws_access_key_id=R2_ACCESS_KEY,
    aws_secret_access_key=R2_SECRET_KEY,
    config=Config(signature_version='s3v4'),
    region_name='auto'
)

# ================= ZAMANLAMA =================
timings = {}

def timing(name):
    def decorator(func):
        def wrapper(*args, **kwargs):
            start = time.time()
            print(f"⏱️ [{name}] BAŞLADI...")
            result = func(*args, **kwargs)
            elapsed = time.time() - start
            timings[name] = elapsed
            print(f"✅ [{name}] TAMAMLANDI: {elapsed:.2f} saniye")
            return result
        return wrapper
    return decorator

# ================= CACHE =================
hero_cache = {}
template_cache = {}
template_raw_cache = {}
_articles_json_cache = None
_articles_json_time = None

def get_articles_from_r2_cached():
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
        start = time.time()
        hero_cache[cache_key] = render_hero(page_type, lang, category)
        print(f"   🚀 Hero cache: {cache_key} ({time.time()-start:.2f}s)")
    return hero_cache[cache_key]

def get_cached_template(template_str, template_name):
    if template_name not in template_cache:
        start = time.time()
        template_cache[template_name] = Template(template_str)
        print(f"   🚀 Template cache: {template_name} ({time.time()-start:.2f}s)")
    return template_cache[template_name]

def get_template_from_r2(template_name):
    if template_name in template_raw_cache:
        return template_raw_cache[template_name]
    start = time.time()
    try:
        url = f"{R2_PUBLIC_URL}/templates/{template_name}"
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            template_raw_cache[template_name] = resp.text
            print(f"   📥 Template indirildi: {template_name} ({time.time()-start:.2f}s)")
            return resp.text
    except:
        pass
    local_path = os.path.join("templates", template_name)
    if os.path.exists(local_path):
        with open(local_path, 'r', encoding='utf-8') as f:
            content = f.read()
            template_raw_cache[template_name] = content
            print(f"   📁 Template local: {template_name} ({time.time()-start:.2f}s)")
            return content
    return None

# ================= RAW ARTICLES OKU (SADECE FİLTRELENENLER) =================

def get_raw_article_by_hash(hash_id, lang, category):
    """Sadece belirli bir hash'teki raw article'ı bulur ve parse eder"""
    prefixes = [
        f"raw-articles/{lang}/{category}/",
        f"raw-articles/{lang}/{category}/2026/04/",
        f"raw-articles/{lang}/{category}/2026/",
    ]
    
    for prefix in prefixes:
        try:
            response = s3.list_objects_v2(Bucket=R2_BUCKET, Prefix=prefix)
            if 'Contents' not in response:
                continue
            
            for obj in response['Contents']:
                key = obj['Key']
                filename = key.split('/')[-1]
                if filename.startswith(hash_id) and filename.endswith('.html'):
                    # Bulundu!
                    file_obj = s3.get_object(Bucket=R2_BUCKET, Key=key)
                    html_content = file_obj['Body'].read().decode('utf-8')
                    from makeup import parse_article_html
                    parsed = parse_article_html(html_content, lang, category, hash_id, "2026", "04")
                    return parsed
        except:
            continue
    
    print(f"   ⚠️ {hash_id} için raw article bulunamadı")
    return None

# ================= RENDER =================

def render_single_page(article, alt_langs, template_str, menu_texts, related_articles):
    start = time.time()
    tmpl = get_cached_template(template_str, 'single')
    parsed = article['parsed']
    canonical = f"{R2_PUBLIC_URL}{article['url']}"
    
    author_name = article.get('author_name', parsed.get('author', 'Gatemirror Expert'))
    author_title = article.get('author_title', '')
    author_bio = article.get('author_bio', '')
    author_avatar = article.get('author_avatar', '')
    
    hero_html = get_cached_hero('article', article['lang'])
    category_name = get_category_name(article['lang'], article['category'])
    
    result = tmpl.render(
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
        editors_note=parsed.get('editors_note', ''),
        summary=parsed.get('summary', ''),
        content=parsed.get('content', ''),
        content_part1=parsed.get('content_part1', ''),
        content_part2=parsed.get('content_part2', ''),
        content_part3=parsed.get('content_part3', ''),
        sources=parsed.get('sources', ''),
        cover_image=parsed['cover_image'],
        content_image_1=parsed.get('content_image_1', ''),
        content_image_2=parsed.get('content_image_2', ''),
        reading_time=parsed.get('reading_time', 5),
        view_count=parsed.get('views', 100),
        alternate_langs=alt_langs,
        menu=menu_texts,
        related_articles=related_articles,
        hero={'html': hero_html, 'show': False},
        category=article['category'],
        category_name=category_name
    )
    print(f"      📄 Render: {parsed['title'][:40]}... ({time.time()-start:.2f}s)")
    return result

def write_single_article(article, alt_langs, single_tpl, menu_texts, related_for_template):
    start = time.time()
    try:
        single_html = render_single_page(article, alt_langs, single_tpl, menu_texts, related_for_template)
        if single_html:
            target_key = article['url'].lstrip('/').replace('articles/', 'articles_ready/', 1)
            s3.put_object(Bucket=R2_BUCKET, Key=target_key, Body=single_html.encode('utf-8'), ContentType='text/html')
            print(f"      💾 Yazıldı: {target_key} ({time.time()-start:.2f}s)")
            return target_key
    except Exception as e:
        print(f"   ⚠️ {article.get('url', 'unknown')} yazılamadı: {e}")
    return None

# ================= ANA DESIGNER =================

@timing("DESIGNER TOPLAM")
def designer():
    print("=" * 60)
    print("🎨 DESIGNER BOT - TASARIM MODU (SADECE EN + TECH/WELLNESS)")
    print("=" * 60)
    
    # 1. TEMPLATE YÜKLEME
    print("\n📄 1. TEMPLATE YÜKLEME")
    t_start = time.time()
    single_tpl = get_template_from_r2("single.html")
    home_tpl = get_template_from_r2("home.html")
    list_tpl = get_template_from_r2("list.html")
    all_articles_tpl = get_template_from_r2("all-articles.html")
    timings["TEMPLATE_YUKLEME"] = time.time() - t_start
    print(f"   ✅ Template yükleme: {timings['TEMPLATE_YUKLEME']:.2f}s")
    
    if not single_tpl:
        print("❌ Template alınamadı")
        return
    
    # 2. JSON'DAN LİSTE OKU
    print("\n📖 2. JSON'DAN MAKALE LİSTESİ OKUMA")
    t_start = time.time()
    articles_meta = get_articles_from_r2_cached()
    timings["JSON_OKUMA"] = time.time() - t_start
    print(f"   ✅ {len(articles_meta)} makale meta okundu: {timings['JSON_OKUMA']:.2f}s")
    
    if not articles_meta:
        print("❌ articles.json yok veya boş")
        return
    
    # 3. FİLTRELE (sadece EN + tech/wellness)
    print("\n🔍 3. FİLTRELEME (EN + tech/wellness)")
    t_start = time.time()
    filtered_meta = [m for m in articles_meta if m.get('lang') == 'en' and m.get('category') in ['tech', 'wellness']]
    timings["FILTRELEME"] = time.time() - t_start
    print(f"   ✅ {len(filtered_meta)} makale filtrelendi: {timings['FILTRELEME']:.2f}s")
    
    if not filtered_meta:
        print("❌ Filtreleme sonucu makale kalmadı")
        return
    
    # 4. HER MAKALE İÇİN RAW ARTICLES OKU (SADECE FİLTRELENENLER)
    print(f"\n📥 4. RAW ARTICLES OKUMA ({len(filtered_meta)} makale)")
    t_start = time.time()
    
    all_articles = []
    for meta in filtered_meta:
        hash_id = meta.get('hash')
        lang = meta.get('lang')
        category = meta.get('category')
        
        print(f"   📥 {hash_id} ({category}) okunuyor...")
        parsed = get_raw_article_by_hash(hash_id, lang, category)
        
        if parsed:
            all_articles.append({
                'url': meta.get('url'),
                'lang': lang,
                'category': category,
                'hash': hash_id,
                'slug': meta.get('slug'),
                'sort_date': meta.get('date'),
                'sort_datetime': meta.get('date'),
                'author_name': meta.get('author_name', 'Gatemirror Expert'),
                'author_title': meta.get('author_title', ''),
                'author_bio': meta.get('author_bio', ''),
                'author_avatar': meta.get('author_avatar', ''),
                'parsed': parsed
            })
            print(f"      ✅ {parsed['title'][:50]}...")
        else:
            print(f"      ⚠️ {hash_id} için raw article bulunamadı, atlanıyor")
    
    timings["RAW_ARTICLES_OKUMA"] = time.time() - t_start
    print(f"   ✅ {len(all_articles)} makale başarıyla okundu: {timings['RAW_ARTICLES_OKUMA']:.2f}s")
    
    if not all_articles:
        print("❌ Hiç makale okunamadı")
        return
    
    # 5. Alternate langs oluştur
    print("\n🌐 5. ALTERNATE LANGS")
    t_start = time.time()
    alt_dict = build_alternate_langs_dict(all_articles)
    timings["ALTERNATE_LANGS"] = time.time() - t_start
    print(f"   ✅ Alternate langs: {timings['ALTERNATE_LANGS']:.2f}s")
    
    lang_articles = all_articles
    lang_articles.sort(key=lambda x: x['sort_datetime'], reverse=True)
    menu_texts = get_menu_texts('en')
    
    # 6. MAKALELERİ PARALEL YAZ
    print(f"\n📝 6. MAKALELERİ PARALEL YAZMA ({len(lang_articles)} makale)")
    t_start = time.time()
    
    articles_to_write = []
    for article in lang_articles:
        key = (article['category'], article['hash'])
        alt_langs = alt_dict.get(key, [])
        same_cat = [a for a in lang_articles if a['category'] == article['category'] and a['hash'] != article['hash']]
        related = random.sample(same_cat, min(3, len(same_cat))) if same_cat else []
        related_for_template = [{'url': r['url'], 'image': r['parsed']['cover_image'], 'title': r['parsed']['title']} for r in related]
        articles_to_write.append((article, alt_langs, related_for_template))
    
    write_start = time.time()
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = []
        for article, alt_langs, related_for_template in articles_to_write:
            future = executor.submit(write_single_article, article, alt_langs, single_tpl, menu_texts, related_for_template)
            futures.append(future)
        
        for future in as_completed(futures):
            future.result()
    
    timings["MAKALE_YAZMA"] = time.time() - write_start
    print(f"   ✅ Makale yazma: {timings['MAKALE_YAZMA']:.2f}s")
    
    # ================= 7. HOME PAGE (DÜZELTİLMİŞ) =================
    print("\n🏠 7. HOME PAGE")
    t_start = time.time()

    # R2_PUBLIC_URL kontrolü
    if not R2_PUBLIC_URL:
        print("   ⚠️ R2_PUBLIC_URL boş! Varsayılan değer kullanılıyor.")
        r2_url = "https://gatemirror-ssg-assets.d71a.r2.cloudflarestorage.com"
    else:
        r2_url = R2_PUBLIC_URL
    print(f"   🔍 Kullanılacak R2_URL: {r2_url}")

    # SVG URL'lerini logla
    print(f"   🔍 SVG1: {r2_url}/assets/svg1.svg")
    print(f"   🔍 SVG2: {r2_url}/assets/svg2.svg")

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

    try:
        tmpl = get_cached_template(home_tpl, 'home')
        hero_html = get_cached_hero('home', 'en')
        home_html = tmpl.render(
            lang='en',
            R2_PUBLIC_URL=r2_url,
            menu=menu_texts,
            articles=articles_for_home,
            featured_article=featured_for_home,
            canonical_url=f"{r2_url}/en/",
            og_image=articles_for_home[0]['image'] if articles_for_home else "",
            alternate_langs=[],
            hero={'html': hero_html, 'show': True}
        )
        s3.put_object(Bucket=R2_BUCKET, Key="articles_ready/en/index.html", Body=home_html.encode('utf-8'), ContentType='text/html')
        timings["HOME_PAGE"] = time.time() - t_start
        print(f"   ✅ Home page: {timings['HOME_PAGE']:.2f}s")
    except Exception as e:
        print(f"   ❌ HOME PAGE RENDER HATASI: {e}")
        timings["HOME_PAGE"] = time.time() - t_start
        print(f"   ⚠️ Home page başarısız: {timings['HOME_PAGE']:.2f}s")
    
    # 8. KATEGORİ SAYFALARI
    print("\n📂 8. KATEGORİ SAYFALARI")
    t_start = time.time()
    categories = ['tech', 'wellness']
    
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
        
        tmpl = get_cached_template(list_tpl, 'list')
        hero_html = get_cached_hero('category', 'en', category)
        list_html = tmpl.render(
            lang='en',
            R2_PUBLIC_URL=R2_PUBLIC_URL,
            menu=menu_texts,
            category_name=get_category_name('en', category),
            category_description=get_category_description('en', category),
            category_url=f"{R2_PUBLIC_URL}/en/{category}/",
            og_image=articles_for_list[0]['image'] if articles_for_list else "",
            articles=articles_for_list,
            featured_article=featured_for_cat,
            trending_articles=[],
            pagination=None,
            guide_articles=[],
            alternate_langs=[],
            hero={'html': hero_html, 'show': True}
        )
        s3.put_object(Bucket=R2_BUCKET, Key=f"articles_ready/en/{category}/index.html", Body=list_html.encode('utf-8'), ContentType='text/html')
        print(f"   ✅ {category} sayfası: {len(cat_articles)} makale")
    
    timings["KATEGORI_SAYFALARI"] = time.time() - t_start
    print(f"   ✅ Kategori sayfaları: {timings['KATEGORI_SAYFALARI']:.2f}s")
    
    # 9. ALL ARTICLES SAYFASI
    if all_articles_tpl:
        print("\n📚 9. ALL ARTICLES SAYFASI")
        t_start = time.time()
        tmpl = get_cached_template(all_articles_tpl, 'all-articles')
        hero_html = get_cached_hero('special', 'en', 'all-articles')
        
        articles_for_template = []
        for a in lang_articles:
            articles_for_template.append({
                'url': a['url'],
                'image': a['parsed']['cover_image'],
                'title': a['parsed']['title'],
                'reading_time': a['parsed']['reading_time'],
                'views': a['parsed']['views'],
                'excerpt': a['parsed']['description'],
                'category_name': get_category_name('en', a['category'])
            })
        
        featured_all = lang_articles[0] if lang_articles else None
        featured_for_template = None
        if featured_all:
            featured_for_template = {
                'url': featured_all['url'],
                'image': featured_all['parsed']['cover_image'],
                'title': featured_all['parsed']['title'],
                'date': featured_all['parsed']['date'],
                'reading_time': featured_all['parsed']['reading_time'],
                'views': featured_all['parsed']['views'],
                'excerpt': featured_all['parsed']['description']
            }
        
        all_html = tmpl.render(
            lang='en',
            R2_PUBLIC_URL=R2_PUBLIC_URL,
            menu=menu_texts,
            articles=articles_for_template,
            featured_article=featured_for_template,
            canonical_url=f"{R2_PUBLIC_URL}/explore/all-articles/en.html",
            og_image=articles_for_template[0]['image'] if articles_for_template else "",
            alternate_langs=[],
            hero={'html': hero_html, 'show': True}
        )
        s3.put_object(Bucket=R2_BUCKET, Key="articles_ready/explore/all-articles/en.html", Body=all_html.encode('utf-8'), ContentType='text/html')
        timings["ALL_ARTICLES"] = time.time() - t_start
        print(f"   ✅ All articles: {timings['ALL_ARTICLES']:.2f}s")
    
      # 10. ZAMAN RAPORU
    print("\n" + "=" * 60)
    print("📊 ZAMAN RAPORU")
    print("=" * 60)
    total = 0
    for name, duration in sorted(timings.items(), key=lambda x: x[1], reverse=True):
        print(f"   {name:25}: {duration:8.2f} saniye")
        total += duration
    print(f"   {'TOPLAM (ölçülen)':25}: {total:8.2f} saniye")
    print("=" * 60)
    
    print("\n🏁 DESIGNER TAMAMLANDI!")

if __name__ == "__main__":
    designer()
