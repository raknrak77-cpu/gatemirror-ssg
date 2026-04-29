import os
import re
import boto3
from datetime import datetime
from botocore.client import Config

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

# NOKTA ATIŞI KRİTERLERİ
MIN_P_TAG_COUNT = 2        # En az 2 paragraf
MIN_P_TEXT_LEN = 300       # Paragraf içi metin toplamı 300 karakter altı = BOŞ


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
    
    # Tüm <p> tag'lerini bul
    p_tags = re.findall(r'<p>(.*?)</p>', content, re.DOTALL)
    p_count = len(p_tags)
    
    # <p> tag'leri içindeki metin uzunluğu (tag'siz)
    p_text = " ".join(p_tags)
    p_text_clean = re.sub(r'<[^>]+>', ' ', p_text)
    p_text_clean = re.sub(r'\s+', ' ', p_text_clean).strip()
    p_text_len = len(p_text_clean)
    
    # Ayrıca <div class="sources"> içindeki metni sayma (kaynaklar içerik değil)
    # Kaynakları temizle
    
    # BOŞ MAKALE KRİTERİ
    is_empty = p_count < MIN_P_TAG_COUNT or p_text_len < MIN_P_TEXT_LEN
    
    reason = ""
    if p_count < MIN_P_TAG_COUNT:
        reason = f"paragraf:{p_count}<{MIN_P_TAG_COUNT}"
    elif p_text_len < MIN_P_TEXT_LEN:
        reason = f"paragraf_metni:{p_text_len}<{MIN_P_TEXT_LEN}"
    
    return {
        'key': key,
        'hash': hash_id,
        'lang': lang,
        'category': category,
        'size_kb': round(size_kb, 2),
        'p_count': p_count,
        'p_text_len': p_text_len,
        'is_empty': is_empty,
        'reason': reason,
        'first_p_text': p_tags[0][:200] if p_tags else "(no paragraph)"
    }


def write_report(analyses, output_path):
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("=" * 100 + "\n")
        f.write("ARTICLES DENETİM BOTU V8 - NOKTA ATIŞI\n")
        f.write(f"Oluşturulma: {datetime.now().isoformat()}\n")
        f.write("=" * 100 + "\n\n")
        
        f.write("📋 NOKTA ATIŞI KRİTERLERİ:\n")
        f.write(f"   - Paragraf sayısı (<p> tag) < {MIN_P_TAG_COUNT}\n")
        f.write(f"   - veya Paragraf içi metin < {MIN_P_TEXT_LEN} karakter\n\n")
        
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
        
        # BOŞ MAKALELER (DETAYLI)
        f.write("=" * 100 + "\n")
        f.write("❌ BOŞ MAKALELER (SİLİNMELİ)\n")
        f.write("=" * 100 + "\n\n")
        
        empty_files = [a for a in analyses if a['is_empty']]
        if empty_files:
            for a in empty_files:
                f.write(f"📁 {a['key']}\n")
                f.write(f"   Hash: {a['hash']} | Dil: {a['lang'].upper()} | Kategori: {a['category']}\n")
                f.write(f"   Boyut: {a['size_kb']} KB | Paragraf sayısı: {a['p_count']} | Paragraf metni: {a['p_text_len']} karakter\n")
                f.write(f"   İlk paragraf: {a['first_p_text'][:150]}...\n")
                f.write(f"   ❌ Sebep: {a['reason']}\n")
                f.write("\n" + "-" * 80 + "\n\n")
        else:
            f.write("   ✅ BOŞ MAKALE YOK\n\n")
        
        f.write("=" * 100 + "\n")
        f.write("🏁 RAPOR SONU\n")
        f.write("=" * 100 + "\n")


def diagnostic_articles():
    print("\n" + "=" * 100)
    print("🔬 ARTICLES DENETİM BOTU V8 - NOKTA ATIŞI")
    print(f"   KRİTER: Paragraf sayısı < {MIN_P_TAG_COUNT} veya paragraf metni < {MIN_P_TEXT_LEN} karakter")
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
    write_report(analyses, output_path)
    
    empty = len([a for a in analyses if a['is_empty']])
    print(f"\n📊 ÖZET:")
    print(f"   Toplam makale: {len(analyses)}")
    print(f"   ❌ BOŞ (paragraf < {MIN_P_TAG_COUNT} veya metin < {MIN_P_TEXT_LEN}): {empty}")
    print(f"\n📄 Rapor: {output_path}")


if __name__ == "__main__":
    diagnostic_articles()
