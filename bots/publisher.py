import os
import re
import random
import boto3
import requests
from datetime import datetime
from botocore.client import Config
from jinja2 import Template

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

# ================= YARDIMCI FONKSİYONLAR =================
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

def get_menu_texts(lang):
    texts = {
        'en': {'home': 'HOME', 'wellness': 'WELLNESS', 'tech': 'TECH & AI', 
               'future-economy': 'FUTURE ECONOMY', 'eco': 'ECO & SUSTAINABLE', 'elearning': 'E-LEARNING'},
        'es': {'home': 'INICIO', 'wellness': 'BIENESTAR', 'tech': 'TECNOLOGÍA & IA',
               'future-economy': 'ECONOMÍA FUTURA', 'eco': 'ECO & SOSTENIBLE', 'elearning': 'E-APRENDIZAJE'},
        'de': {'home': 'STARTSEITE', 'wellness': 'WOHLBEFINDEN', 'tech': 'TECHNOLOGIE & KI',
               'future-economy': 'ZUKUNFTSWIRTSCHAFT', 'eco': 'ÖKO & NACHHALTIG', 'elearning': 'E-LEARNING'},
        'fr': {'home': 'ACCUEIL', 'wellness': 'BIEN-ÊTRE', 'tech': 'TECHNOLOGIE & IA',
               'future-economy': 'ÉCONOMIE FUTURE', 'eco': 'ÉCO & DURABLE', 'elearning': 'E-APPRENTISSAGE'}
    }
    return texts.get(lang, texts['en'])

def get_category_name(lang, category):
    names = {
        'en': {'wellness': 'WELLNESS', 'tech': 'TECH & AI', 'future-economy': 'FUTURE ECONOMY',
               'eco': 'ECO & SUSTAINABLE', 'elearning': 'E-LEARNING'},
        'es': {'wellness': 'BIENESTAR', 'tech': 'TECNOLOGÍA & IA', 'future-economy': 'ECONOMÍA FUTURA',
               'eco': 'ECO & SOSTENIBLE', 'elearning': 'E-APRENDIZAJE'},
        'de': {'wellness': 'WOHLBEFINDEN', 'tech': 'TECHNOLOGIE & KI', 'future-economy': 'ZUKUNFTSWIRTSCHAFT',
               'eco': 'ÖKO & NACHHALTIG', 'elearning': 'E-LEARNING'},
        'fr': {'wellness': 'BIEN-ÊTRE', 'tech': 'TECHNOLOGIE & IA', 'future-economy': 'ÉCONOMIE FUTURE',
               'eco': 'ÉCO & DURABLE', 'elearning': 'E-APPRENTISSAGE'}
    }
    return names.get(lang, names['en']).get(category, category.upper())

def get_category_description(lang, category):
    descriptions = {
        'en': {
            'wellness': 'Deep insights on physical, mental, and emotional well-being.',
            'tech': 'Latest developments in AI, software, and digital transformation.',
            'future-economy': 'Finance, DeFi, tokenomics, and algorithmic trading.',
            'eco': 'Sustainable living, green energy, and climate solutions.',
            'elearning': 'Online education, career development, and digital skills.'
        },
        'es': {
            'wellness': 'Perspectivas profundas sobre bienestar físico, mental y emotional.',
            'tech': 'Últimos avances en IA, software y transformación digital.',
            'future-economy': 'Finanzas, DeFi, tokenomics y trading algorítmico.',
            'eco': 'Vida sostenible, energía verde y soluciones climáticas.',
            'elearning': 'Educación en línea, desarrollo profesional y habilidades digitales.'
        },
        'de': {
            'wellness': 'Tiefe Einblicke in körperliches, geistiges und emotionales Wohlbefinden.',
            'tech': 'Neueste Entwicklungen in KI, Software und digitaler Transformation.',
            'future-economy': 'Finanzen, DeFi, Tokenomics und algorithmischer Handel.',
            'eco': 'Nachhaltiges Leben, grüne Energie und Klimaschutzlösungen.',
            'elearning': 'Online-Bildung, Karriereentwicklung und digitale Kompetenzen.'
        },
        'fr': {
            'wellness': 'Aperçus approfondis sur le bien-être physique, mental et émotionnel.',
            'tech': 'Derniers développements en IA, logiciels et transformation numérique.',
            'future-economy': 'Finance, DeFi, tokenomics et trading algorithmique.',
            'eco': 'Vie durable, énergie verte et solutions climatiques.',
            'elearning': 'Éducation en ligne, développement de carrière et compétences numériques.'
        }
    }
    return descriptions.get(lang, descriptions.get('en', {})).get(category, '')

def calculate_reading_time(html_content):
    text = re.sub(r'<[^>]+>', ' ', html_content)
    words = re.findall(r'\b\w+\b', text)
    return max(1, len(words) // 200)

def generate_views(hash_id):
    random.seed(hash_id)
    return random.randint(200, 5000)

def image_exists(url):
    try:
        resp = requests.head(url, timeout=5)
        return resp.status_code == 200
    except:
        return False

def parse_article_html(html_content, lang, category, hash_id, yil, ay, r2_base):
    """
    HTML içeriğini parse eder.
    Görseller için önce yıl/ay bazlı yeni yapıyı dener, yoksa eski yapıya düşer.
    """
    title_match = re.search(r'<h1>(.*?)</h1>', html_content, re.DOTALL)
    title = title_match.group(1).strip() if title_match else ""
    
    meta_match = re.search(r'<!-- META: author=(.*?), datetime=(.*?) -->', html_content)
    if meta_match:
        author = meta_match.group(1).strip()
        sort_datetime_raw = meta_match.group(2).strip()
        sort_datetime = sort_datetime_raw
        sort_date = sort_datetime_raw[:10]
        try:
            display_date = datetime.strptime(sort_date, "%Y-%m-%d").strftime("%d %B %Y")
        except:
            display_date = sort_date
    else:
        author = "Gatemirror Expert"
        sort_datetime = None
        sort_date = None
        display_date = datetime.now().strftime("%d %B %Y")
    
    note_match = re.search(r'<div class="editors-note">(.*?)</div>', html_content, re.DOTALL)
    editors_note = note_match.group(1).strip() if note_match else ""
    
    takeaway_match = re.search(r'<h2>Key Takeaways</h2>\s*<ul>(.*?)</ul>', html_content, re.DOTALL | re.IGNORECASE)
    if takeaway_match:
        items = re.findall(r'<li>(.*?)</li>', takeaway_match.group(1), re.DOTALL)
        summary_html = "".join([f"<li>{item.strip()}</li>" for item in items])
    else:
        summary_html = "<li>No summary available</li>"
    
    sources_match = re.search(r'<div class="sources">.*?<ul>(.*?)</ul>.*?</div>', html_content, re.DOTALL | re.IGNORECASE)
    if sources_match:
        items = re.findall(r'<li>(.*?)</li>', sources_match.group(1), re.DOTALL)
        sources_html = "".join([f"<li>{item.strip()}</li>" for item in items])
    else:
        sources_html = "<li>Sources not available</li>"
    content_clean = html_content
    content_clean = re.sub(r'<!-- META:.*?-->', '', content_clean, flags=re.DOTALL)
    content_clean = re.sub(r'<div class="editors-note">.*?</div>', '', content_clean, flags=re.DOTALL)
    # Key Takeaways tekrarlarını temizle
    content_clean = re.sub(r'(<h2>Key Takeaways</h2>\s*<ul>.*?</ul>){2,}', 
                       r'<h2>Key Takeaways</h2>\n<ul>\n  <li>No summary available</li>\n</ul>', 
                       content_clean, flags=re.DOTALL | re.IGNORECASE)
    content_clean = re.sub(r'<div class="sources">.*?</div>', '', content_clean, flags=re.DOTALL)
    content_clean = re.sub(r'<h1>.*?</h1>', '', content_clean, flags=re.DOTALL)  # h1 tekrarını engeller
    content_clean = content_clean.strip()

    reading_time = calculate_reading_time(content_clean)
    views = generate_views(hash_id)
    
    plain_text = re.sub(r'<[^>]+>', '', content_clean[:500])
    description = plain_text[:150].strip() + ("..." if len(plain_text) > 150 else "")
    if not description:
        description = title
    
    # Görsel URL'leri: Önce yeni yapıyı dene (yıl/ay), yoksa eski yapı
    if yil and ay:
        base_new = f"{r2_base}/images/{yil}/{ay}/{category}/{hash_id}"
        base_old = f"{r2_base}/images/{category}/{hash_id}"
    else:
        base_new = None
        base_old = f"{r2_base}/images/{category}/{hash_id}"
    
    # Kapak
    if base_new and image_exists(f"{base_new}_kapak.webp"):
        cover_image = f"{base_new}_kapak.webp"
    else:
        cover_image = f"{base_old}_kapak.webp"
    
    # İç görsel 1
    if base_new:
        if image_exists(f"{base_new}_icerik_1.webp"):
            content_image_1 = f"{base_new}_icerik_1.webp"
        elif image_exists(f"{base_new}_icerik.webp"):
            content_image_1 = f"{base_new}_icerik.webp"
        elif image_exists(f"{base_old}_icerik_1.webp"):
            content_image_1 = f"{base_old}_icerik_1.webp"
        else:
            content_image_1 = f"{base_old}_icerik.webp"
    else:
        if image_exists(f"{base_old}_icerik_1.webp"):
            content_image_1 = f"{base_old}_icerik_1.webp"
        else:
            content_image_1 = f"{base_old}_icerik.webp"
    
    # İç görsel 2
    if base_new and image_exists(f"{base_new}_icerik_2.webp"):
        content_image_2 = f"{base_new}_icerik_2.webp"
    else:
        content_image_2 = f"{base_old}_icerik_2.webp"
    
    return {
        'title': title,
        'author': author,
        'date': display_date,
        'sort_date': sort_date,
        'sort_datetime': sort_datetime,
        'editors_note': editors_note,
        'summary': summary_html,
        'sources': sources_html,
        'content': content_clean,
        'cover_image': cover_image,
        'content_image_1': content_image_1,
        'content_image_2': content_image_2,
        'reading_time': reading_time,
        'views': views,
        'description': description,
        'hash': hash_id,
        'category': category,
        'lang': lang
    }

def get_all_articles_all_langs():
    languages = ['en', 'es', 'de', 'fr']
    all_articles = []
    for lang in languages:
        prefix = f"articles/{lang}/"
        try:
            response = s3.list_objects_v2(Bucket=R2_BUCKET, Prefix=prefix)
            if 'Contents' not in response:
                continue
        except Exception as e:
            print(f"⚠️ R2 listeleme hatası ({lang}): {e}")
            continue
        for obj in response['Contents']:
            key = obj['Key']
            if not key.endswith('.html') or key.endswith('index.html'):
                continue
            
            # Parse path: articles/en/wellness/2026/04/hash-slug.html  veya eski: articles/en/wellness/hash.html
            rel_path = key.replace(prefix, '')
            parts = rel_path.split('/')
            
            # Yeni format (yıl/ay/slug)
            if len(parts) >= 4:
                category = parts[0]
                yil = parts[1]
                ay = parts[2]
                filename = parts[3]
                if '-' in filename:
                    hash_id = filename.split('-')[0]
                    slug = filename.replace(hash_id + '-', '').replace('.html', '')
                else:
                    hash_id = filename.replace('.html', '')
                    slug = None
            # Eski format (düz hash.html)
            elif len(parts) >= 2:
                category = parts[0]
                filename = parts[1]
                hash_id = filename.replace('.html', '')
                yil = None
                ay = None
                slug = None
            else:
                continue
            
            try:
                file_obj = s3.get_object(Bucket=R2_BUCKET, Key=key)
                html_content = file_obj['Body'].read().decode('utf-8')
                
                # Parse et (yıl/ay bilgisini de gönder)
                parsed = parse_article_html(html_content, lang, category, hash_id, yil, ay, R2_PUBLIC_URL)
                
                # Article URL oluştur (yeni yapı varsa onu kullan)
                if yil and ay and slug:
                    article_url = f"/articles/{lang}/{category}/{yil}/{ay}/{hash_id}-{slug}.html"
                else:
                    article_url = f"/articles/{lang}/{category}/{hash_id}.html"
                
                sort_datetime = parsed['sort_datetime']
                if sort_datetime is None:
                    sort_datetime = obj['LastModified'].strftime("%Y-%m-%d %H:%M:%S")
                    sort_date = sort_datetime[:10]
                else:
                    sort_date = parsed['sort_date']
                
                all_articles.append({
                    'lang': lang,
                    'category': category,
                    'hash': hash_id,
                    'yil': yil,
                    'ay': ay,
                    'slug': slug,
                    'parsed': parsed,
                    'url': article_url,
                    'sort_date': sort_date,
                    'sort_datetime': sort_datetime
                })
            except Exception as e:
                print(f"⚠️ {key} okunamadı: {e}")
    return all_articles

def build_alternate_langs_dict(all_articles):
    alt_dict = {}
    for article in all_articles:
        key = (article['category'], article['hash'])
        alt_dict.setdefault(key, []).append({
            'lang': article['lang'],
            'url': f"{R2_PUBLIC_URL}{article['url']}"
        })
    return alt_dict

def generate_sitemap(all_articles, alt_dict, base_url):
    urls = []
    languages = ['en', 'es', 'de', 'fr']
    categories = ['wellness', 'tech', 'future-economy', 'eco', 'elearning']
    
    for lang in languages:
        urls.append({
            'loc': f"{base_url}/{lang}/",
            'priority': '1.0',
            'changefreq': 'daily',
            'lastmod': datetime.now().strftime("%Y-%m-%d"),
            'alternates': [{'lang': l, 'url': f"{base_url}/{l}/"} for l in languages if l != lang]
        })
    
    for lang in languages:
        for cat in categories:
            urls.append({
                'loc': f"{base_url}/{lang}/{cat}/",
                'priority': '0.8',
                'changefreq': 'weekly',
                'lastmod': datetime.now().strftime("%Y-%m-%d"),
                'alternates': [{'lang': l, 'url': f"{base_url}/{l}/{cat}/"} for l in languages if l != lang]
            })
    
    for article in all_articles:
        key = (article['category'], article['hash'])
        alternates = alt_dict.get(key, [])
        urls.append({
            'loc': f"{base_url}{article['url']}",
            'lastmod': article['sort_date'],
            'priority': '0.6',
            'changefreq': 'monthly',
            'alternates': alternates
        })
    
    static_pages = [
        ('/about-us.html', '0.4'),
        ('/contact.html', '0.4'),
        ('/privacy-policy.html', '0.3')
    ]
    for path, priority in static_pages:
        urls.append({
            'loc': f"{base_url}{path}",
            'priority': priority,
            'lastmod': datetime.now().strftime("%Y-%m-%d"),
            'alternates': []
        })
    
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">\n'
    for url in urls:
        xml += '    <url>\n'
        xml += f'        <loc>{url["loc"]}</loc>\n'
        if 'lastmod' in url and url['lastmod']:
            xml += f'        <lastmod>{url["lastmod"]}</lastmod>\n'
        if 'changefreq' in url:
            xml += f'        <changefreq>{url["changefreq"]}</changefreq>\n'
        xml += f'        <priority>{url["priority"]}</priority>\n'
        for alt in url.get('alternates', []):
            xml += f'        <xhtml:link rel="alternate" hreflang="{alt["lang"]}" href="{alt["url"]}"/>\n'
        xml += '    </url>\n'
    xml += '</urlset>'
    return xml

def generate_robots_txt(base_url):
    return f"""# Tüm arama motorlarına izin ver
User-agent: *
Allow: /

# Sitemap'in yeri
Sitemap: {base_url}/sitemap.xml

# Tarayıcı hız sınırı (isteğe bağlı)
Crawl-delay: 1

# Engellenen alanlar
Disallow: /templates/
Disallow: /*.json$
Disallow: /tmp/
Disallow: /private/
"""

def render_single_page(article, alt_langs, template_str, menu_texts, related_articles):
    tmpl = Template(template_str)
    parsed = article['parsed']
    canonical = f"{R2_PUBLIC_URL}{article['url']}"
    return tmpl.render(
        lang=article['lang'], title=parsed['title'], description=parsed['description'],
        canonical_url=canonical, author=parsed['author'], date=parsed['date'],
        editors_note=parsed['editors_note'], summary=parsed['summary'], content=parsed['content'],
        sources=parsed['sources'], cover_image=parsed['cover_image'],
        content_image_1=parsed['content_image_1'], content_image_2=parsed['content_image_2'],
        reading_time=parsed['reading_time'], view_count=parsed['views'],
        alternate_langs=alt_langs, menu=menu_texts, related_articles=related_articles
    )

def render_home_page(lang, articles, featured_article, template_str, menu_texts, alternate_langs):
    tmpl = Template(template_str)
    canonical = f"{R2_PUBLIC_URL}/{lang}/"
    og_image = articles[0]['image'] if articles else ""
    return tmpl.render(
        lang=lang, menu=menu_texts, articles=articles, featured_article=featured_article,
        canonical_url=canonical, og_image=og_image, alternate_langs=alternate_langs
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

def publisher():
    print("🚀 Publisher Bot (Sitemap + Hreflang + robots.txt) başlatılıyor...")
    upload_templates_to_r2()
    
    single_tpl = get_template_from_r2("single.html")
    home_tpl = get_template_from_r2("home.html")
    list_tpl = get_template_from_r2("list.html")
    if not single_tpl or not home_tpl or not list_tpl:
        print("❌ Template'ler alınamadı.")
        return
    
    all_articles = get_all_articles_all_langs()
    if not all_articles:
        print("❌ Hiç makale bulunamadı.")
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
            same_cat = [a for a in lang_articles if a['category'] == article['category'] and a['hash'] != article['hash']]
            related = random.sample(same_cat, min(3, len(same_cat)))
            related_for_template = [{'url': r['url'], 'image': r['parsed']['cover_image'], 'title': r['parsed']['title']} for r in related]
            single_html = render_single_page(article, alt_langs, single_tpl, menu_texts, related_for_template)
            if single_html:
                target_key = article['url'].lstrip('/')
                s3.put_object(Bucket=R2_BUCKET, Key=target_key, Body=single_html.encode('utf-8'), ContentType='text/html')
                print(f"   ✅ Makale: {target_key}")
        
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
    
    print("\n📊 Sitemap oluşturuluyor (hreflang ile)...")
    sitemap_xml = generate_sitemap(all_articles, alt_dict, R2_PUBLIC_URL)
    s3.put_object(Bucket=R2_BUCKET, Key='sitemap.xml', Body=sitemap_xml.encode('utf-8'), ContentType='application/xml')
    print("   ✅ Sitemap yüklendi: sitemap.xml")
    
    print("🤖 robots.txt oluşturuluyor...")
    robots_txt = generate_robots_txt(R2_PUBLIC_URL)
    s3.put_object(Bucket=R2_BUCKET, Key='robots.txt', Body=robots_txt.encode('utf-8'), ContentType='text/plain')
    print("   ✅ robots.txt yüklendi: robots.txt")
    
    print("\n🏁 Publisher tamamlandı.")

if __name__ == "__main__":
    publisher()
