import os
import random
import json
import boto3
import requests
from datetime import datetime
from botocore.client import Config
from jinja2 import Template

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
    try:
        url = f"{R2_PUBLIC_URL}/templates/{template_name}"
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            return resp.text
    except:
        pass
    local_path = os.path.join("templates", template_name)
    if os.path.exists(local_path):
        with open(local_path, 'r', encoding='utf-8') as f:
            return f.read()
    return None

# ================= RENDER FONKSİYONLARI =================

def render_single_page(article, alt_langs, template_str, menu_texts, related_articles):
    tmpl = Template(template_str)
    parsed = article['parsed']
    canonical = f"{R2_PUBLIC_URL}{article['url']}"
    
    # 🔥 YENİ: Yazar bilgilerini al (makeup'tan gelen)
    author_name = article.get('author_name', parsed.get('author', 'Gatemirror Expert'))
    author_title = article.get('author_title', '')
    author_bio = article.get('author_bio', '')
    author_avatar = article.get('author_avatar', '')
    
    return tmpl.render(
        lang=article['lang'],
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
        sources=parsed['sources'],
        cover_image=parsed['cover_image'],
        content_image_1=parsed['content_image_1'],
        content_image_2=parsed['content_image_2'],
        reading_time=parsed['reading_time'],
        view_count=parsed['views'],
        alternate_langs=alt_langs,
        menu=menu_texts,
        related_articles=related_articles
    )

def render_home_page(lang, articles, featured_article, template_str, menu_texts, alternate_langs):
    tmpl = Template(template_str)
    canonical = f"{R2_PUBLIC_URL}/{lang}/"
    og_image = articles[0]['image'] if articles else ""
    return tmpl.render(
        lang=lang, menu=menu_texts, articles=articles, featured_article=featured_article,
        canonical_url=canonical, og_image=og_image, alternate_langs=alternate_langs
    )

def render_list_page(lang, category, cat_articles, featured_article, trending_articles, template_str, menu_texts, alternate_langs):
    tmpl = Template(template_str)
    category_name = get_category_name(lang, category)
    category_description = get_category_description(lang, category)
    category_url = f"{R2_PUBLIC_URL}/{lang}/{category}/"
    og_image = cat_articles[0]['image'] if cat_articles else ""
    return tmpl.render(
        lang=lang, menu=menu_texts, category_name=category_name, category_description=category_description,
        category_url=category_url, og_image=og_image, articles=cat_articles,
        featured_article=featured_article, trending_articles=trending_articles,
        pagination=None, guide_articles=[], alternate_langs=alternate_langs
    )

# ================= ANA PUBLISHER =================

def publisher():
    print("🚀 Publisher Bot (Sitemap + Hreflang + robots.txt) başlatılıyor...")
    upload_templates_to_r2()
    
    single_tpl = get_template_from_r2("single.html")
    home_tpl = get_template_from_r2("home.html")
    list_tpl = get_template_from_r2("list.html")
    if not single_tpl or not home_tpl or not list_tpl:
        print("❌ Template'ler alınamadı.")
        return
    
    # Makeup'ten zenginleştirilmiş makaleleri al (yazar bilgileri içinde)
    all_articles = get_all_raw_articles()
    if not all_articles:
        print("❌ Hiç makale bulunamadı (raw-articles/ boş).")
        return
    
    alt_dict = build_alternate_langs_dict(all_articles)
    languages = ['en', 'es', 'de', 'fr']
    
    for lang in languages:
        print(f"\n🌍 {lang.upper()} işleniyor...")
        lang_articles = [a for a in all_articles if a['lang'] == lang]
        if not lang_articles:
            continue
        
        lang_articles.sort(key=lambda x: x['sort_datetime'], reverse=True)
        menu_texts = get_menu_texts(lang)
        
        for article in lang_articles:
            key = (article['category'], article['hash'])
            alt_langs = alt_dict.get(key, [])
            
            # 🔥 YENİ: cluster bazlı related articles seçimi
            same_cluster = [a for a in lang_articles if a.get('cluster_id') == article.get('cluster_id') and a['hash'] != article['hash']]
            if same_cluster:
                related = random.sample(same_cluster, min(3, len(same_cluster)))
            else:
                same_cat = [a for a in lang_articles if a['category'] == article['category'] and a['hash'] != article['hash']]
                related = random.sample(same_cat, min(3, len(same_cat))) if same_cat else []
            
            related_for_template = [{'url': r['url'], 'image': r['parsed']['cover_image'], 'title': r['parsed']['title']} for r in related]
            single_html = render_single_page(article, alt_langs, single_tpl, menu_texts, related_for_template)
            if single_html:
                target_key = article['url'].lstrip('/')
                s3.put_object(Bucket=R2_BUCKET, Key=target_key, Body=single_html.encode('utf-8'), ContentType='text/html')
                print(f"   ✅ Makale: {target_key}")
        
        # Ana sayfa
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
        home_html = render_home_page(lang, articles_for_home, featured_for_home, home_tpl, menu_texts, home_alt_langs)
        if home_html:
            s3.put_object(Bucket=R2_BUCKET, Key=f"articles/{lang}/index.html", Body=home_html.encode('utf-8'), ContentType='text/html')
            print(f"   ✅ Ana sayfa: articles/{lang}/index.html")
        
        # Kategori sayfaları
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
            cat_alt_langs = []
            for other_lang in languages:
                if other_lang == lang:
                    continue
                cat_alt_langs.append({'lang': other_lang, 'url': f"{R2_PUBLIC_URL}/{other_lang}/{category}/"})
            list_html = render_list_page(lang, category, articles_for_list, featured_for_cat, trending, list_tpl, menu_texts, cat_alt_langs)
            if list_html:
                s3.put_object(Bucket=R2_BUCKET, Key=f"articles/{lang}/{category}/index.html", Body=list_html.encode('utf-8'), ContentType='text/html')
                print(f"   ✅ Kategori arşivi: articles/{lang}/{category}/index.html")
    
    # Sitemap ve robots.txt
    print("\n📊 Sitemap oluşturuluyor (hreflang ile)...")
    sitemap_xml = generate_sitemap(all_articles, alt_dict)
    s3.put_object(Bucket=R2_BUCKET, Key='sitemap.xml', Body=sitemap_xml.encode('utf-8'), ContentType='application/xml')
    print("   ✅ Sitemap yüklendi: sitemap.xml")
    
    print("🤖 robots.txt oluşturuluyor...")
    robots_txt = generate_robots_txt()
    s3.put_object(Bucket=R2_BUCKET, Key='robots.txt', Body=robots_txt.encode('utf-8'), ContentType='text/plain')
    print("   ✅ robots.txt yüklendi: robots.txt")
    
    print("\n🏁 Publisher tamamlandı.")

if __name__ == "__main__":
    publisher()
