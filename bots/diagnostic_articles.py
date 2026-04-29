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

# Dil bazlı beklenen başlıklar
EXPECTED_HEADERS = {
    'en': ['Introduction', 'Main Analysis', 'Practical Implications', 'Conclusion'],
    'es': ['Introducción', 'Análisis Principal', 'Implicaciones Prácticas', 'Conclusión'],
    'de': ['Einleitung', 'Hauptanalyse', 'Praktische Auswirkungen', 'Fazit'],
    'fr': ['Introduction', 'Analyse principale', 'Implications pratiques', 'Conclusion']
}

# Minimum eşikler
MIN_CLEAN_TEXT_LEN = 500     # Temiz metin minimum karakter
MIN_WORD_COUNT = 80           # Minimum kelime sayısı (yaklaşık 500 karaktere denk)
MIN_H2_COUNT = 2              # Minimum h2 başlık sayısı (en az Intro + bir şey)


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
    """Dosya yolundan hash'i çıkarır"""
    filename = key.split('/')[-1]
    if '-' in filename:
        return filename.split('-')[0]
    return filename.replace('.html', '')


def extract_lang_from_key(key):
    """Dosya yolundan dili çıkarır"""
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
    """Tek bir makaleyi analiz eder"""
    try:
        response = s3.get_object(Bucket=R2_BUCKET, Key=key)
        content = response['Body'].read().decode('utf-8')
        size_kb = len(content.encode('utf-8')) / 1024
    except Exception as e:
        return None
    
    hash_id = extract_hash_from_key(key)
    lang = extract_lang_from_key(key)
    category = extract_category_from_key(key)
    
    # 1. TEMİZ METİN (tag'leri temizle)
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
    
    # 4. BEKLENEN BAŞLIKLAR VAR MI? (dil bazlı)
    expected = EXPECTED_HEADERS.get(lang, EXPECTED_HEADERS['en'])
    found_headers = []
    missing_headers = []
    
    for header in expected:
        if re.search(rf'<h2>{header}</h2>', content, re.IGNORECASE):
            found_headers.append(header)
        else:
            missing_headers.append(header)
    
    # 5. META KONTROLÜ
    meta_match = re.search(r'<!-- META: (.*?) -->', content, re.DOTALL)
    has_meta = meta_match is not None
    
    # 6. GÖRSEL KONTROLÜ (URL var mı, gerçekten var mı kontrol etme)
    cover_image_match = re.search(r'cover_image["\']?\s*:\s*["\']([^"\']+)', content)
    content_img1_match = re.search(r'content_image_1["\']?\s*:\s*["\']([^"\']+)', content)
    content_img2_match = re.search(r'content_image_2["\']?\s*:\s*["\']([^"\']+)', content)
    
    has_cover = cover_image_match is not None
    has_img1 = content_img1_match is not None
    has_img2 = content_img2_match is not None
    
    # 7. MAKALE SAĞLIKLI MI?
    is_healthy = (
        clean_text_len >= MIN_CLEAN_TEXT_LEN and
        word_count >= MIN_WORD_COUNT and
        h2_count >= MIN_H2_COUNT and
        len(missing_headers) <= 2  # En fazla 2 başlık eksik olabilir
    )
    
    # 8. HATA NEDENİ
    issues = []
    if clean_text_len < MIN_CLEAN_TEXT_LEN:
        issues.append(f"temiz_metin_kisa({clean_text_len}<{MIN_CLEAN_TEXT_LEN})")
    if word_count < MIN_WORD_COUNT:
        issues.append(f"kelime_az({word_count}<{MIN_WORD_COUNT})")
    if h2_count < MIN_H2_COUNT:
        issues.append(f"h2_az({h2_count}<{MIN_H2_COUNT})")
    if missing_headers:
        issues.append(f"eksik_başlıklar:{','.join(missing_headers[:2])}")
    if not has_meta:
        issues.append("meta_yok")
    
    return {
        'key': key,
        'hash': hash_id,
        'lang': lang,
        'category': category,
        'size_kb': round(size_kb, 2),
        'clean_text_len': clean_text_len,
        'word_count': word_count,
        'h2_count': h2_count,
        'h2_tags': h2_tags[:10],
        'found_headers': found_headers,
        'missing_headers': missing_headers,
        'has_meta': has_meta,
        'has_cover': has_cover,
        'has_img1': has_img1,
        'has_img2': has_img2,
        'is_healthy': is_healthy,
        'issues': issues
    }


def group_by_hash(analyses):
    """Analizleri hash'e göre gruplar"""
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
        f.write("ARTICLES DENETİM BOTU V1 - YAYINLANAN MAKALE KALİTE KONTROLÜ\n")
        f.write(f"Oluşturulma: {datetime.now().isoformat()}\n")
        f.write("=" * 100 + "\n\n")
        
        total = len(analyses)
        healthy = sum(1 for a in analyses if a['is_healthy'])
        unhealthy = total - healthy
        
        f.write("📊 GENEL İSTATİSTİKLER\n")
        f.write("-" * 50 + "\n")
        f.write(f"Toplam makale: {total}\n")
        f.write(f"Sağlıklı makale: {healthy}\n")
        f.write(f"Sorunlu makale: {unhealthy}\n\n")
        
        # Dil bazında
        f.write("📊 DİL BAZINDA DURUM\n")
        f.write("-" * 50 + "\n")
        for lang in LANGUAGES:
            lang_articles = [a for a in analyses if a['lang'] == lang]
            lang_healthy = sum(1 for a in lang_articles if a['is_healthy'])
            f.write(f"{lang.upper()}: {len(lang_articles)} makale, {lang_healthy} sağlıklı, {len(lang_articles)-lang_healthy} sorunlu\n")
        f.write("\n")
        
        # Hash bazında (4 dil kontrolü)
        f.write("=" * 100 + "\n")
        f.write("🔑 HASH BAZINDA 4 DİL KONTROLÜ\n")
        f.write("=" * 100 + "\n\n")
        
        for hash_id, items in grouped.items():
            langs_present = [item['lang'] for item in items]
            missing_langs = [lang for lang in LANGUAGES if lang not in langs_present]
            
            # Tüm diller sağlıklı mı?
            all_healthy = all(item['is_healthy'] for item in items)
            
            if missing_langs or not all_healthy:
                f.write(f"📁 Hash: {hash_id}\n")
                f.write(f"   Mevcut diller: {', '.join(langs_present)}\n")
                if missing_langs:
                    f.write(f"   ❌ Eksik diller: {', '.join(missing_langs)}\n")
                for item in items:
                    status = "✅" if item['is_healthy'] else "❌"
                    f.write(f"   {status} {item['lang'].upper()}: {item['clean_text_len']} karakter, {item['word_count']} kelime, {item['h2_count']} h2\n")
                    if not item['is_healthy'] and item['issues']:
                        f.write(f"      Sorunlar: {', '.join(item['issues'])}\n")
                f.write("\n")
        
        # SORUNLU MAKALELER (detaylı)
        f.write("=" * 100 + "\n")
        f.write("❌ SORUNLU MAKALELER (DETAYLI)\n")
        f.write("=" * 100 + "\n\n")
        
        unhealthy_articles = [a for a in analyses if not a['is_healthy']]
        for a in unhealthy_articles:
            f.write(f"📁 {a['key']}\n")
            f.write(f"   Hash: {a['hash']} | Dil: {a['lang'].upper()} | Kategori: {a['category']}\n")
            f.write(f"   Boyut: {a['size_kb']} KB\n")
            f.write(f"   Temiz metin: {a['clean_text_len']} karakter\n")
            f.write(f"   Kelime: {a['word_count']}\n")
            f.write(f"   h2 sayısı: {a['h2_count']}\n")
            f.write(f"   Bulunan başlıklar: {a['found_headers'][:3]}\n")
            f.write(f"   Eksik başlıklar: {a['missing_headers']}\n")
            f.write(f"   META: {'✅' if a['has_meta'] else '❌'}\n")
            f.write(f"   Görseller: kapak:{'✅' if a['has_cover'] else '❌'}, icerik1:{'✅' if a['has_img1'] else '❌'}, icerik2:{'✅' if a['has_img2'] else '❌'}\n")
            f.write(f"   ❌ Sorunlar: {', '.join(a['issues'])}\n")
            f.write("\n" + "-" * 80 + "\n\n")
        
        # ÖZET
        f.write("=" * 100 + "\n")
        f.write("✅ ÖZET VE ÖNERİLER\n")
        f.write("=" * 100 + "\n\n")
        
        f.write(f"Sağlıklı makale sayısı: {healthy}\n")
        f.write(f"Sorunlu makale sayısı: {unhealthy}\n\n")
        
        if unhealthy > 0:
            f.write("🔧 ÖNERİLEN AKSİYONLAR:\n")
            f.write("   1. Yukarıdaki sorunlu makalelerin hash'lerini not alın\n")
            f.write("   2. Bu hash'lere ait raw-articles dosyalarını kontrol edin\n")
            f.write("   3. Eğer raw-articles da boşsa, R2'den silin ve task'ı yeniden işletin\n")
            f.write("   4. Eğer raw-articles dolu ama articles boşsa, Publisher'dan geçmemiştir\n")
        else:
            f.write("✅ Tüm makaleler sağlıklı görünüyor!\n")
        
        f.write("\n" + "=" * 100 + "\n")
        f.write("🏁 RAPOR SONU\n")
        f.write("=" * 100 + "\n")


def diagnostic_articles():
    print("\n" + "=" * 100)
    print("🔬 ARTICLES DENETİM BOTU V1")
    print("   Amaç: Yayınlanan makalelerin kalitesini kontrol etmek")
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
    
    healthy = sum(1 for a in analyses if a['is_healthy'])
    print(f"\n📊 ÖZET:")
    print(f"   Toplam makale: {len(analyses)}")
    print(f"   Sağlıklı makale: {healthy}")
    print(f"   Sorunlu makale: {len(analyses) - healthy}")
    print(f"\n📄 Rapor: {output_path}")

if __name__ == "__main__":
    diagnostic_articles()
