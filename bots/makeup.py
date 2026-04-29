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

def calculate_reading_time_and_word_count(html_content):
    text = re.sub(r'<[^>]+>', ' ', html_content)
    words = re.findall(r'\b\w+\b', text)
    word_count = len(words)
    reading_time = max(1, word_count // 200)
    return reading_time, word_count

def generate_views(hash_id):
    random.seed(hash_id)
    return random.randint(200, 5000)

def image_exists(url):
    try:
        resp = requests.head(url, timeout=5)
        return resp.status_code == 200
    except:
        return False

def split_article_content_multilang(content_html, lang):
    """
    Makale içeriğini <h2> başlıklarına göre 3 parçaya böler.
    DİL BAZLI BAŞLIK DESTEĞİ İLE (ES, DE, FR)
    """
    if not content_html:
        return {'content_part1': '', 'content_part2': '', 'content_part3': ''}
    
    # Dillere göre başlık pattern'leri
    patterns = {
        'en': {
            'intro': r'<h2>Introduction</h2>',
            'main': r'<h2>Main Analysis</h2>',
            'practical': r'<h2>Practical Implications</h2>',
            'conclusion': r'<h2>Conclusion</h2>'
        },
        'es': {
            'intro': r'<h2>Introducción</h2>',
            'main': r'<h2>Análisis Principal</h2>',
            'practical': r'<h2>Implicaciones Prácticas</h2>',
            'conclusion': r'<h2>Conclusión</h2>'
        },
        'de': {
            'intro': r'<h2>Einleitung</h2>',
            'main': r'<h2>Hauptanalyse</h2>',
            'practical': r'<h2>Praktische Auswirkungen</h2>',
            'conclusion': r'<h2>Fazit</h2>'
        },
        'fr': {
            'intro': r'<h2>Introduction</h2>',
            'main': r'<h2>Analyse principale</h2>',
            'practical': r'<h2>Implications pratiques</h2>',
            'conclusion': r'<h2>Conclusion</h2>'
        }
    }
    
    # Varsayılan İngilizce
    p = patterns.get(lang, patterns['en'])
    
    # Başlıkları bul (dil bazlı)
    intro_match = re.search(rf'({p["intro"]}.*?){p["main"]}', content_html, re.DOTALL)
    main_analysis_match = re.search(rf'{p["main"]}(.*?){p["practical"]}', content_html, re.DOTALL)
    practical_match = re.search(rf'{p["practical"]}(.*?){p["conclusion"]}', content_html, re.DOTALL)
    conclusion_match = re.search(rf'{p["conclusion"]}(.*?)(?=<h2>|$)', content_html, re.DOTALL)
    
    intro = intro_match.group(1) if intro_match else ""
    main_analysis = main_analysis_match.group(1) if main_analysis_match else ""
    practical = practical_match.group(1) if practical_match else ""
    conclusion = conclusion_match.group(1) if conclusion_match else ""
    
    # Main Analysis'i <h3> başlıklarına göre ikiye böl
    h3_sections = re.findall(r'(<h3>.*?</h3>.*?)(?=<h3>|$)', main_analysis, re.DOTALL)
    
    if h3_sections:
        mid = len(h3_sections) // 2
        main_part1 = ''.join(h3_sections[:mid])
        main_part2 = ''.join(h3_sections[mid:])
    else:
        mid = len(main_analysis) // 2
        main_part1 = main_analysis[:mid]
        main_part2 = main_analysis[mid:]
    
    part1 = intro + main_part1
    part2 = main_part2
    part3 = practical + conclusion
    
    return {
        'content_part1': part1.strip(),
        'content_part2': part2.strip(),
        'content_part3': part3.strip()
    }

def parse_article_html(html_content, lang, category, hash_id, yil, ay):
    """HTML içeriğini parse eder, yazar bilgilerini ve cluster_id'yi META'dan okur"""
    
    # Başlık
    title_match = re.search(r'<h1>(.*?)</h1>', html_content, re.DOTALL)
    title = title_match.group(1).strip() if title_match else ""
    
    # META: author, author_title, author_bio, author_avatar, datetime, cluster_id
    meta_match = re.search(r'<!-- META: author=(.*?), author_title=(.*?), author_bio=(.*?), author_avatar=(.*?), datetime=(.*?)(?:, cluster_id=(.*?))? -->', html_content)
    
    if meta_match:
        author = meta_match.group(1).strip()
        author_title = meta_match.group(2).strip()
        author_bio = meta_match.group(3).strip()
        author_avatar = meta_match.group(4).strip()
        sort_datetime_raw = meta_match.group(5).strip()
        sort_datetime = sort_datetime_raw
        sort_date = sort_datetime_raw[:10]
        cluster_id = meta_match.group(6).strip() if meta_match.group(6) else None
        try:
            display_date = datetime.strptime(sort_date, "%Y-%m-%d").strftime("%d %B %Y")
        except:
            display_date = sort_date
    else:
        author = "Gatemirror Expert"
        author_title = ""
        author_bio = ""
        author_avatar = ""
        sort_datetime = None
        sort_date = None
        display_date = datetime.now().strftime("%d %B %Y")
        cluster_id = None
    
    datetime_iso = sort_datetime if sort_datetime else datetime.now().isoformat()
    
    # Editor's Note
    note_match = re.search(r'<div class="editors-note">(.*?)</div>', html_content, re.DOTALL)
    editors_note = note_match.group(1).strip() if note_match else ""
    
    # Key Takeaways
    takeaway_match = re.search(r'<h2>Key Takeaways</h2>\s*<ul>(.*?)</ul>', html_content, re.DOTALL | re.IGNORECASE)
    if takeaway_match:
        items = re.findall(r'<li>(.*?)</li>', takeaway_match.group(1), re.DOTALL)
        summary_html = "".join([f"<li>{item.strip()}</li>" for item in items])
    else:
        summary_html = "<li>No summary available</li>"
    
    summary_text = ""
    if takeaway_match:
        items = re.findall(r'<li>(.*?)</li>', takeaway_match.group(1), re.DOTALL)
        clean_items = []
        for item in items[:3]:
            clean = re.sub(r'<[^>]+>', '', item).strip()
            if clean:
                clean_items.append(clean)
        summary_text = " ".join(clean_items)
    
    # Sources
    sources_match = re.search(r'<div class="sources">.*?<ul>(.*?)</ul>.*?</div>', html_content, re.DOTALL | re.IGNORECASE)
    if sources_match:
        items = re.findall(r'<li>(.*?)</li>', sources_match.group(1), re.DOTALL)
        sources_html = "".join([f"<li>{item.strip()}</li>" for item in items])
    else:
        sources_html = "<li>Sources not available</li>"
    
    # İçeriği temizle
    content_clean = html_content
    content_clean = re.sub(r'<!-- META:.*?-->', '', content_clean, flags=re.DOTALL)
    content_clean = re.sub(r'<div class="editors-note">.*?</div>', '', content_clean, flags=re.DOTALL)
    content_clean = re.sub(r'<h2>Key Takeaways</h2>\s*<ul>.*?</ul>', '', content_clean, flags=re.DOTALL)
    content_clean = re.sub(r'<div class="sources">.*?</div>', '', content_clean, flags=re.DOTALL)
    content_clean = re.sub(r'<h1>.*?</h1>', '', content_clean, flags=re.DOTALL)
    content_clean = content_clean.strip()

    # Makaleyi 3 parçaya böl - ÇOK DİLLİ VERSİYON
    content_parts = split_article_content_multilang(content_clean, lang)
    
    reading_time, word_count = calculate_reading_time_and_word_count(content_clean)
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
    
    if base_new and image_exists(f"{base_new}_kapak.webp"):
        cover_image = f"{base_new}_kapak.webp"
    else:
        cover_image = f"{base_old}_kapak.webp"
    
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
    
    if base_new and image_exists(f"{base_new}_icerik_2.webp"):
        content_image_2 = f"{base_new}_icerik_2.webp"
    else:
        content_image_2 = f"{base_old}_icerik_2.webp"
    
    return {
        'title': title,
        'author': author,
        'author_title': author_title,
        'author_bio': author_bio,
        'author_avatar': author_avatar,
        'date': display_date,
        'sort_date': sort_date,
        'sort_datetime': sort_datetime,
        'datetime_iso': datetime_iso,
        'editors_note': editors_note,
        'summary': summary_html,
        'summary_text': summary_text,
        'sources': sources_html,
        'content': content_clean,
        'content_part1': content_parts['content_part1'],
        'content_part2': content_parts['content_part2'],
        'content_part3': content_parts['content_part3'],
        'cover_image': cover_image,
        'content_image_1': content_image_1,
        'content_image_2': content_image_2,
        'reading_time': reading_time,
        'word_count': word_count,
        'views': views,
        'description': description,
        'hash': hash_id,
        'category': category,
        'lang': lang,
        'cluster_id': cluster_id
    }

def get_all_raw_articles():
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
                    'cluster_id': parsed.get('cluster_id'),
                    'author_name': parsed.get('author'),
                    'author_title': parsed.get('author_title'),
                    'author_bio': parsed.get('author_bio'),
                    'author_avatar': parsed.get('author_avatar'),
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
