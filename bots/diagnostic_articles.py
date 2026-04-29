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

# ================= KATMANLI KRİTERLER =================
KB_SAFE = 51        # ≥51 KB = güvenli
KB_WARNING = 49     # 49-51 KB = incele
KB_CRITICAL = 48    # <48 KB = kritik

# İçerik kontrolleri için eşikler
MIN_CLEAN_TEXT = 500      # 500 karakter altı çok kısa
MIN_WORD_COUNT = 80       # 80 kelime altı çok kısa
MIN_H2_COUNT = 1          # h2 sayısı


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
    
    # Temiz metin ve kelime sayısı
    text_clean = re.sub(r'<[^>]+>', ' ', content)
    text_clean = re.sub(r'\s+', ' ', text_clean).strip()
    clean_text_len = len(text_clean)
    words = re.findall(r'\b\w+\b', text_clean)
    word_count = len(words)
    
    # h2 başlıkları
    h2_tags = re.findall(r'<h2>(.*?)</h2>', content, re.DOTALL)
    h2_tags = [tag.strip() for tag in h2_tags]
    h2_count = len(h2_tags)
    
    # Introduction var mı? (dil bazlı)
    intro_patterns = {
        'en': r'<h2>Introduction</h2>',
        'es': r'<h2>Introducción</h2>',
        'de': r'<h2>Einleitung</h2>',
        'fr': r'<h2>Introduction</h2>'
    }
    intro_pattern = intro_patterns.get(lang, intro_patterns['en'])
    has_intro = re.search(intro_pattern, content, re.IGNORECASE) is not None
    
    # ================= KATMANLI KARAR =================
    if size_kb >= KB_SAFE:
        # ≥51 KB: Güvenli bölge
        status = "GUVENLI"
        reason = f"boyut:{size_kb:.1f}KB ≥ {KB_SAFE}KB"
        
    elif size_kb >= KB_WARNING:
        # 49-51 KB: Hash bazlı + dil bazlı içerik kontrolü
        # İçerik yeterli mi?
        if clean_text_len >= MIN_CLEAN_TEXT and word_count >= MIN_WORD_COUNT:
            status = "INCELE"
            reason = f"boyut:{size_kb:.1f}KB ({KB_WARNING}-{KB_SAFE}KB), içerik yeterli"
        else:
            status = "KRITIK"
            reason = f"boyut:{size_kb:.1f}KB ({KB_WARNING}-{KB_SAFE}KB), içerik yetersiz (temiz:{clean_text_len}, kelime:{word_count})"
            
    else:
        # <48 KB: Sıkı kontrol
        issues = []
        if clean_text_len < MIN_CLEAN_TEXT:
            issues.append(f"temiz_metin:{clean_text_len}<{MIN_CLEAN_TEXT}")
        if word_count < MIN_WORD_COUNT:
            issues.append(f"kelime:{word_count}<{MIN_WORD_COUNT}")
        if h2_count < MIN_H2_COUNT:
            issues.append(f"h2:{h2_count}<{MIN_H2_COUNT}")
        if not has_intro:
            issues.append("intro_yok")
        
        if issues:
            status = "KRITIK"
            reason = f"boyut:{size_kb:.1f}KB <{KB_CRITICAL}KB, sorunlar: {', '.join(issues)}"
        else:
            status = "INCELE"
            reason = f"boyut:{size_kb:.1f}KB <{KB_CRITICAL}KB ama içerik normal"
    
    return {
        'key': key,
        'hash': hash_id,
        'lang': lang,
        'category': category,
        'size_kb': round(size_kb, 2),
        'clean_text_len': clean_text_len,
        'word_count': word_count,
        'h2_count': h2_count,
        'h2_tags': h2_tags[:3],
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
        f.write("ARTICLES DENETİM BOTU V3 - KB KONTROLLÜ\n")
        f.write(f"Oluşturulma: {datetime.now().isoformat()}\n")
        f.write("=" * 100 + "\n\n")
        
        # KRİTERLER
        f.write("📋 KATMANLI KRİTERLER:\n")
        f.write(f"   ✅ GÜVENLİ: ≥ {KB_SAFE} KB (içerik kontrolü yapılmaz)\n")
        f.write(f"   ⚠️ İNCELE: {KB_WARNING}-{KB_SAFE} KB (içerik yeterliyse incele, yetersizse kritik)\n")
        f.write(f"   ❌ KRİTİK: < {KB_CRITICAL} KB (sıkı kontrol, sorun varsa kritik)\n\n")
        
        total = len(analyses)
        safe = len([a for a in analyses if a['status'] == 'GUVENLI'])
        medium = len([a for a in analyses if a['status'] == 'INCELE'])
        critical = len([a for a in analyses if a['status'] == 'KRITIK'])
        
        f.write("📊 GENEL İSTATİSTİKLER\n")
        f.write("-" * 50 + "\n")
        f.write(f"Toplam makale: {total}\n")
        f.write(f"✅ GÜVENLİ (≥{KB_SAFE}KB): {safe}\n")
        f.write(f"⚠️ İNCELE ({KB_WARNING}-{KB_SAFE}KB): {medium}\n")
        f.write(f"❌ KRİTİK (<{KB_CRITICAL}KB): {critical}\n\n")
        
        # Dil bazında
        f.write("📊 DİL BAZINDA DURUM\n")
        f.write("-" * 50 + "\n")
        for lang in LANGUAGES:
            lang_articles = [a for a in analyses if a['lang'] == lang]
            lang_safe = len([a for a in lang_articles if a['status'] == 'GUVENLI'])
            lang_medium = len([a for a in lang_articles if a['status'] == 'INCELE'])
            lang_critical = len([a for a in lang_articles if a['status'] == 'KRITIK'])
            f.write(f"{lang.upper()}: Toplam {len(lang_articles)} | ✅ {lang_safe} | ⚠️ {lang_medium} | ❌ {lang_critical}\n")
        f.write("\n")
        
        # KRİTİK OLANLAR (SİLİNMELİ)
        f.write("=" * 100 + "\n")
        f.write("❌ KRİTİK MAKALELER (SİLİNMELİ)\n")
        f.write("=" * 100 + "\n\n")
        
        critical_files = [a for a in analyses if a['status'] == 'KRITIK']
        if critical_files:
            # Hash bazında grupla
            critical_by_hash = {}
            for a in critical_files:
                if a['hash'] not in critical_by_hash:
                    critical_by_hash[a['hash']] = []
                critical_by_hash[a['hash']].append(a)
            
            for hash_id, files in critical_by_hash.items():
                f.write(f"🔑 HASH: {hash_id}\n")
                for a in files:
                    f.write(f"   📁 {a['lang'].upper()}: {a['size_kb']} KB | {a['clean_text_len']} karakter | {a['word_count']} kelime | h2:{a['h2_count']}\n")
                    f.write(f"      Sebep: {a['reason']}\n")
                f.write("\n" + "-" * 80 + "\n\n")
        else:
            f.write("   ✅ KRİTİK MAKALE YOK\n\n")
        
        # İNCELE OLANLAR (HASH BAZLI GRUPLANMIŞ)
        f.write("=" * 100 + "\n")
        f.write("⚠️ İNCELE GEREKEN MAKALELER (HASH BAZLI)\n")
        f.write("=" * 100 + "\n\n")
        
        medium_files = [a for a in analyses if a['status'] == 'INCELE']
        if medium_files:
            medium_by_hash = {}
            for a in medium_files:
                if a['hash'] not in medium_by_hash:
                    medium_by_hash[a['hash']] = []
                medium_by_hash[a['hash']].append(a)
            
            for hash_id, files in medium_by_hash.items():
                f.write(f"🔑 HASH: {hash_id}\n")
                for a in files:
                    f.write(f"   📁 {a['lang'].upper()}: {a['size_kb']} KB | {a['clean_text_len']} karakter | {a['word_count']} kelime\n")
                f.write("\n")
            f.write(f"TOPLAM {len(medium_files)} dosya ( {len(medium_by_hash)} hash )\n\n")
        else:
            f.write("   ⚠️ İNCELE GEREKEN MAKALE YOK\n\n")
        
        # ÖZET
        f.write("=" * 100 + "\n")
        f.write("🔧 YAPILACAKLAR\n")
        f.write("=" * 100 + "\n")
        f.write(f"1. {critical} KRİTİK makaleyi R2'den SİLİN\n")
        if critical > 0:
            f.write("   - raw-articles/ klasöründen\n")
            f.write("   - articles/ klasöründen\n")
            f.write("   - images/ klasöründen (görseller)\n")
        f.write(f"2. {medium} İNCELE makaleyi kontrol edin (gerekirse düzeltin)\n")
        f.write(f"3. {safe} GÜVENLİ makaleye dokunmayın\n")
        
        f.write("\n" + "=" * 100 + "\n")
        f.write("🏁 RAPOR SONU\n")
        f.write("=" * 100 + "\n")


def diagnostic_articles():
    print("\n" + "=" * 100)
    print("🔬 ARTICLES DENETİM BOTU V3 - KB KONTROLLÜ")
    print(f"   ✅ GÜVENLİ: ≥ {KB_SAFE} KB")
    print(f"   ⚠️ İNCELE: {KB_WARNING}-{KB_SAFE} KB (içerik kontrolü ile)")
    print(f"   ❌ KRİTİK: < {KB_CRITICAL} KB (sıkı kontrol)")
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
    
    safe = len([a for a in analyses if a['status'] == 'GUVENLI'])
    medium = len([a for a in analyses if a['status'] == 'INCELE'])
    critical = len([a for a in analyses if a['status'] == 'KRITIK'])
    
    print(f"\n📊 ÖZET:")
    print(f"   Toplam makale: {len(analyses)}")
    print(f"   ✅ GÜVENLİ (≥{KB_SAFE}KB): {safe}")
    print(f"   ⚠️ İNCELE ({KB_WARNING}-{KB_SAFE}KB): {medium}")
    print(f"   ❌ KRİTİK (<{KB_CRITICAL}KB): {critical}")
    print(f"\n📄 Rapor: {output_path}")


if __name__ == "__main__":
    diagnostic_articles()
