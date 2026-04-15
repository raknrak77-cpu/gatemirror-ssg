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

# Import from hero_bot
from hero_bot import render_hero, get_hero_data

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
    """templates/ klasöründeki tüm HTML dosyalarını R2'ye yükler"""
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
    """R2'den template içeriğini alır, yoksa local'den dener"""
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
    """
    Tek makale sayfasını render eder
    Hero: article tipinde (show: false varsayılan)
    """
    tmpl = Template(template_str)
    parsed = article['parsed']
    canonical = f"{R2_PUBLIC_URL}{article['url']}"
    
    author_name = article.get('author_name', parsed.get('author', 'Gatemirror Expert'))
    author_title = article.get('author_title', '')
    author_bio = article.get('author_bio', '')
    author_avatar = article.get('author_avatar', '')
    
    # Hero verisini al (article tipinde - genellikle show: false)
    hero_html = render_hero('article', article['lang'])
    hero_data = get_hero_data('article', article['lang'])
    
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
        hero={'html': hero_html, 'show': hero_data.get('show', False)}
    )

def render_home_page(lang, articles, featured_article, template_str, menu_texts, alternate_langs):
    """
    Ana sayfayı render eder
    Hero: home tipinde
    """
    tmpl = Template(template_str)
    canonical = f"{R2_PUBLIC_URL}/{lang}/"
    og_image = articles[0]['image'] if articles else ""
    
    # Hero verisini al (home tipinde)
    hero_html = render_hero('home', lang)
    hero_data = get_hero_data('home', lang)
    
    return tmpl.render(
        lang=lang,
        menu=menu_texts,
        articles=articles,
        featured_article=featured_article,
        canonical_url=canonical,
        og_image=og_image,
        alternate_langs=alternate_langs,
        hero={'html': hero_html, 'show': hero_data.get('show', True)}
    )

def render_list_page(lang, category, cat_articles, featured_article, trending_articles, template_str, menu_texts, alternate_langs):
    """
    Kategori listeleme sayfasını render eder
    Hero: category tipinde
    """
    tmpl = Template(template_str)
    category_name = get_category_name(lang, category)
    category_description = get_category_description(lang, category)
    category_url = f"{R2_PUBLIC_URL}/{lang}/{category}/"
    og_image = cat_articles[0]['image'] if cat_articles else ""
    
    # Hero verisini al (category tipinde)
    hero_html = render_hero('category', lang, category)
    hero_data = get_hero_data('category', lang, category)
    
    return tmpl.render(
        lang=lang,
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
        hero={'html': hero_html, 'show': hero_data.get('show', True)}
    )

# ================= ARTICLES.JSON ÜRETİMİ =================

def generate_articles_json(all_articles):
    """Worker'ın random article seçmesi için articles.json oluşturur"""
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
            'description': article['parsed']['description']
        })
    
    articles_json = json.dumps(articles_list, indent=2, ensure_ascii=False)
    s3.put_object(
        Bucket=R2_BUCKET,
        Key='articles.json',
        Body=articles_json.encode('utf-8'),
        ContentType='application/json'
    )
    print("   ✅ articles.json oluşturuldu (random article için)")

# ================= ANA PUBLISHER =================

def publisher():
    print("=" * 60)
    print("🚀 PUBLISHER BOT - Tam Donanımlı")
    print("   ✅ Sitemap + Hreflang + robots.txt")
    print("   ✅ Hero Bot entegre (çok dilli, modüler)")
    print("   ✅ Makale 3 parçaya bölünüyor")
    print("   ✅ AdSense alanı hazır")
    print("=" * 60)
    
    # Template'leri R2'ye yükle
    upload_templates_to_r2()
    
    # Template'leri al
    single_tpl = get_template_from_r2("single.html")
    home_tpl = get_template_from_r2("home.html")
    list_tpl = get_template_from_r2("list.html")
    
    if not single_tpl or not home_tpl or not list_tpl:
        print("❌ Template'ler alınamadı.")
        print(f"   single: {'✅' if single_tpl else '❌'}")
        print(f"   home: {'✅' if home_tpl else '❌'}")
        print(f"   list: {'✅' if list_tpl else '❌'}")
        return
    
    # Tüm makaleleri al
    all_articles = get_all_raw_articles()
    if not all_articles:
        print("❌ Hiç makale bulunamadı (raw-articles/ boş).")
        return
    
    print(f"\n📊 Toplam {len(all_articles)} makale bulundu.")
    
    # Alternatif diller sözlüğü oluştur
    alt_dict = build_alternate_langs_dict(all_articles)
    languages = ['en', 'es', 'de', 'fr']
    
    # Her dil için işlem yap
    for lang in languages:
        print(f"\n{'=' * 40}")
        print(f"🌍 {lang.upper()} işleniyor...")
        print(f"{'=' * 40}")
        
        lang_articles = [a for a in all_articles if a['lang'] == lang]
        if not lang_articles:
            print(f"   ⚠️ {lang.upper()} için makale bulunamadı.")
            continue
        
        # Makaleleri tarihe göre sırala (en yeniden eskiye)
        lang_articles.sort(key=lambda x: x['sort_datetime'], reverse=True)
        menu_texts = get_menu_texts(lang)
        
        # 1. MAKALELERİ RENDER ET
        print(f"\n📝 Makaleler işleniyor...")
        for article in lang_articles:
            key = (article['category'], article['hash'])
            alt_langs = alt_dict.get(key, [])
            
            # İlgili makaleleri bul (aynı cluster veya aynı kategori)
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
                print(f"   ✅ {target_key}")
        
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
            s3.put_object(Bucket=R2_BUCKET, Key=f"articles/{lang}/index.html", Body=home_html.encode('utf-8'), ContentType='text/html')
            print(f"   ✅ articles/{lang}/index.html")
        
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
                s3.put_object(Bucket=R2_BUCKET, Key=f"articles/{lang}/{category}/index.html", Body=list_html.encode('utf-8'), ContentType='text/html')
                print(f"   ✅ articles/{lang}/{category}/index.html ({len(cat_articles)} makale)")
    
    # 4. SITEMAP VE ROBOTS.TXT
    print(f"\n{'=' * 40}")
    print("📊 Sitemap ve robots.txt oluşturuluyor...")
    print(f"{'=' * 40}")
    
    sitemap_xml = generate_sitemap(all_articles, alt_dict)
    s3.put_object(Bucket=R2_BUCKET, Key='sitemap.xml', Body=sitemap_xml.encode('utf-8'), ContentType='application/xml')
    print("   ✅ sitemap.xml yüklendi")
    
    robots_txt = generate_robots_txt()
    s3.put_object(Bucket=R2_BUCKET, Key='robots.txt', Body=robots_txt.encode('utf-8'), ContentType='text/plain')
    print("   ✅ robots.txt yüklendi")
    
    # 5. ARTICLES.JSON (Worker random article için)
    generate_articles_json(all_articles)
    
    # 6. ÖZET RAPORU
    print(f"\n{'=' * 40}")
    print("🏁 PUBLISHER TAMAMLANDI!")
    print(f"{'=' * 40}")
    print(f"\n📊 İstatistikler:")
    print(f"   Toplam makale: {len(all_articles)}")
    for lang in languages:
        count = len([a for a in all_articles if a['lang'] == lang])
        print(f"   {lang.upper()}: {count} makale")
    
    print(f"\n📁 Oluşturulan dosyalar:")
    print(f"   ✅ articles/{lang}/index.html (her dil için ana sayfa)")
    print(f"   ✅ articles/{lang}/{category}/index.html (kategori sayfaları)")
    print(f"   ✅ articles/{lang}/{category}/{yil}/{ay}/{hash}-{slug}.html (makaleler)")
    print(f"   ✅ sitemap.xml")
    print(f"   ✅ robots.txt")
    print(f"   ✅ articles.json")
    print(f"\n🎨 Hero Bot entegre çalışıyor (hero.json ile yönetiliyor)")
    print(f"{'=' * 40}")

if __name__ == "__main__":
    publisher()
