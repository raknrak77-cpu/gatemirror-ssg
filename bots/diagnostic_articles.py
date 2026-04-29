import os
import re
import json
import boto3
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

LANGUAGES = ['en', 'es', 'de', 'fr']

# ================= DİL BAZLI BAŞLIK PATTERN'LERİ =================
HEADER_PATTERNS = {
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

# ================= GERÇEK BOŞ MAKALE KRİTERLERİ =================
MIN_CLEAN_TEXT = 1000      # Temiz metin 1000 karakter altı = BOŞ
MIN_WORD_COUNT = 150       # Kelime 150 altı = BOŞ
MIN_H2_COUNT = 1           # En az 1 h2 başlığı olmalı


def list_all_articles():
    prefix = "articles/"
    files = []
    try:
        response = s3.list_objects_v2(Bucket=R2_BUCKET, Prefix=prefix)
        if 'Contents' not in response:
            return files
        for obj in response['Contents']:
            key = obj['Key']
            if key.endswith('.html') and not key.endswith('/index.html'):
                files.append(key)
    except Exception as e:
        print(f"⚠️ articles/ listelenemedi: {e}")
    return files


def extract_hash_from_key(key):
    filename = key.split('/')[-1]
    if '-' in filename:
        return filename.split('-')[0]
    return filename.replace('.html', '')


def extract_lang_from_key(key):
    parts = key.split('/')
    if len(parts) >= 2:
        return parts[1]
    return 'unknown'


def extract_category_from_key(key):
    parts = key.split('/')
    if len(parts) >= 3:
        return parts[2]
    return 'unknown'


def analyze_article(key):
    try:
        response = s3.get_object(Bucket=R2_BUCKET, Key=key)
        content = response['Body'].read().decode('utf-8')
        size_kb = len(content.encode('utf-8')) / 1024
    except Exception as e:
        return None
    
    hash_id = extract_hash_from_key(key)
    lang = extract_lang_from_key(key)
    category = extract_category_from_key(key)
    
    # TEMİZ METİN (tag'leri temizle)
    text_clean = re.sub(r'<[^>]+>', ' ', content)
    text_clean = re.sub(r'\s+', ' ', text_clean).strip()
    clean_text_len = len(text_clean)
    
    # KELİME SAYISI
    words = re.findall(r'\b\w+\b', text_clean)
    word_count = len(words)
    
    # DİL BAZLI BAŞLIK KONTROLÜ
    patterns = HEADER_PATTERNS.get(lang, HEADER_PATTERNS['en'])
    
    has_intro = re.search(patterns['intro'], content, re.IGNORECASE) is not None
    has_main = re.search(patterns['main'], content, re.IGNORECASE) is not None
    has_practical = re.search(patterns['practical'], content, re.IGNORECASE) is not None
    has_conclusion = re.search(patterns['conclusion'], content, re.IGNORECASE) is not None
    
    # TÜM H2 BAŞLIKLARI
    h2_tags = re.findall(r'<h2>(.*?)</h2>', content, re.DOTALL)
    h2_tags = [tag.strip() for tag in h2_tags]
    h2_count = len(h2_tags)
    
    # ================= BOŞ KONTROLÜ (İÇERİK + DİL BAZLI BAŞLIK) =================
    is_empty = False
    reason = ""
    
    if clean_text_len < MIN_CLEAN_TEXT:
        is_empty = True
        reason = f"temiz_metin:{clean_text_len}<{MIN_CLEAN_TEXT}"
    elif word_count < MIN_WORD_COUNT:
        is_empty = True
        reason = f"kelime:{word_count}<{MIN_WORD_COUNT}"
    elif h2_count < MIN_H2_COUNT:
        is_empty = True
        reason = f"h2_sayisi:{h2_count}<{MIN_H2_COUNT} (dil:{lang})"
    elif not has_intro:
        is_empty = True
        reason = f"Introduction tag'i yok (dil:{lang}, aranan:{patterns['intro']})"
    
    return {
        'key': key,
        'hash': hash_id,
        'lang': lang,
        'category': category,
        'size_kb': round(size_kb, 2),
        'clean_text_len': clean_text_len,
        'word_count': word_count,
        'h2_count': h2_count,
        'h2_tags': h2_tags[:5],
        'has_intro': has_intro,
        'has_main': has_main,
        'has_practical': has_practical,
        'has_conclusion': has_conclusion,
        'is_empty': is_empty,
        'reason': reason
    }


def group_by_hash(analyses):
    grouped = {}
    for analysis in analyses:
        if not analysis:
            continue
        hash_id = analysis['hash']
        if hash_id not in grouped:
            grouped[hash_id] = []
        grouped[hash_id].append(analysis)
    return grouped


def write_report(analyses, grouped, output_path):
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("=" * 100 + "\n")
        f.write("ARTICLES DENETİM BOTU V5 - DİL BAZLI KONTROL\n")
        f.write(f"Oluşturulma: {datetime.now().isoformat()}\n")
        f.write("=" * 100 + "\n\n")
        
        f.write("📋 BOŞ MAKALE KRİTERLERİ:\n")
        f.write(f"   - Temiz metin < {MIN_CLEAN_TEXT} karakter\n")
        f.write(f"   - veya Kelime < {MIN_WORD_COUNT}\n")
        f.write(f"   - veya h2 sayısı < {MIN_H2_COUNT}\n")
        f.write(f"   - veya Introduction tag'i yok (dil bazlı)\n\n")
        
        total = len(analyses)
        empty = len([a for a in analyses if a['is_empty']])
        healthy = total - empty
        
        f.write("📊 GENEL İSTATİSTİKLER\n")
        f.write("-" * 50 + "\n")
        f.write(f"Toplam makale: {total}\n")
        f.write(f"✅ SAĞLIKLI: {healthy}\n")
        f.write(f"❌ BOŞ MAKALE: {empty}\n\n")
        
        # Dil bazında
        f.write("📊 DİL BAZINDA DURUM\n")
        f.write("-" * 50 + "\n")
        for lang in LANGUAGES:
            lang_articles = [a for a in analyses if a['lang'] == lang]
            lang_empty = len([a for a in lang_articles if a['is_empty']])
            lang_healthy = len(lang_articles) - lang_empty
            f.write(f"{lang.upper()}: Toplam {len(lang_articles)} | ✅ {lang_healthy} | ❌ {lang_empty}\n")
        f.write("\n")
        
        # BOŞ MAKALELER (HASH BAZLI)
        f.write("=" * 100 + "\n")
        f.write("❌ BOŞ MAKALELER (SİLİNMELİ)\n")
        f.write("=" * 100 + "\n\n")
        
        empty_files = [a for a in analyses if a['is_empty']]
        if empty_files:
            empty_by_hash = {}
            for a in empty_files:
                if a['hash'] not in empty_by_hash:
                    empty_by_hash[a['hash']] = []
                empty_by_hash[a['hash']].append(a)
            
            f.write(f"Toplam {len(empty_files)} boş dosya, {len(empty_by_hash)} benzersiz hash\n\n")
            
            for hash_id, files in empty_by_hash.items():
                f.write(f"🔑 HASH: {hash_id}\n")
                for a in files:
                    f.write(f"   📁 {a['lang'].upper()} | Kategori: {a['category']} | Boyut: {a['size_kb']} KB\n")
                    f.write(f"      Temiz metin: {a['clean_text_len']} karakter | Kelime: {a['word_count']} | h2: {a['h2_count']}\n")
                    f.write(f"      Intro: {'✅' if a['has_intro'] else '❌'} | Main: {'✅' if a['has_main'] else '❌'}\n")
                    f.write(f"      Sebep: {a['reason']}\n")
                    if a['h2_tags']:
                        f.write(f"      Mevcut h2 başlıkları: {a['h2_tags'][:3]}\n")
                f.write("\n" + "-" * 80 + "\n\n")
        else:
            f.write("   ✅ BOŞ MAKALE YOK\n\n")
        
        # ÖZET
        f.write("=" * 100 + "\n")
        f.write("🔧 YAPILACAKLAR\n")
        f.write("=" * 100 + "\n")
        if empty > 0:
            f.write(f"1. {empty} BOŞ makaleyi R2'den SİLİN\n")
            f.write("   - raw-articles/ klasöründen\n")
            f.write("   - articles/ klasöründen\n")
            f.write("   - images/ klasöründen (görseller)\n")
        else:
            f.write("   ✅ SİLİNECEK MAKALE YOK\n")
        
        f.write("\n" + "=" * 100 + "\n")
        f.write("🏁 RAPOR SONU\n")
        f.write("=" * 100 + "\n")


def diagnostic_articles():
    print("\n" + "=" * 100)
    print("🔬 ARTICLES DENETİM BOTU V5 - DİL BAZLI KONTROL")
    print(f"   KRİTER: Temiz metin < {MIN_CLEAN_TEXT} veya kelime < {MIN_WORD_COUNT}")
    print(f"           veya h2 < {MIN_H2_COUNT} veya Introduction yok (dil bazlı)")
    print("=" * 100)
    
    print("\n📂 R2'den makaleler listeleniyor...")
    files = list_all_articles()
    print(f"   Toplam {len(files)} makale dosyası bulundu.")
    
    print("\n🔍 Makaleler analiz ediliyor...")
    analyses = []
    for i, f in enumerate(files):
        if i % 100 == 0 and i > 0:
            print(f"   İlerleme: {i}/{len(files)}")
        analysis = analyze_article(f)
        if analysis:
            analyses.append(analysis)
    
    print(f"\n   Analiz tamamlandı. {len(analyses)} makale işlendi.")
    
    output_path = "articles_diagnostic_report.txt"
    write_report(analyses, group_by_hash(analyses), output_path)
    
    empty = len([a for a in analyses if a['is_empty']])
    print(f"\n📊 ÖZET:")
    print(f"   Toplam makale: {len(analyses)}")
    print(f"   ❌ BOŞ MAKALE: {empty}")
    print(f"\n📄 Rapor: {output_path}")


if __name__ == "__main__":
    diagnostic_articles()
