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
    """Local templates/ klasöründeki HTML dosyalarını R2'ye yükler."""
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
    """R2'den template çeker, yoksa local'den okur."""
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

def parse_article_html(html_content, lang, category, hash_id, r2_base):
    title_match = re.search(r'<h1>(.*?)</h1>', html_content, re.DOTALL)
    title = title_match.group(1).strip() if title_match else ""
    
    meta_match = re.search(r'<!-- META: author=(.*?), date=(.*?) -->', html_content)
    if meta_match:
        author = meta_match.group(1).strip()
        date = meta_match.group(2).strip()
    else:
        author = "Gatemirror Expert"
        date = datetime.now().strftime("%d %B %Y")
    
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
    content_clean = content_clean.strip()
    
    reading_time = calculate_reading_time(content_clean)
    views = generate_views(hash_id)
    
    plain_text = re.sub(r'<[^>]+>', '', content_clean[:500])
    description = plain_text[:150].strip() + ("..." if len(plain_text) > 150 else "")
    if not description:
        description = title
    
    cover_image = f"{r2_base}/images/{category}/{hash_id}_kapak.webp"
    content_image_1 = f"{r2_base}/images/{category}/{hash_id}_icerik_1.webp"
    content_image_2 = f"{r2_base}/images/{category}/{hash_id}_icerik_2.webp"
    
    return {
        'title': title, 'author': author, 'date': date,
        'editors_note': editors_note, 'summary': summary_html, 'sources': sources_html,
        'content': content_clean, 'cover_image': cover_image,
        'content_image_1': content_image_1, 'content_image_2': content_image_2,
        'reading_time': reading_time, 'views': views, 'description': description,
        'hash': hash_id, 'category': category, 'lang': lang
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
            parts = key.replace(prefix, '').split('/')
            if len(parts) >= 2:
                category = parts[0]
                hash_id = parts[1].replace('.html', '')
            else:
                continue
            try:
                file_obj = s3.get_object(Bucket=R2_BUCKET, Key=key)
                html_content = file_obj['Body'].read().decode('utf-8')
                parsed = parse_article_html(html_content, lang, category, hash_id, R2_PUBLIC_URL)
                article_url = f"/articles/{lang}/{category}/{hash_id}.html"
                all_articles.append({
                    'lang': lang, 'category': category, 'hash': hash_id,
                    'parsed': parsed, 'url': article_url, 'date': parsed['date']
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
    print("🚀 Publisher Bot (SITE_URL yok, R2_PUBLIC_URL kullanılır) başlatılıyor...")
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
        lang_articles.sort(key=lambda x: x['date'], reverse=True)
        menu_texts = get_menu_texts(lang)
        
        # 1. Tekil makaleler
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
        
        # 2. Ana sayfa
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
        
        # 3. Kategori arşivleri
        categories = ['wellness', 'tech', 'future-economy', 'eco', 'elearning']
        for category in categories:
            cat_articles = [a for a in lang_articles if a['category'] == category]
            if not cat_articles:
                continue
            cat_articles.sort(key=lambda x: x['date'], reverse=True)
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
    
    print("\n🏁 Publisher tamamlandı.")

if __name__ == "__main__":
    publisher()
