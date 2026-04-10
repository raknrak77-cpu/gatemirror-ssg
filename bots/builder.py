import os
import re
from datetime import datetime
from jinja2 import Environment, FileSystemLoader

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

def builder():
    """content/ altındaki ham HTML'leri template ile birleştirip yine content/ altına yazar"""
    
    template_dir = "templates"
    if not os.path.exists(template_dir):
        print(f"❌ {template_dir} bulunamadı!")
        return
    
    try:
        env = Environment(loader=FileSystemLoader(template_dir))
        single_template = env.get_template("single.html")
        home_template = env.get_template("home.html")
        list_template = env.get_template("list.html")
    except Exception as e:
        print(f"❌ Template hatası: {e}")
        return
    
    r2_base = os.getenv('R2_PUBLIC_URL', 'https://pub-f9790eb09fb8460a9ba4e1509db5b135.r2.dev')
    languages = ['en', 'es', 'de', 'fr']
    all_articles = {lang: [] for lang in languages}
    
    for lang in languages:
        content_base = f"content/{lang}"
        if not os.path.exists(content_base):
            print(f"⏭️ {content_base} yok, atlanıyor.")
            continue
        
        print(f"\n📖 {lang.upper()} işleniyor...")
        
        for root, dirs, files in os.walk(content_base):
            for file in files:
                if not file.endswith('.html'):
                    continue
                
                html_path = os.path.join(root, file)
                try:
                    with open(html_path, 'r', encoding='utf-8') as f:
                        ham_html = f.read()
                except Exception as e:
                    print(f"   ⚠️ {html_path} okunamadı: {e}")
                    continue
                
                hash_id = file.replace('.html', '')
                category = os.path.basename(root)
                
                # Başlık ve Editor's Note'u al
                title_match = re.search(r'<h1>(.*?)</h1>', ham_html)
                title = title_match.group(1) if title_match else ""
                
                note_match = re.search(r'<div class="editors-note">(.*?)</div>', ham_html, re.DOTALL)
                editors_note = note_match.group(1) if note_match else ""
                
                # R2 görsel linkleri
                cover_image = f"{r2_base}/images/{category}/{hash_id}_kapak.webp"
                content_image = f"{r2_base}/images/{category}/{hash_id}_icerik.webp"
                
                menu_texts = get_menu_texts(lang)
                date = datetime.now().strftime("%d %B %Y")
                author = "Gatemirror Expert"
                
                try:
                    html_output = single_template.render(
                        lang=lang, title=title, author=author, date=date,
                        editors_note=editors_note, summary="<li>Analysis: High-Fidelity</li>",
                        content=ham_html, sources="", cover_image=cover_image,
                        content_image=content_image, menu=menu_texts, related_articles=[]
                    )
                except Exception as e:
                    print(f"   ⚠️ {html_path} template hatası: {e}")
                    continue
                
                # content/ altına yaz (üzerine yaz)
                target_dir = os.path.join("content", lang, category)
                os.makedirs(target_dir, exist_ok=True)
                target_path = os.path.join(target_dir, f"{hash_id}.html")
                
                with open(target_path, 'w', encoding='utf-8') as f:
                    f.write(html_output)
                print(f"   ✅ {target_path}")
                
                all_articles[lang].append({
                    'title': title,
                    'url': f"/articles/{lang}/{category}/{hash_id}.html",  # ✅ /articles/ eklendi
                    'image': cover_image,
                    'excerpt': title[:100],
                    'date': date,
                    'category': category
                })
        
        # Ana sayfa (content/{lang}/index.html)
        if all_articles[lang]:
            all_articles[lang].sort(key=lambda x: x['date'], reverse=True)
            latest_articles = all_articles[lang][:12]
            menu_texts = get_menu_texts(lang)
            home_html = home_template.render(lang=lang, menu=menu_texts, articles=latest_articles)
            home_path = os.path.join("content", lang, "index.html")
            os.makedirs(os.path.dirname(home_path), exist_ok=True)
            with open(home_path, 'w', encoding='utf-8') as f:
                f.write(home_html)
            print(f"   ✅ Ana sayfa: {home_path}")
        
        # Kategori arşivleri (content/{lang}/{category}/index.html)
        categories = ['wellness', 'tech', 'future-economy', 'eco', 'elearning']
        for category in categories:
            cat_articles = [a for a in all_articles[lang] if a['category'] == category]
            if not cat_articles:
                continue
            
            cat_articles.sort(key=lambda x: x['date'], reverse=True)
            menu_texts = get_menu_texts(lang)
            category_name = get_category_name(lang, category)
            category_description = get_category_description(lang, category)
            
            list_html = list_template.render(
                lang=lang, menu=menu_texts,
                category_name=category_name,
                category_description=category_description,
                articles=cat_articles
            )
            
            target_dir = os.path.join("content", lang, category)
            os.makedirs(target_dir, exist_ok=True)
            target_path = os.path.join(target_dir, "index.html")
            
            with open(target_path, 'w', encoding='utf-8') as f:
                f.write(list_html)
            print(f"   ✅ Kategori arşivi: {target_path}")
    
    print("\n🏁 Builder tamamlandı. (content/ klasörü template'li HTML'lerle güncellendi)")

if __name__ == "__main__":
    builder()
