import os
import re
import random
import boto3
import requests
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

# ================= MAKYAJ FONKSİYONLARI =================

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

def parse_article_html(html_content, lang, category, hash_id, yil, ay):
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
    content_clean = re.sub(r'<h2>Key Takeaways</h2>\s*<ul>.*?</ul>', '', content_clean, flags=re.DOTALL)
    content_clean = re.sub(r'<div class="sources">.*?</div>', '', content_clean, flags=re.DOTALL)
    content_clean = re.sub(r'<h1>.*?</h1>', '', content_clean, flags=re.DOTALL)
    content_clean = content_clean.strip()

    reading_time = calculate_reading_time(content_clean)
    views = generate_views(hash_id)
    
    plain_text = re.sub(r'<[^>]+>', '', content_clean[:500])
    description = plain_text[:150].strip() + ("..." if len(plain_text) > 150 else "")
    if not description:
        description = title
    
    # Görsel URL'leri
    if yil and ay:
        base_new = f"{R2_PUBLIC_URL}/images/{yil}/{ay}/{category}/{hash_id}"
        base_old = f"{R2_PUBLIC_URL}/images/{category}/{hash_id}"
    else:
        base_new = None
        base_old = f"{R2_PUBLIC_URL}/images/{category}/{hash_id}"
    
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

def get_all_raw_articles():
    """raw-articles/ altındaki tüm HTML dosyalarını listeler ve parse eder"""
    languages = ['en', 'es', 'de', 'fr']
    all_articles = []
    
    for lang in languages:
        prefix = f"raw-articles/{lang}/"
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
            
            rel_path = key.replace(prefix, '')
            parts = rel_path.split('/')
            
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
                
                parsed = parse_article_html(html_content, lang, category, hash_id, yil, ay)
                
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

def generate_sitemap(all_articles, alt_dict):
    base_url = R2_PUBLIC_URL
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

def generate_robots_txt():
    base_url = R2_PUBLIC_URL
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
