import os
import markdown
from datetime import datetime
from jinja2 import Environment, FileSystemLoader

def parse_frontmatter(content):
    """Markdown dosyasının frontmatter'ını (YAML) ve içeriğini ayırır"""
    if not content.startswith('---'):
        return {}, content
    
    parts = content.split('---', 2)
    if len(parts) < 3:
        return {}, content
    
    frontmatter_text = parts[1]
    md_content = parts[2].strip()
    
    frontmatter = {}
    for line in frontmatter_text.split('\n'):
        line = line.strip()
        if ':' in line:
            key, value = line.split(':', 1)
            key = key.strip()
            value = value.strip().strip('"')
            frontmatter[key] = value
    
    return frontmatter, md_content

def extract_summary_items(summary_text):
    """Summary YAML'den madde işaretlerini çıkarır"""
    items = []
    for line in summary_text.split('\n'):
        line = line.strip()
        if line.startswith('-'):
            items.append(line[1:].strip())
    return items

def get_menu_texts(lang):
    """Dile göre menü metinlerini döndürür"""
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
    """Kategori adını dile göre döndürür"""
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
    """Kategori açıklamasını dile göre döndürür (pas geç, yoksa boş string)"""
    descriptions = {
        'en': {
            'wellness': 'Deep insights on physical, mental, and emotional well-being.',
            'tech': 'Latest developments in AI, software, and digital transformation.',
            'future-economy': 'Finance, DeFi, tokenomics, and algorithmic trading.',
            'eco': 'Sustainable living, green energy, and climate solutions.',
            'elearning': 'Online education, career development, and digital skills.'
        },
        'es': {
            'wellness': 'Perspectivas profundas sobre bienestar físico, mental y emocional.',
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

def builder():
    """Tüm dillerdeki Markdown dosyalarını okur, HTML oluşturur (hata yok, pas geçer)"""
    
    template_dir = "templates"
    if not os.path.exists(template_dir):
        print(f"❌ {template_dir} klasörü bulunamadı!")
        return
    
    try:
        env = Environment(loader=FileSystemLoader(template_dir))
        single_template = env.get_template("single.html")
        home_template = env.get_template("home.html")
        list_template = env.get_template("list.html")
    except Exception as e:
        print(f"❌ Template yüklenemedi: {e}")
        return
    
    languages = ['en', 'es', 'de', 'fr']
    r2_base = os.getenv('R2_PUBLIC_URL', 'https://pub-f9790eb09fb8460a9ba4e1509db5b135.r2.dev')
    
    all_articles = {lang: [] for lang in languages}
    
    for lang in languages:
        content_base = f"content/{lang}"
        if not os.path.exists(content_base):
            print(f"⏭️ {content_base} klasörü yok, atlanıyor.")
            continue
        
        print(f"\n📖 {lang.upper()} dili işleniyor...")
        
        for root, dirs, files in os.walk(content_base):
            for file in files:
                if not file.endswith('.md'):
                    continue
                
                md_path = os.path.join(root, file)
                try:
                    with open(md_path, 'r', encoding='utf-8') as f:
                        md_content = f.read()
                except Exception as e:
                    print(f"   ⚠️ {md_path} okunamadı: {e}")
                    continue
                
                frontmatter, md_body = parse_frontmatter(md_content)
                if not md_body:
                    print(f"   ⚠️ {md_path} içerik boş, atlanıyor.")
                    continue
                
                try:
                    html_body = markdown.markdown(md_body, extensions=['extra', 'codehilite'])
                except Exception as e:
                    print(f"   ⚠️ {md_path} Markdown hatası: {e}")
                    continue
                
                slug = frontmatter.get('hash', file.replace('.md', ''))
                category = frontmatter.get('category', os.path.basename(root))
                title = frontmatter.get('title', 'Untitled')
                date = frontmatter.get('date', datetime.now().strftime("%d %B %Y"))
                author = frontmatter.get('author', 'Expert Analyst')
                editors_note = frontmatter.get('editors_note', '')  # YENİ
                
                summary_raw = frontmatter.get('summary', '')
                summary_items = extract_summary_items(summary_raw)
                summary_html = ''.join([f'<li>{item}</li>' for item in summary_items]) if summary_items else '<li>Analysis: High-Fidelity</li>'
                
                sources_raw = frontmatter.get('sources', '')
                sources_html = ''
                if sources_raw and sources_raw != '- ' and 'http' in sources_raw:
                    sources_html = f'<li><a href="{sources_raw}" target="_blank">Reference</a></li>'
                
                # R2 görsel linkleri (kategori bazlı, WebP)
                cover_image = f"{r2_base}/images/{category}/{slug}_kapak.webp"
                content_image_1 = f"{r2_base}/images/{category}/{slug}_icerik_1.webp"
                content_image_2 = f"{r2_base}/images/{category}/{slug}_icerik_2.webp"
                
                menu_texts = get_menu_texts(lang)
                
                try:
                    html_output = single_template.render(
                        lang=lang,
                        title=title,
                        author=author,
                        date=date,
                        editors_note=editors_note,  # YENİ
                        summary=summary_html,
                        content=html_body,
                        sources=sources_html,
                        cover_image=cover_image,
                        content_image_1=content_image_1,
                        content_image_2=content_image_2,
                        menu=menu_texts,
                        related_articles=[]
                    )
                except Exception as e:
                    print(f"   ⚠️ {md_path} template hatası: {e}")
                    continue
                
                target_dir = os.path.join("public", lang, category)
                os.makedirs(target_dir, exist_ok=True)
                target_path = os.path.join(target_dir, f"{slug}.html")
                
                try:
                    with open(target_path, 'w', encoding='utf-8') as f:
                        f.write(html_output)
                    print(f"   ✅ {target_path}")
                except Exception as e:
                    print(f"   ⚠️ {target_path} yazılamadı: {e}")
                    continue
                
                all_articles[lang].append({
                    'title': title,
                    'url': f"/{lang}/{category}/{slug}.html",
                    'image': cover_image,
                    'excerpt': summary_items[0][:100] if summary_items else title[:100],
                    'date': date,
                    'category': category
                })
        
        # Ana sayfa (home.html) oluştur
        if all_articles[lang]:
            try:
                all_articles[lang].sort(key=lambda x: x['date'], reverse=True)
                latest_articles = all_articles[lang][:12]
                menu_texts = get_menu_texts(lang)
                home_html = home_template.render(lang=lang, menu=menu_texts, articles=latest_articles)
                home_path = os.path.join("public", lang, "index.html")
                os.makedirs(os.path.dirname(home_path), exist_ok=True)
                with open(home_path, 'w', encoding='utf-8') as f:
                    f.write(home_html)
                print(f"   ✅ Ana sayfa: {home_path}")
            except Exception as e:
                print(f"   ⚠️ {lang} ana sayfa oluşturulamadı: {e}")
        
        # Kategori arşivleri (list.html) oluştur
        categories = ['wellness', 'tech', 'future-economy', 'eco', 'elearning']
        for category in categories:
            cat_articles = [a for a in all_articles[lang] if a['category'] == category]
            if not cat_articles:
                continue
            
            try:
                cat_articles.sort(key=lambda x: x['date'], reverse=True)
                menu_texts = get_menu_texts(lang)
                category_name = get_category_name(lang, category)
                category_description = get_category_description(lang, category)
                
                list_html = list_template.render(
                    lang=lang,
                    menu=menu_texts,
                    category_name=category_name,
                    category_description=category_description,
                    articles=cat_articles
                )
                
                target_dir = os.path.join("public", lang, category)
                os.makedirs(target_dir, exist_ok=True)
                target_path = os.path.join(target_dir, "index.html")
                
                with open(target_path, 'w', encoding='utf-8') as f:
                    f.write(list_html)
                
                print(f"   ✅ Kategori arşivi: {target_path}")
            except Exception as e:
                print(f"   ⚠️ {lang}/{category} arşivi oluşturulamadı: {e}")
    
    print("\n🏁 Builder tamamlandı. (Hatalar pas geçildi, eksik diller atlandı)")

if __name__ == "__main__":
    builder()
