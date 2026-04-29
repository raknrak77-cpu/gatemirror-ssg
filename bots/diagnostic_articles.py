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

# ================= BOŞ MAKALE KRİTERİ =================
MIN_CLEAN_TEXT = 700      # 750 karakter altı = BOŞ


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
    
    # ================= BOŞ KONTROLÜ (SADECE KARAKTER) =================
    is_empty = clean_text_len < MIN_CLEAN_TEXT
    
    return {
        'key': key,
        'hash': hash_id,
        'lang': lang,
        'category': category,
        'size_kb': round(size_kb, 2),
        'clean_text_len': clean_text_len,
        'is_empty': is_empty,
        'status': 'BOŞ' if is_empty else 'DOLU'
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
        f.write("ARTICLES DENETİM BOTU V7 - SADECE KARAKTER KONTROLÜ\n")
        f.write(f"Oluşturulma: {datetime.now().isoformat()}\n")
        f.write("=" * 100 + "\n\n")
        
        f.write("📋 BOŞ MAKALE KRİTERİ:\n")
        f.write(f"   - Temiz metin < {MIN_CLEAN_TEXT} karakter\n\n")
        
        total = len(analyses)
        empty = len([a for a in analyses if a['is_empty']])
        healthy = total - empty
        
        f.write("📊 GENEL İSTATİSTİKLER\n")
        f.write("-" * 50 + "\n")
        f.write(f"Toplam makale: {total}\n")
        f.write(f"✅ DOLU: {healthy}\n")
        f.write(f"❌ BOŞ: {empty}\n\n")
        
        # Dil bazında
        f.write("📊 DİL BAZINDA DURUM\n")
        f.write("-" * 50 + "\n")
        for lang in LANGUAGES:
            lang_articles = [a for a in analyses if a['lang'] == lang]
            lang_empty = len([a for a in lang_articles if a['is_empty']])
            f.write(f"{lang.upper()}: Toplam {len(lang_articles)} | ❌ Boş: {lang_empty}\n")
        f.write("\n")
        
        # BOŞ MAKALELER
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
                    f.write(f"   📁 {a['lang'].upper()} | {a['category']} | {a['size_kb']} KB | {a['clean_text_len']} karakter\n")
                f.write("\n")
        else:
            f.write("   ✅ BOŞ MAKALE YOK\n\n")
        
        f.write("=" * 100 + "\n")
        f.write("🏁 RAPOR SONU\n")
        f.write("=" * 100 + "\n")


def diagnostic_articles():
    print("\n" + "=" * 100)
    print("🔬 ARTICLES DENETİM BOTU V7 - SADECE KARAKTER")
    print(f"   KRİTER: Temiz metin < {MIN_CLEAN_TEXT} karakter")
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
    print(f"   ❌ BOŞ (temiz metin < {MIN_CLEAN_TEXT}): {empty}")
    print(f"\n📄 Rapor: {output_path}")


if __name__ == "__main__":
    diagnostic_articles()
