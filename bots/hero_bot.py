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
    """YouTube URL'sinden video ID'sini çıkarır"""
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

def get_popular_articles(limit=3, lang='en'):
    """
    TEST MODU: Örnek veri döndürür
    Gerçek sistemde R2'den articles.json okuyacak
    """
    # ========== TEST VERİSİ ==========
    test_articles = {
        'en': [
            {
                'url': '/en/tech/ai-revolution-2026.html',
                'image': '',
                'title': 'AI Revolution 2026: What\'s Coming',
                'reading_time': 8
            },
            {
                'url': '/en/wellness/red-light-therapy.html',
                'image': '',
                'title': 'Red Light Therapy: Science Update 2026',
                'reading_time': 6
            },
            {
                'url': '/en/eco/carbon-capture-breakthrough.html',
                'image': '',
                'title': 'Carbon Capture Breakthrough: New Tech',
                'reading_time': 7
            }
        ],
        'es': [
            {
                'url': '/es/tech/revolucion-ia-2026.html',
                'image': '',
                'title': 'Revolución IA 2026: Lo Que Viene',
                'reading_time': 8
            },
            {
                'url': '/es/wellness/terapia-luz-roja.html',
                'image': '',
                'title': 'Terapia de Luz Roja: Actualización 2026',
                'reading_time': 6
            },
            {
                'url': '/es/eco/captura-carbono.html',
                'image': '',
                'title': 'Avance en Captura de Carbono',
                'reading_time': 7
            }
        ],
        'de': [
            {
                'url': '/de/tech/ki-revolution-2026.html',
                'image': '',
                'title': 'KI-Revolution 2026: Was Kommt',
                'reading_time': 8
            },
            {
                'url': '/de/wellness/rotlicht-therapie.html',
                'image': '',
                'title': 'Rotlichttherapie: Wissenschaft 2026',
                'reading_time': 6
            },
            {
                'url': '/de/eco/kohlenstoffabscheidung.html',
                'image': '',
                'title': 'Durchbruch bei CO2-Abscheidung',
                'reading_time': 7
            }
        ],
        'fr': [
            {
                'url': '/fr/tech/revolution-ia-2026.html',
                'image': '',
                'title': 'Révolution IA 2026: Ce Qui Vient',
                'reading_time': 8
            },
            {
                'url': '/fr/wellness/therapie-lumiere-rouge.html',
                'image': '',
                'title': 'Thérapie par Lumière Rouge: Mise à Jour',
                'reading_time': 6
            },
            {
                'url': '/fr/eco/captage-carbone.html',
                'image': '',
                'title': 'Percée dans le Captage du Carbone',
                'reading_time': 7
            }
        ]
    }
    
    # Dile göre test verisini döndür, yoksa İngilizce
    articles = test_articles.get(lang, test_articles['en'])
    return articles[:limit]

def get_featured_articles(limit=3, lang='en'):
    """Öne çıkan makaleleri döndürür (aynı popular kullanılabilir)"""
    return get_popular_articles(limit, lang)

# ================= BLOK RENDER FONKSİYONLARI =================

def render_title_block(block):
    return f'<h1 class="hero-title">{block["content"]}</h1>'

def render_description_block(block):
    return f'<p class="hero-description">{block["content"]}</p>'

def render_cta_block(block):
    style = block.get('style', 'primary')
    return f'<a href="{block["url"]}" class="hero-cta hero-cta-{style}">{block["text"]}</a>'

def render_featured_articles_block(block, lang):
    articles = get_popular_articles(limit=block.get('limit', 3), lang=lang)
    if not articles:
        return ''
    
    show_images = block.get('show_images', True)
    no_images_class = '' if show_images else ' no-images'
    
    html = f'<div class="hero-featured-section"><h3 class="hero-featured-title">{block.get("title", "Featured")}</h3>'
    html += f'<div class="hero-featured-articles{no_images_class}">'
    for article in articles:
        html += f'''
        <div class="featured-article-item">
            <a href="{article['url']}">
                {f'<img src="{article["image"]}" alt="{article["title"]}" loading="lazy">' if show_images else ''}
                <span class="featured-article-title">{article['title']}</span>
                <span class="featured-article-meta">⏱️ {article.get('reading_time', 5)} min read</span>
            </a>
        </div>'''
    html += '</div></div>'
    return html

def render_news_ticker_block(block):
    items = block.get('items', [])
    if not items:
        return ''
    
    html = '<div class="hero-news-ticker"><div class="ticker-wrapper"><div class="ticker">'
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

def render_youtube_block(block):
    video_id = extract_youtube_id(block['url'])
    if not video_id:
        return ''
    
    title = block.get('title', 'Video')
    return f'''
    <div class="hero-youtube">
        <iframe 
            src="https://www.youtube.com/embed/{video_id}" 
            title="{title}" 
            frameborder="0" 
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" 
            allowfullscreen>
        </iframe>
        {f'<p class="hero-youtube-caption">{title}</p>' if title else ''}
    </div>'''

def render_gif_block(block):
    return f'<div class="hero-gif-wrapper"><img src="{block["url"]}" alt="{block.get("alt", "Animation")}" class="hero-gif" loading="lazy"></div>'

def render_image_block(block):
    return f'<div class="hero-image-wrapper"><img src="{block["url"]}" alt="{block.get("alt", "")}" class="hero-image" loading="lazy"></div>'

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

def render_carousel_block(block):
    items = block.get('items', [])
    if not items:
        return ''
    
    html = '<div class="hero-carousel"><div class="carousel-container">'
    for i, item in enumerate(items):
        active_class = 'active' if i == 0 else ''
        html += f'<div class="carousel-slide {active_class}"><img src="{item}" loading="lazy"></div>'
    html += '''
    </div>
    <button class="carousel-prev">❮</button>
    <button class="carousel-next">❯</button>
    <div class="carousel-dots">'''
    for i in range(len(items)):
        html += f'<span class="dot" data-index="{i}"></span>'
    html += '</div></div>'
    return html

def render_countdown_block(block):
    target_date = block.get('target_date', '')
    if not target_date:
        return ''
    return f'''
    <div class="hero-countdown" data-target="{target_date}">
        <div class="countdown-timer"></div>
        <div class="countdown-label">{block.get('label', '')}</div>
    </div>'''

def render_quote_block(block):
    return f'''
    <div class="hero-quote">
        <blockquote>"{block['content']}"</blockquote>
        <cite>— {block.get('author', '')}</cite>
    </div>'''

# ================= BLOK TİPİ RENDER MAP =================
BLOCK_RENDERERS = {
    'title': render_title_block,
    'description': render_description_block,
    'cta': render_cta_block,
    'featured_articles': lambda b, lang=None: render_featured_articles_block(b, lang),
    'news_ticker': render_news_ticker_block,
    'youtube': render_youtube_block,
    'gif': render_gif_block,
    'image': render_image_block,
    'stats': render_stats_block,
    'carousel': render_carousel_block,
    'countdown': render_countdown_block,
    'quote': render_quote_block
}

# ================= HERO VERİSİNİ YÜKLE =================

def load_hero_data():
    """R2'den hero.json dosyasını yükler"""
    try:
        response = s3.get_object(Bucket=R2_BUCKET, Key='templates/hero.json')
        return json.loads(response['Body'].read().decode('utf-8'))
    except Exception as e:
        print(f"⚠️ templates/hero.json yüklenemedi: {e}")
        return None

def get_hero_blocks(page_type, lang, category=None):
    """
    Sayfa tipine ve dile göre hero bloklarını döndürür
    
    page_type: 'home', 'category', 'special', 'article'
    lang: 'en', 'es', 'de', 'fr'
    category: 'tech', 'wellness', 'future-economy', 'eco', 'elearning' (sadece category için)
    """
    hero_data = load_hero_data()
    
    if not hero_data:
        # Fallback: varsayılan hero
        return [{'type': 'title', 'content': 'Gatemirror'}, {'type': 'description', 'content': 'Global insights'}]
    
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
    else:
        page_data = {}
    
    # Dil bazlı veriyi al
    lang_data = page_data.get(lang, {})
    blocks = lang_data.get('blocks', [])
    
    # Eğer dil bazlı blok yoksa, defaults'u dene
    if not blocks:
        defaults = hero_data.get('defaults', {})
        default_data = defaults.get(lang, defaults.get('en', {}))
        blocks = default_data.get('blocks', [])
    
    return blocks

def render_block(block, lang=None):
    """Tek bir bloğu render eder"""
    block_type = block.get('type')
    renderer = BLOCK_RENDERERS.get(block_type)
    
    if renderer:
        try:
            if block_type == 'featured_articles':
                return renderer(block, lang)
            else:
                return renderer(block)
        except Exception as e:
            print(f"⚠️ Hero bloğu render hatası ({block_type}): {e}")
    return ''

def render_hero(page_type, lang, category=None):
    """
    Hero HTML'ini oluşturur - 2 KOLONLU GRID DESTEKLİ
    
    page_type: 'home', 'category', 'special', 'article'
    lang: 'en', 'es', 'de', 'fr'
    category: 'tech', 'wellness', 'future-economy', 'eco', 'elearning' veya special_type
    """
    blocks = get_hero_blocks(page_type, lang, category)
    
    if not blocks:
        return ''
    
    # Grid'e göre ayır
    left_column = []
    right_column = []
    full_width = []
    
    for block in blocks:
        grid_type = block.get('grid', 'full')
        
        if grid_type == 'col-left':
            left_column.append(block)
        elif grid_type == 'col-right':
            right_column.append(block)
        else:  # 'full'
            full_width.append(block)
    
    html = '<div class="hero-grid">\n'
    
    # Sol ve sağ sütunlar (2 kolon) - sadece ikisi de boş değilse
    if left_column or right_column:
        html += '    <div class="hero-grid-row-2cols">\n'
        html += '        <div class="hero-grid-col-left">\n'
        for block in left_column:
            html += render_block(block, lang)
        html += '        </div>\n'
        html += '        <div class="hero-grid-col-right">\n'
        for block in right_column:
            html += render_block(block, lang)
        html += '        </div>\n'
        html += '    </div>\n'
    
    # Tam genişlik bloklar
    for block in full_width:
        html += '    <div class="hero-grid-full">\n'
        html += render_block(block, lang)
        html += '    </div>\n'
    
    html += '</div>'
    return html

# ================= PUBLISHER İÇİN HAZIR FONKSİYON =================

def get_hero_data(page_type, lang, category=None):
    """
    Publisher için hero verisini döndürür (render edilmiş HTML olarak)
    """
    return {
        'html': render_hero(page_type, lang, category),
        'has_hero': True
    }

# ================= TEST =================
if __name__ == "__main__":
    print("🧪 Hero Bot Testi (TEST MODU - Örnek Verilerle)")
    print("-" * 50)
    
    print("\n🏠 HOME (EN) - Grid Düzeni:")
    print(render_hero('home', 'en'))
    
    print("\n🏠 HOME (ES) - Grid Düzeni:")
    print(render_hero('home', 'es'))
    
    print("\n🏠 HOME (DE) - Grid Düzeni:")
    print(render_hero('home', 'de'))
    
    print("\n🏠 HOME (FR) - Grid Düzeni:")
    print(render_hero('home', 'fr'))
    
    print("\n✅ Hero Bot TEST MODU çalışıyor!")
