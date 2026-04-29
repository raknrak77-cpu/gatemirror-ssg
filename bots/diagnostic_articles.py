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

# ================= YUMUŞAK KRİTERLER =================
MIN_CLEAN_TEXT = 1000      # 1000 karakter altı = KRİTİK HATALI
MIN_WORD_COUNT = 150       # 150 kelime altı = KRİTİK HATALI
MIN_H2_COUNT = 1           # 0 h2 = ORTA HATALI (sadece uyarı)


def list_all_articles():
    """articles/ klasöründeki tüm HTML dosyalarını listeler"""
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
    """Tek bir makaleyi analiz eder - YUMUŞAK KRİTERLER"""
    try:
        response = s3.get_object(Bucket=R2_BUCKET, Key=key)
        content = response['Body'].read().decode('utf-8')
        size_kb = len(content.encode('utf-8')) / 1024
    except Exception as e:
        return None
    
    hash_id = extract_hash_from_key(key)
    lang = extract_lang_from_key(key)
    category = extract_category_from_key(key)
    
    # 1. TEMİZ METİN
    text_clean = re.sub(r'<[^>]+>', ' ', content)
    text_clean = re.sub(r'\s+', ' ', text_clean).strip()
    clean_text_len = len(text_clean)
    
    # 2. KELİME SAYISI
    words = re.findall(r'\b\w+\b', text_clean)
    word_count = len(words)
    
    # 3. H2 BAŞLIKLARI
    h2_tags = re.findall(r'<h2>(.*?)</h2>', content, re.DOTALL)
    h2_tags = [tag.strip() for tag in h2_tags]
    h2_count = len(h2_tags)
    
    # 4. INTRODUCTION VAR MI? (dil bazlı)
    intro_patterns = {
        'en': r'<h2>Introduction</h2>',
        'es': r'<h2>Introducción</h2>',
        'de': r'<h2>Einleitung</h2>',
        'fr': r'<h2>Introduction</h2>'
    }
    intro_pattern = intro_patterns.get(lang, intro_patterns['en'])
    has_intro = re.search(intro_pattern, content, re.IGNORECASE) is not None
    
    # 5. MAKALE DURUMU (YUMUŞAK)
    if clean_text_len < MIN_CLEAN_TEXT or word_count < MIN_WORD_COUNT:
        status = "KRITIK_HATALI"
        reason = f"temiz_metin:{clean_text_len}(<{MIN_CLEAN_TEXT}) veya kelime:{word_count}(<{MIN_WORD_COUNT})"
    elif h2_count < MIN_H2_COUNT or not has_intro:
        status = "ORTA_HATALI"
        reason = f"h2_sayisi:{h2_count}(<{MIN_H2_COUNT}) veya intro_yok"
    else:
        status = "SAĞLIKLI"
        reason = ""
    
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
        'status': status,
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
        f.write("ARTICLES DENETİM BOTU V2 - YUMUŞAK KRİTERLER\n")
        f.write(f"Oluşturulma: {datetime.now().isoformat()}\n")
        f.write("=" * 100 + "\n\n")
        
        # KRİTERLER
        f.write("📋 KRİTERLER:\n")
        f.write(f"   - KRİTİK HATALI: temiz metin < {MIN_CLEAN_TEXT} veya kelime < {MIN_WORD_COUNT}\n")
        f.write(f"   - ORTA HATALI: h2 sayısı < {MIN_H2_COUNT} veya Introduction yok\n")
        f.write(f"   - SAĞLIKLI: tüm kriterleri geçer\n\n")
        
        total = len(analyses)
        critical = len([a for a in analyses if a['status'] == 'KRITIK_HATALI'])
        medium = len([a for a in analyses if a['status'] == 'ORTA_HATALI'])
        healthy = len([a for a in analyses if a['status'] == 'SAĞLIKLI'])
        
        f.write("📊 GENEL İSTATİSTİKLER\n")
        f.write("-" * 50 + "\n")
        f.write(f"Toplam makale: {total}\n")
        f.write(f"✅ SAĞLIKLI: {healthy}\n")
        f.write(f"⚠️ ORTA HATALI: {medium}\n")
        f.write(f"❌ KRİTİK HATALI: {critical}\n\n")
        
        # Dil bazında
        f.write("📊 DİL BAZINDA DURUM\n")
        f.write("-" * 50 + "\n")
        for lang in LANGUAGES:
            lang_articles = [a for a in analyses if a['lang'] == lang]
            lang_healthy = len([a for a in lang_articles if a['status'] == 'SAĞLIKLI'])
            lang_medium = len([a for a in lang_articles if a['status'] == 'ORTA HATALI'])
            lang_critical = len([a for a in lang_articles if a['status'] == 'KRITIK_HATALI'])
            f.write(f"{lang.upper()}: Toplam {len(lang_articles)} | ✅ {lang_healthy} | ⚠️ {lang_medium} | ❌ {lang_critical}\n")
        f.write("\n")
        
        # KRİTİK HATALILAR (SİLİNMELİ)
        f.write("=" * 100 + "\n")
        f.write("❌ KRİTİK HATALI MAKALELER (SİLİNMELİ)\n")
        f.write("=" * 100 + "\n\n")
        
        critical_files = [a for a in analyses if a['status'] == 'KRITIK_HATALI']
        if critical_files:
            for a in critical_files:
                f.write(f"📁 {a['key']}\n")
                f.write(f"   Hash: {a['hash']} | Dil: {a['lang'].upper()} | Kategori: {a['category']}\n")
                f.write(f"   Boyut: {a['size_kb']} KB | Temiz metin: {a['clean_text_len']} karakter | Kelime: {a['word_count']}\n")
                f.write(f"   Sebep: {a['reason']}\n")
                f.write("\n" + "-" * 80 + "\n\n")
        else:
            f.write("   ✅ KRİTİK HATALI MAKALE YOK\n\n")
        
        # ORTA HATALILAR (İNCELENMELİ)
        f.write("=" * 100 + "\n")
        f.write("⚠️ ORTA HATALI MAKALELER (İNCELENMELİ)\n")
        f.write("=" * 100 + "\n\n")
        
        medium_files = [a for a in analyses if a['status'] == 'ORTA_HATALI']
        if medium_files:
            for a in medium_files[:50]:  # İlk 50
                f.write(f"📁 {a['key']}\n")
                f.write(f"   Hash: {a['hash']} | Dil: {a['lang'].upper()} | Kategori: {a['category']}\n")
                f.write(f"   h2 sayısı: {a['h2_count']} | Introduction var: {'✅' if a['has_intro'] else '❌'}\n")
                f.write(f"   İlk 3 h2: {a['h2_tags'][:3]}\n")
                f.write("\n")
            if len(medium_files) > 50:
                f.write(f"... ve {len(medium_files) - 50} dosya daha\n\n")
        else:
            f.write("   ✅ ORTA HATALI MAKALE YOK\n\n")
        
        # SAĞLIKLI ÖZET
        f.write("=" * 100 + "\n")
        f.write("✅ SAĞLIKLI MAKALELER (ÖZET)\n")
        f.write("=" * 100 + "\n")
        f.write(f"Toplam {healthy} makale sağlıklı.\n\n")
        
        # ÖZET
        f.write("=" * 100 + "\n")
        f.write("🔧 YAPILACAKLAR\n")
        f.write("=" * 100 + "\n")
        f.write(f"1. {critical} KRİTİK HATALI makaleyi R2'den SİLİN\n")
        if critical > 0:
            f.write("   - raw-articles/ klasöründen\n")
            f.write("   - articles/ klasöründen\n")
            f.write("   - images/ klasöründen (görseller)\n")
        f.write(f"2. {medium} ORTA HATALI makaleyi İNCELEYİN (gerekirse düzeltin)\n")
        f.write(f"3. {healthy} SAĞLIKLI makaleye dokunmayın\n")
        
        f.write("\n" + "=" * 100 + "\n")
        f.write("🏁 RAPOR SONU\n")
        f.write("=" * 100 + "\n")


def diagnostic_articles():
    print("\n" + "=" * 100)
    print("🔬 ARTICLES DENETİM BOTU V2 - YUMUŞAK KRİTERLER")
    print(f"   KRİTİK: temiz metin < {MIN_CLEAN_TEXT} veya kelime < {MIN_WORD_COUNT}")
    print(f"   ORTA: h2 sayısı < {MIN_H2_COUNT} veya Introduction yok")
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
    
    grouped = group_by_hash(analyses)
    
    output_path = "articles_diagnostic_report.txt"
    write_report(analyses, grouped, output_path)
    
    critical = len([a for a in analyses if a['status'] == 'KRITIK_HATALI'])
    medium = len([a for a in analyses if a['status'] == 'ORTA_HATALI'])
    healthy = len([a for a in analyses if a['status'] == 'SAĞLIKLI'])
    
    print(f"\n📊 ÖZET:")
    print(f"   Toplam makale: {len(analyses)}")
    print(f"   ✅ SAĞLIKLI: {healthy}")
    print(f"   ⚠️ ORTA HATALI: {medium}")
    print(f"   ❌ KRİTİK HATALI: {critical}")
    print(f"\n📄 Rapor: {output_path}")


if __name__ == "__main__":
    diagnostic_articles()
