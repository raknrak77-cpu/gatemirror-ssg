import os
import random
import json
import boto3
import requests
from datetime import datetime
from botocore.client import Config
from jinja2 import Template
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib

from makeup import (
    get_all_raw_articles,
    build_alternate_langs_dict,
    get_menu_texts,
    get_category_name,
    get_category_description,
    generate_sitemap,
    generate_robots_txt
)
from hero_bot import render_hero

# ================= KONFIGURASYON =================
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

# ================= CACHE =================
hero_cache = {}
template_cache = {}
template_raw_cache = {}

def get_cached_hero(page_type, lang, category=None):
    cache_key = f"{page_type}_{lang}_{category or ''}"
    if cache_key not in hero_cache:
        hero_cache[cache_key] = render_hero(page_type, lang, category)
    return hero_cache[cache_key]

def get_cached_template(template_str, template_name):
    if template_name not in template_cache:
        template_cache[template_name] = Template(template_str)
    return template_cache[template_name]

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

def upload_templates_to_r2():
    templates_dir = "templates"
    if not os.path.exists(templates_dir):
        return
    for file in os.listdir(templates_dir):
        if file.endswith('.html'):
            local_path = os.path.join(templates_dir, file)
            try:
                s3.upload_file(local_path, R2_BUCKET, f"templates/{file}")
            except:
                pass

# ================= RENDER FONKSIYONLARI =================

def render_single_page(article, alt_langs, template_str, menu_texts, related_articles):
    tmpl = get_cached_template(template_str, 'single')
    parsed = article['parsed']
    canonical = f"{R2_PUBLIC_URL}{article['url']}"
    
    author_name = article.get('author_name', parsed.get('author', 'Gatemirror Expert'))
    author_title = article.get('author_title', '')
    author_bio = article.get('author_bio', '')
    author_avatar = article.get('author_avatar', '')
    
    hero_html = get_cached_hero('article', article['lang'])
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

def render_home_page(lang, articles, featured_article, template_str, menu_texts, alternate_langs, manifesto_html=""):
    tmpl = get_cached_template(template_str, 'home')
    canonical = f"{R2_PUBLIC_URL}/{lang}/"
    og_image = articles[0]['image'] if articles else ""
    hero_html = get_cached_hero('home', lang)
    return tmpl.render(
        lang=lang, R2_PUBLIC_URL=R2_PUBLIC_URL, menu=menu_texts,
        articles=articles, featured_article=featured_article,
        canonical_url=canonical, og_image=og_image,
        alternate_langs=alternate_langs, hero={'html': hero_html, 'show': True},
        manifesto=manifesto_html
    )

def render_list_page(lang, category, cat_articles, featured_article, trending_articles, template_str, menu_texts, alternate_langs):
    tmpl = get_cached_template(template_str, 'list')
    category_name = get_category_name(lang, category)
    category_description = get_category_description(lang, category)
    category_url = f"{R2_PUBLIC_URL}/{lang}/{category}/"
    og_image = cat_articles[0]['image'] if cat_articles else ""
    hero_html = get_cached_hero('category', lang, category)
    return tmpl.render(
        lang=lang, R2_PUBLIC_URL=R2_PUBLIC_URL, menu=menu_texts,
        category_name=category_name, category_description=category_description,
        category_url=category_url, category=category, og_image=og_image,
        articles=cat_articles, featured_article=featured_article,
        trending_articles=trending_articles, pagination=None, guide_articles=[],
        alternate_langs=alternate_langs, hero={'html': hero_html, 'show': True}
    )

def render_all_articles_page(lang, all_articles, featured_article, template_str, menu_texts, alternate_langs):
    tmpl = get_cached_template(template_str, 'all-articles')
    canonical = f"{R2_PUBLIC_URL}/explore/all-articles/{lang}.html"
    og_image = all_articles[0]['parsed']['cover_image'] if all_articles else ""
    hero_html = get_cached_hero('special', lang, 'all-articles')
    articles_for_template = []
    for a in all_articles:
        articles_for_template.append({
            'url': a['url'], 'image': a['parsed']['cover_image'],
            'title': a['parsed']['title'], 'reading_time': a['parsed']['reading_time'],
            'views': a['parsed']['views'], 'excerpt': a['parsed']['description'],
            'category_name': get_category_name(lang, a['category'])
        })
    featured_for_template = None
    if featured_article:
        featured_for_template = {
            'url': featured_article['url'], 'image': featured_article['parsed']['cover_image'],
            'title': featured_article['parsed']['title'], 'date': featured_article['parsed']['date'],
            'reading_time': featured_article['parsed']['reading_time'],
            'views': featured_article['parsed']['views'], 'excerpt': featured_article['parsed']['description']
        }
    return tmpl.render(
        lang=lang, R2_PUBLIC_URL=R2_PUBLIC_URL, menu=menu_texts,
        articles=articles_for_template, featured_article=featured_for_template,
        canonical_url=canonical, og_image=og_image,
        alternate_langs=alternate_langs, hero={'html': hero_html, 'show': True}
    )

# ================= SIZE KONTROL VE LOG =================

def log_size_report(entries, report_type="publisher"):
    """Size raporu kaydet (JSON formatında)"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_key = f"reports/size_report_{report_type}_{timestamp}.json"
    
    report = {
        "generated": datetime.now().isoformat(),
        "type": report_type,
        "min_size_kb": MIN_SIZE_KB,
        "entries": entries
    }
    
    try:
        s3.put_object(
            Bucket=R2_BUCKET,
            Key=report_key,
            Body=json.dumps(report, indent=2, ensure_ascii=False).encode('utf-8'),
            ContentType='application/json'
        )
        print(f"   📊 Rapor kaydedildi: {report_key}")
        return report_key
    except Exception as e:
        print(f"   ⚠️ Rapor kaydedilemedi: {e}")
        return None

def check_and_write_article(article, alt_langs, single_tpl, menu_texts, related_for_template, failed_log):
    """Tek bir makaleyi kontrol et + yaz (51 KB kontrolü)"""
    try:
        single_html = render_single_page(article, alt_langs, single_tpl, menu_texts, related_for_template)
        if not single_html:
            return None
        
        html_bytes = single_html.encode('utf-8')
        size_kb = len(html_bytes) / 1024
        
        target_key = article['url'].lstrip('/').replace('articles/', 'articles_ready/', 1)
        
        if size_kb < MIN_SIZE_KB:
            # KÜÇÜK MAKALE: YAYINLANMA, LOGLA
            entry = {
                "timestamp": datetime.now().isoformat(),
                "source": "publisher",
                "status": "REJECTED",
                "url": article['url'],
                "target_key": target_key,
                "size_kb": round(size_kb, 2),
                "min_required_kb": MIN_SIZE_KB,
                "hash": article.get('hash'),
                "lang": article['lang'],
                "category": article['category'],
                "title": article['parsed']['title'][:100]
            }
            failed_log.append(entry)
            print(f"   ⚠️ REDdedildi (Publisher): {target_key} -> {size_kb:.1f} KB (<{MIN_SIZE_KB} KB)")
            return None
        
        # BOYUT YETERLİ: YAYINLA
        s3.put_object(Bucket=R2_BUCKET, Key=target_key, Body=html_bytes, ContentType='text/html')
        print(f"   ✅ Yayınlandı: {target_key} ({size_kb:.1f} KB)")
        return target_key
        
    except Exception as e:
        print(f"   ❌ Hata: {article.get('url', 'unknown')} - {e}")
        return None

# ================= ARTICLES.JSON ÜRETIMI =================

def generate_articles_json(all_articles):
    articles_list = []
    for article in all_articles:
        parsed = article['parsed']
        articles_list.append({
            'hash': article.get('hash', ''), 'slug': article.get('slug', ''),
            'url': article['url'], 'canonical': f"{R2_PUBLIC_URL}{article['url']}",
            'lang': article['lang'], 'category': article['category'],
            'category_name': get_category_name(article['lang'], article['category']),
            'title': parsed['title'], 'description': parsed['description'],
            'summary': parsed.get('summary_text', ''),
            'author': {'name': parsed.get('author', 'Gatemirror Expert'), 'title': parsed.get('author_title', ''),
                       'bio': parsed.get('author_bio', ''), 'avatar': parsed.get('author_avatar', '')},
            'date': parsed['date'], 'datetime': parsed.get('datetime_iso', ''),
            'reading_time': parsed['reading_time'], 'word_count': parsed.get('word_count', 0),
            'views': parsed['views'], 'cover_image': parsed['cover_image'],
            'content_image_1': parsed.get('content_image_1', ''),
            'content_image_2': parsed.get('content_image_2', ''), 'tags': []
        })
    for article in articles_list:
        alt_langs = {}
        for other in articles_list:
            if other['category'] == article['category'] and other['hash'] == article['hash'] and other['lang'] != article['lang']:
                alt_langs[other['lang']] = other['url']
        article['alternate_langs'] = alt_langs
    final_json = {"version": "1.1", "generated": datetime.now().isoformat(),
                  "total_articles": len(articles_list), "articles": articles_list}
    s3.put_object(Bucket=R2_BUCKET, Key='articles.json',
                  Body=json.dumps(final_json, indent=2, ensure_ascii=False).encode('utf-8'),
                  ContentType='application/json')
    print(f"   ✅ articles.json oluşturuldu ({len(articles_list)} makale)")

# ================= ANA PUBLISHER =================

def publisher():
    print("=" * 60)
    print("🚀 PUBLISHER BOT v43 - 51 KB KONTROLLÜ")
    print("   ❌ Küçük makaleler YAYINLANMAYACAK")
    print("   📊 Detaylı rapor (R2/reports/)")
    print("=" * 60)
    
    upload_templates_to_r2()
    
    single_tpl = get_template_from_r2("single.html")
    home_tpl = get_template_from_r2("home.html")
    list_tpl = get_template_from_r2("list.html")
    all_articles_tpl = get_template_from_r2("all-articles.html")
    
    if not single_tpl or not home_tpl or not list_tpl:
        print("❌ Template'ler alınamadı.")
        return
    
    all_articles = get_all_raw_articles()
    if not all_articles:
        print("❌ Hiç makale bulunamadı.")
        return
    
    print(f"\n📊 Toplam {len(all_articles)} makale bulundu.")
    
    alt_dict = build_alternate_langs_dict(all_articles)
    languages = ['en', 'es', 'de', 'fr']
    total_pages = 0
    failed_log = []  # Publisher tarafından reddedilenler
    
    # Manifesto
    manifesto_html = ""
    try:
        manifesto_response = s3.get_object(Bucket=R2_BUCKET, Key='templates/manifesto.html')
        manifesto_html = manifesto_response['Body'].read().decode('utf-8')
        manifesto_html = manifesto_html.replace("{{ R2_PUBLIC_URL }}", R2_PUBLIC_URL)
    except:
        pass
    
    for lang in languages:
        print(f"\n{'=' * 40}")
        print(f"🌍 {lang.upper()} işleniyor...")
        
        lang_articles = [a for a in all_articles if a['lang'] == lang]
        if not lang_articles:
            continue
        
        lang_articles.sort(key=lambda x: x['sort_datetime'], reverse=True)
        menu_texts = get_menu_texts(lang)
        
        # MAKALELERİ KONTROLLÜ YAZ
        print(f"\n📝 Makaleler işleniyor (51 KB kontrolü)...")
        
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
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = []
            for article, alt_langs, related_for_template in articles_to_write:
                future = executor.submit(check_and_write_article, article, alt_langs, single_tpl, menu_texts, related_for_template, failed_log)
                futures.append(future)
            for future in as_completed(futures):
                if future.result():
                    total_pages += 1
        
        # HOME PAGE
        featured = lang_articles[0] if lang_articles else None
        featured_for_home = None
        if featured:
            featured_for_home = {
                'url': featured['url'], 'image': featured['parsed']['cover_image'],
                'title': featured['parsed']['title'], 'date': featured['parsed']['date'],
                'reading_time': featured['parsed']['reading_time'], 'views': featured['parsed']['views'],
                'excerpt': featured['parsed']['description']
            }
        articles_for_home = []
        for a in lang_articles[:12]:
            articles_for_home.append({
                'url': a['url'], 'image': a['parsed']['cover_image'], 'title': a['parsed']['title'],
                'reading_time': a['parsed']['reading_time'], 'views': a['parsed']['views'],
                'excerpt': a['parsed']['description']
            })
        home_alt_langs = [{'lang': l, 'url': f"{R2_PUBLIC_URL}/{l}/"} for l in languages if l != lang]
        home_html = render_home_page(lang, articles_for_home, featured_for_home, home_tpl, menu_texts, home_alt_langs, manifesto_html)
        if home_html:
            s3.put_object(Bucket=R2_BUCKET, Key=f"articles_ready/{lang}/index.html", Body=home_html.encode('utf-8'), ContentType='text/html')
            total_pages += 1
        
        # KATEGORİ SAYFALARI
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
                    'url': featured_cat['url'], 'image': featured_cat['parsed']['cover_image'],
                    'title': featured_cat['parsed']['title'], 'date': featured_cat['parsed']['date'],
                    'reading_time': featured_cat['parsed']['reading_time'], 'views': featured_cat['parsed']['views'],
                    'excerpt': featured_cat['parsed']['description']
                }
            trending = []
            for a in cat_articles[1:4]:
                trending.append({
                    'url': a['url'], 'image': a['parsed']['cover_image'], 'title': a['parsed']['title'],
                    'reading_time': a['parsed']['reading_time'], 'views': a['parsed']['views'],
                    'excerpt': a['parsed']['description']
                })
            articles_for_list = []
            for a in cat_articles:
                articles_for_list.append({
                    'url': a['url'], 'image': a['parsed']['cover_image'], 'title': a['parsed']['title'],
                    'reading_time': a['parsed']['reading_time'], 'views': a['parsed']['views'],
                    'excerpt': a['parsed']['description']
                })
            cat_alt_langs = [{'lang': l, 'url': f"{R2_PUBLIC_URL}/{l}/{category}/"} for l in languages if l != lang]
            list_html = render_list_page(lang, category, articles_for_list, featured_for_cat, trending, list_tpl, menu_texts, cat_alt_langs)
            if list_html:
                s3.put_object(Bucket=R2_BUCKET, Key=f"articles_ready/{lang}/{category}/index.html", Body=list_html.encode('utf-8'), ContentType='text/html')
                total_pages += 1
        
        # ALL ARTICLES
        if all_articles_tpl:
            explore_alt_langs = [{'lang': l, 'url': f"{R2_PUBLIC_URL}/explore/all-articles/{l}.html"} for l in languages if l != lang]
            featured_all = lang_articles[0] if lang_articles else None
            all_html = render_all_articles_page(lang, lang_articles, featured_all, all_articles_tpl, menu_texts, explore_alt_langs)
            if all_html:
                s3.put_object(Bucket=R2_BUCKET, Key=f"articles_ready/explore/all-articles/{lang}.html", Body=all_html.encode('utf-8'), ContentType='text/html')
                total_pages += 1
    
     # RAPOR KAYDET
    if failed_log:
        log_size_report(failed_log, "publisher")
        print(f"\n⚠️ Publisher TARAFINDAN REDDEDİLEN: {len(failed_log)} makale")
    else:
        print(f"\n✅ Tüm makaleler Publisher'da 51 KB kontrolünü geçti")
    
    # SITEMAP & ROBOTS & ARTICLES.JSON
    sitemap_xml = generate_sitemap(all_articles, alt_dict)
    s3.put_object(Bucket=R2_BUCKET, Key='sitemap.xml', Body=sitemap_xml.encode('utf-8'), ContentType='application/xml')
    robots_txt = generate_robots_txt()
    s3.put_object(Bucket=R2_BUCKET, Key='robots.txt', Body=robots_txt.encode('utf-8'), ContentType='text/plain')
    generate_articles_json(all_articles)
    
    print(f"\n{'=' * 40}")
    print("🏁 PUBLISHER v43 TAMAMLANDI!")
    print(f"   ✅ Toplam sayfa: {total_pages}")
    print(f"   ❌ Reddedilen makale: {len(failed_log)}")
    print(f"{'=' * 40}")

if __name__ == "__main__":
    publisher()
