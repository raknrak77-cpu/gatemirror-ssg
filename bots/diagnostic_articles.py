import os
import re
import boto3
from datetime import datetime
from botocore.client import Config

# ================= KONFIGURASYON =================
R2_ID = os.getenv('R2_ACCOUNT_ID')
R2_ACCESS_KEY = os.getenv('R2_ACCESS_KEY_ID')
R2_SECRET_KEY = os.getenv('R2_SECRET_ACCESS_KEY')
R2_BUCKET = os.getenv('R2_BUCKET_NAME')

s3 = boto3.client(
    's3',
    endpoint_url=f'https://{R2_ID}.r2.cloudflarestorage.com',
    aws_access_key_id=R2_ACCESS_KEY,
    aws_secret_access_key=R2_SECRET_KEY,
    config=Config(signature_version='s3v4'),
    region_name='auto'
)

LANGUAGES = ['en', 'es', 'de', 'fr']

# ================= DİL BAZLI BÖLÜM PATTERN'LERİ =================
SECTION_PATTERNS = {
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

SECTION_NAMES = ['intro', 'main', 'practical', 'conclusion']


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
    
    # Dil bazlı pattern'leri al
    patterns = SECTION_PATTERNS.get(lang, SECTION_PATTERNS['en'])
    
    # Her bölümü kontrol et
    sections_found = {}
    for section, pattern in patterns.items():
        found = re.search(pattern, content, re.IGNORECASE) is not None
        sections_found[section] = found
    
    section_count = sum(1 for v in sections_found.values() if v)
    
    # Durum belirleme
    if section_count == 0:
        status = "COK_BOS"
        action = "SIL"
    elif section_count == 1:
        status = "BOS"
        action = "SIL"
    elif section_count == 2:
        status = "EKSIK"
        action = "INCELE"
    elif section_count == 3:
        status = "YETERLI"
        action = "KORU"
    else:
        status = "TAM"
        action = "KORU"
    
    # Temiz metin (içerik kontrolü için)
    text_clean = re.sub(r'<[^>]+>', ' ', content)
    text_clean = re.sub(r'\s+', ' ', text_clean).strip()
    clean_text_len = len(text_clean)
    
    return {
        'key': key,
        'hash': hash_id,
        'lang': lang,
        'category': category,
        'size_kb': round(size_kb, 2),
        'clean_text_len': clean_text_len,
        'sections_found': sections_found,
        'section_count': section_count,
        'status': status,
        'action': action
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
        f.write("ARTICLES DENETİM BOTU V8 - BÖLÜM BAZLI ANALİZ\n")
        f.write(f"Oluşturulma: {datetime.now().isoformat()}\n")
        f.write("=" * 100 + "\n\n")
        
        f.write("📋 BÖLÜM KRİTERLERİ:\n")
        f.write("   - 4 bölüm: TAM (KORU)\n")
        f.write("   - 3 bölüm: YETERLİ (KORU)\n")
        f.write("   - 2 bölüm: EKSİK (İNCELE)\n")
        f.write("   - 1 bölüm: BOŞ (SİL)\n")
        f.write("   - 0 bölüm: ÇOK BOŞ (SİL)\n\n")
        
        f.write("📌 BÖLÜMLER: intro, main, practical, conclusion\n\n")
        
        total = len(analyses)
        total_tam = len([a for a in analyses if a['status'] == 'TAM'])
        total_yeterli = len([a for a in analyses if a['status'] == 'YETERLI'])
        total_eksik = len([a for a in analyses if a['status'] == 'EKSIK'])
        total_bos = len([a for a in analyses if a['status'] == 'BOS'])
        total_cok_bos = len([a for a in analyses if a['status'] == 'COK_BOS'])
        
        f.write("📊 GENEL İSTATİSTİKLER\n")
        f.write("-" * 50 + "\n")
        f.write(f"Toplam makale: {total}\n")
        f.write(f"✅ TAM (4 bölüm): {total_tam}\n")
        f.write(f"✅ YETERLİ (3 bölüm): {total_yeterli}\n")
        f.write(f"⚠️ EKSİK (2 bölüm): {total_eksik}\n")
        f.write(f"❌ BOŞ (1 bölüm): {total_bos}\n")
        f.write(f"❌ ÇOK BOŞ (0 bölüm): {total_cok_bos}\n\n")
        
        # Dil bazında
        f.write("📊 DİL BAZINDA DURUM\n")
        f.write("-" * 50 + "\n")
        for lang in LANGUAGES:
            lang_articles = [a for a in analyses if a['lang'] == lang]
            lang_tam = len([a for a in lang_articles if a['status'] == 'TAM'])
            lang_yeterli = len([a for a in lang_articles if a['status'] == 'YETERLI'])
            lang_eksik = len([a for a in lang_articles if a['status'] == 'EKSIK'])
            lang_bos = len([a for a in lang_articles if a['status'] == 'BOS'])
            lang_cok_bos = len([a for a in lang_articles if a['status'] == 'COK_BOS'])
            f.write(f"{lang.upper()}: Toplam {len(lang_articles)} | ✅ TAM:{lang_tam} YETERLI:{lang_yeterli} | ⚠️ EKSIK:{lang_eksik} | ❌ BOS:{lang_bos} COK_BOS:{lang_cok_bos}\n")
        f.write("\n")
        
        # HASH BAZLI DETAYLI RAPOR
        f.write("=" * 100 + "\n")
        f.write("🔑 HASH BAZLI DETAYLI ANALİZ\n")
        f.write("=" * 100 + "\n\n")
        
        for hash_id, items in grouped.items():
            f.write(f"🔑 HASH: {hash_id}\n")
            for a in items:
                # Bölüm sembolleri
                symbols = ""
                for section in SECTION_NAMES:
                    if a['sections_found'].get(section, False):
                        symbols += "✅"
                    else:
                        symbols += "❌"
                
                status_symbol = "✅" if a['action'] == "KORU" else "⚠️" if a['action'] == "INCELE" else "❌"
                f.write(f"   {status_symbol} {a['lang'].upper()}: {symbols} ({a['section_count']}/4) | {a['size_kb']} KB | {a['clean_text_len']} karakter\n")
            f.write("\n")
        
        # SİLİNMESİ GEREKENLER (BOŞ ve ÇOK BOŞ)
        f.write("=" * 100 + "\n")
        f.write("❌ SİLİNMESİ GEREKEN MAKALELER (BOŞ / ÇOK BOŞ)\n")
        f.write("=" * 100 + "\n\n")
        
        to_delete = [a for a in analyses if a['status'] in ['BOS', 'COK_BOS']]
        if to_delete:
            for a in to_delete:
                f.write(f"📁 {a['key']}\n")
                f.write(f"   Hash: {a['hash']} | Dil: {a['lang'].upper()} | Kategori: {a['category']}\n")
                f.write(f"   Bölüm sayısı: {a['section_count']}/4 | Boyut: {a['size_kb']} KB\n")
                missing = [s for s in SECTION_NAMES if not a['sections_found'].get(s, False)]
                f.write(f"   Eksik bölümler: {', '.join(missing)}\n")
                f.write("\n")
        else:
            f.write("   ✅ SİLİNECEK MAKALE YOK\n\n")
        
        # İNCELENMESİ GEREKENLER (EKSİK)
        f.write("=" * 100 + "\n")
        f.write("⚠️ İNCELENMESİ GEREKEN MAKALELER (2 BÖLÜM)\n")
        f.write("=" * 100 + "\n\n")
        
        to_review = [a for a in analyses if a['status'] == 'EKSIK']
        if to_review:
            for a in to_review[:50]:  # İlk 50
                f.write(f"📁 {a['key']}\n")
                f.write(f"   Hash: {a['hash']} | Dil: {a['lang'].upper()} | Kategori: {a['category']}\n")
                missing = [s for s in SECTION_NAMES if not a['sections_found'].get(s, False)]
                f.write(f"   Eksik bölümler: {', '.join(missing)}\n")
                f.write("\n")
            if len(to_review) > 50:
                f.write(f"... ve {len(to_review) - 50} dosya daha\n\n")
        else:
            f.write("   ⚠️ İNCELENECEK MAKALE YOK\n\n")
        
        f.write("=" * 100 + "\n")
        f.write("🏁 RAPOR SONU\n")
        f.write("=" * 100 + "\n")


def diagnostic_articles():
    print("\n" + "=" * 100)
    print("🔬 ARTICLES DENETİM BOTU V8 - BÖLÜM BAZLI ANALİZ")
    print("   TAM: 4 bölüm | YETERLİ: 3 bölüm | EKSİK: 2 bölüm | BOŞ: 1 bölüm | ÇOK BOŞ: 0 bölüm")
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
    
    tam = len([a for a in analyses if a['status'] == 'TAM'])
    yeterli = len([a for a in analyses if a['status'] == 'YETERLI'])
    eksik = len([a for a in analyses if a['status'] == 'EKSIK'])
    bos = len([a for a in analyses if a['status'] == 'BOS'])
    cok_bos = len([a for a in analyses if a['status'] == 'COK_BOS'])
    
    print(f"\n📊 ÖZET:")
    print(f"   Toplam makale: {len(analyses)}")
    print(f"   ✅ TAM (4 bölüm): {tam}")
    print(f"   ✅ YETERLİ (3 bölüm): {yeterli}")
    print(f"   ⚠️ EKSİK (2 bölüm): {eksik}")
    print(f"   ❌ BOŞ (1 bölüm): {bos}")
    print(f"   ❌ ÇOK BOŞ (0 bölüm): {cok_bos}")
    print(f"\n📄 Rapor: {output_path}")


if __name__ == "__main__":
    diagnostic_articles()
