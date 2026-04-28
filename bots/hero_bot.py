import os
import json
import re
import boto3
from botocore.client import Config
from datetime import datetime

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

def extract_youtube_id(url):
    patterns = [
        r'(?:youtube\.com\/watch\?v=)([\w-]+)',
        r'(?:youtu\.be\/)([\w-]+)',
        r'(?:youtube\.com\/embed\/)([\w-]+)'
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

# ================= BLOK RENDER FONKSİYONLARI =================

def render_title_block(block):
    return f'<h1 class="hero-title">{block["content"]}</h1>'

def render_description_block(block):
    content = block["content"].replace('\n', '<br>')
    return f'<p class="hero-description">{content}</p>'

def render_cta_block(block):
    style = block.get('style', 'primary')
    return f'<a href="{block["url"]}" class="hero-cta hero-cta-{style}">{block["text"]}</a>'

def render_news_ticker_block(block):
    items = block.get('items', [])
    if not items:
        return ''
    
    html = '<div class="hero-news-ticker"><div class="ticker-wrapper"><div class="ticker">'
    html += '<span class="ticker-label">🔥 Latest:</span>'
    for item in items:
        if '→' in item:
            parts = item.split('→')
            text = parts[0].strip()
            url = parts[1].strip()
            html += f'<a href="{url}" class="ticker-item">{text}</a>'
        else:
            html += f'<span class="ticker-item">{item}</span>'
    html += '</div></div></div>'
    return html

def render_stats_block(block):
    items = block.get('items', [])
    if not items:
        return ''
    
    html = '<div class="hero-stats">'
    for stat in items:
        html += f'''
        <div class="stat">
            <span class="stat-value">{stat["value"]}</span>
            <span class="stat-label">{stat["label"]}</span>
        </div>'''
    html += '</div>'
    return html

def render_youtube_block(block):
    video_id = extract_youtube_id(block['url'])
    if not video_id:
        return ''
    title = block.get('title', 'Video')
    return f'''
    <div class="hero-youtube">
        <iframe src="https://www.youtube.com/embed/{video_id}" title="{title}" frameborder="0" allowfullscreen></iframe>
        {f'<p class="hero-youtube-caption">{title}</p>' if title else ''}
    </div>'''

def render_gif_block(block):
    return f'<div class="hero-gif-wrapper"><img src="{block["url"]}" alt="{block.get("alt", "Animation")}" class="hero-gif" loading="lazy"></div>'

def render_image_block(block):
    return f'<div class="hero-image-wrapper"><img src="{block["url"]}" alt="{block.get("alt", "")}" class="hero-image" loading="lazy"></div>'

def render_carousel_block(block):
    items = block.get('items', [])
    if not items:
        return ''
    html = '<div class="hero-carousel"><div class="carousel-container">'
    for i, item in enumerate(items):
        active_class = 'active' if i == 0 else ''
        html += f'<div class="carousel-slide {active_class}"><img src="{item}" loading="lazy"></div>'
    html += '</div><button class="carousel-prev">❮</button><button class="carousel-next">❯</button><div class="carousel-dots">'
    for i in range(len(items)):
        html += f'<span class="dot" data-index="{i}"></span>'
    html += '</div></div>'
    return html

def render_countdown_block(block):
    target_date = block.get('target_date', '')
    if not target_date:
        return ''
    return f'<div class="hero-countdown" data-target="{target_date}"><div class="countdown-timer"></div><div class="countdown-label">{block.get("label", "")}</div></div>'

def render_quote_block(block):
    return f'<div class="hero-quote"><blockquote>"{block["content"]}"</blockquote><cite>— {block.get("author", "")}</cite></div>'

def render_breadcrumb_block(block):
    """Breadcrumb bloğu - sadece article sayfasında gösterilir"""
    return '<div class="hero-breadcrumb"></div>'  # Breadcrumb template'de ayrıca var, bu sadece placeholder

# ================= BLOK TİPİ RENDER MAP =================
BLOCK_RENDERERS = {
    'title': render_title_block,
    'description': render_description_block,
    'cta': render_cta_block,
    'news_ticker': render_news_ticker_block,
    'stats': render_stats_block,
    'youtube': render_youtube_block,
    'gif': render_gif_block,
    'image': render_image_block,
    'carousel': render_carousel_block,
    'countdown': render_countdown_block,
    'quote': render_quote_block,
    'breadcrumb': render_breadcrumb_block
}

# ================= HERO VERİSİNİ YÜKLE (assets/ klasöründen) =================

# Cache mekanizması (R2'den tekrar tekrar okumamak için)
_hero_data_cache = None
_hero_data_cache_time = None

def load_hero_data():
    """hero.json'u R2'den okur, cache'ler. Hata durumunda None döner (sessizce)"""
    global _hero_data_cache, _hero_data_cache_time
    
    now = datetime.now()
    if _hero_data_cache and _hero_data_cache_time and (now - _hero_data_cache_time).seconds < 60:
        return _hero_data_cache
    
    try:
        response = s3.get_object(Bucket=R2_BUCKET, Key='assets/hero.json')
        data = json.loads(response['Body'].read().decode('utf-8'))
        _hero_data_cache = data
        _hero_data_cache_time = now
        return data
    except Exception as e:
        # Sessizce hata ver, ama çok fazla log basma
        if not hasattr(load_hero_data, '_warned'):
            print(f"⚠️ assets/hero.json yüklenemedi (varsayılan kullanılacak): {e}")
            load_hero_data._warned = True
        return None

def get_default_blocks(lang):
    """hero.json yoksa kullanılacak varsayılan bloklar"""
    defaults = {
        'en': [
            {'type': 'title', 'content': 'Gatemirror'},
            {'type': 'description', 'content': 'Global insights on technology, wellness, and future economy.'}
        ],
        'es': [
            {'type': 'title', 'content': 'Gatemirror'},
            {'type': 'description', 'content': 'Perspectivas globales sobre tecnología, bienestar y economía futura.'}
        ],
        'de': [
            {'type': 'title', 'content': 'Gatemirror'},
            {'type': 'description', 'content': 'Globale Einblicke in Technologie, Wohlbefinden und Zukunftswirtschaft.'}
        ],
        'fr': [
            {'type': 'title', 'content': 'Gatemirror'},
            {'type': 'description', 'content': 'Perspectives mondiales sur la technologie, le bien-être et l\'économie future.'}
        ]
    }
    return defaults.get(lang, defaults['en'])

def get_hero_blocks(page_type, lang, category=None):
    hero_data = load_hero_data()
    
    # hero_data yoksa veya geçersizse default döndür
    if not hero_data or not isinstance(hero_data, dict):
        return get_default_blocks(lang)
    
    pages = hero_data.get('pages', {})
    
    # Sayfa tipine göre veriyi al
    if page_type == 'home':
        page_data = pages.get('home', {})
    elif page_type == 'category' and category:
        category_data = pages.get('category', {})
        page_data = category_data.get(category, {})
    elif page_type == 'special':
        special_data = pages.get('special', {})
        page_data = special_data.get(category, {})
    elif page_type == 'article':
        article_data = pages.get('article', {})
        page_data = article_data
    else:
        page_data = {}
    
    # Dil bazlı blokları al
    lang_data = page_data.get(lang, {})
    blocks = lang_data.get('blocks', [])
    
    # Blok yoksa default dene
    if not blocks:
        defaults = hero_data.get('defaults', {})
        default_data = defaults.get(lang, defaults.get('en', {}))
        blocks = default_data.get('blocks', [])
    
    # Hala yoksa hardcoded default
    if not blocks:
        blocks = get_default_blocks(lang)
    
    return blocks

def render_block(block, lang=None):
    block_type = block.get('type')
    renderer = BLOCK_RENDERERS.get(block_type)
    
    if renderer:
        try:
            return renderer(block)
        except Exception as e:
            print(f"⚠️ Hero bloğu render hatası ({block_type}): {e}")
    return ''

def render_hero(page_type, lang, category=None):
    """Hero HTML'i oluşturur"""
    blocks = get_hero_blocks(page_type, lang, category)
    
    if not blocks:
        return ''
    
    html = '<div class="hero-grid">\n'
    for block in blocks:
        # hide_on kontrolü: eğer page_type hide_on listesindeyse atla
        hide_on = block.get('hide_on', [])
        if page_type in hide_on:
            continue
        
        block_html = render_block(block, lang)
        if block_html:
            # full genişlikte göster (grid sistemi için)
            html += f'    <div class="hero-grid-full">{block_html}</div>\n'
    html += '</div>'
    return html

def get_hero_data(page_type, lang, category=None):
    return {
        'html': render_hero(page_type, lang, category),
        'has_hero': True
    }

# ================= TEST =================
if __name__ == "__main__":
    print("🧪 Hero Bot Testi (assets/hero.json okuyor)")
    print("-" * 50)
    
    print("\n🏠 HOME (EN):")
    print(render_hero('home', 'en'))
    
    print("\n🏠 HOME (ES):")
    print(render_hero('home', 'es'))
    
    print("\n📂 CATEGORY TECH (EN):")
    print(render_hero('category', 'en', 'tech'))
    
    print("\n📄 ARTICLE (EN):")
    print(render_hero('article', 'en'))
    
    print("\n✅ Hero Bot çalışıyor!")
