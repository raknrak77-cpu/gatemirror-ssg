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

# Makeup'ın gerçekten ihtiyaç duyduğu şeyler (META hariç, yazar hariç)
REQUIRED_FOR_PARSE = {
    'has_h1': r'<h1>.*?</h1>',
    'has_editors_note': r'<div class="editors-note">.*?</div>',
    'has_key_takeaways': r'<h2>Key Takeaways</h2>',
    'has_sources': r'<div class="sources">.*?</div>',
    'has_intro': r'<h2>Introduction</h2>',      # Makeup İngilizce arıyor
    'has_main_analysis': r'<h2>Main Analysis</h2>',  # Makeup İngilizce arıyor
    'has_practical': r'<h2>Practical Implications</h2>',
    'has_conclusion': r'<h2>Conclusion</h2>',
    'has_faq': r'<h2>Frequently Asked Questions</h2>',
    'has_body': r'<body>.*?</body>',
}

def list_all_files():
    """Tüm HTML dosyalarını listele"""
    files = []
    for lang in LANGUAGES:
        prefix = f"raw-articles/{lang}/"
        try:
            response = s3.list_objects_v2(Bucket=R2_BUCKET, Prefix=prefix)
            if 'Contents' not in response:
                continue
            for obj in response['Contents']:
                key = obj['Key']
                if key.endswith('.html') and not key.endswith('index.html'):
                    files.append(key)
        except Exception as e:
            print(f"⚠️ {lang} listelenemedi: {e}")
    return files

def analyze_file(key):
    """Tek dosyayı Makeup perspektifinden analiz et"""
    try:
        response = s3.get_object(Bucket=R2_BUCKET, Key=key)
        content = response['Body'].read().decode('utf-8')
        size_kb = len(content.encode('utf-8')) / 1024
    except:
        return None
    
    # Hash ve dil bilgisi
    filename = key.split('/')[-1]
    hash_id = filename.split('-')[0] if '-' in filename else filename.replace('.html', '')
    lang = key.split('/')[1] if len(key.split('/')) >= 2 else 'unknown'
    
    # Makeup'ın ihtiyaç duyduğu kontroller
    checks = {}
    for check_name, pattern in REQUIRED_FOR_PARSE.items():
        found = re.search(pattern, content, re.DOTALL | re.IGNORECASE) is not None
        checks[check_name] = found
    
    # Özet: Makeup parse edebilir mi?
    # has_intro ve has_main_analysis ZORUNLU (çünkü split_article_content bunları arıyor)
    can_parse = checks['has_intro'] and checks['has_main_analysis']
    
    # Eksik olanlar (sadece önemli olanlar)
    missing = []
    if not checks['has_intro']:
        missing.append('Introduction')
    if not checks['has_main_analysis']:
        missing.append('Main Analysis')
    if not checks['has_practical']:
        missing.append('Practical Implications')
    if not checks['has_conclusion']:
        missing.append('Conclusion')
    
    return {
        'key': key,
        'hash': hash_id,
        'lang': lang,
        'size_kb': round(size_kb, 2),
        'can_parse': can_parse,
        'missing': missing,
        'checks': checks
    }

def write_report(analyses, output_path):
    """TXT rapor yaz"""
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("RAW-ARTICLES TANI BOTU V2 - MAKEPERSPEKTİFİ\n")
        f.write(f"Oluşturulma: {datetime.now().isoformat()}\n")
        f.write("=" * 80 + "\n\n")
        
        # İstatistikler
        total = len(analyses)
        parseable = sum(1 for a in analyses if a['can_parse'])
        not_parseable = total - parseable
        
        f.write("📊 GENEL İSTATİSTİKLER\n")
        f.write("-" * 40 + "\n")
        f.write(f"Toplam dosya: {total}\n")
        f.write(f"Parse edilebilir: {parseable}\n")
        f.write(f"Parse edilemez: {not_parseable}\n\n")
        
        # Dil bazında
        f.write("📊 DİL BAZINDA DURUM\n")
        f.write("-" * 40 + "\n")
        for lang in LANGUAGES:
            lang_files = [a for a in analyses if a['lang'] == lang]
            lang_parseable = sum(1 for a in lang_files if a['can_parse'])
            f.write(f"{lang.upper()}: {len(lang_files)} dosya, {lang_parseable} parse edilebilir\n")
        f.write("\n")
        
        # PARSE EDİLEMEYEN DOSYALAR (ASIL ÖNEMLİ)
        f.write("=" * 80 + "\n")
        f.write("❌ PARSE EDİLEMEYEN DOSYALAR\n")
        f.write("=" * 80 + "\n\n")
        
        not_parseable_files = [a for a in analyses if not a['can_parse']]
        for a in not_parseable_files:
            f.write(f"📁 {a['key']}\n")
            f.write(f"   Hash: {a['hash']} | Dil: {a['lang'].upper()} | Boyut: {a['size_kb']} KB\n")
            f.write(f"   ❌ Eksik: {', '.join(a['missing'])}\n")
            
            # Özel not: eğer sadece Intro/Main eksikse
            if not a['checks']['has_intro'] and not a['checks']['has_main_analysis']:
                f.write(f"   ⚠️ KRİTİK: Introduction ve Main Analysis tag'leri yok - Makeup split yapamaz\n")
            elif not a['checks']['has_intro']:
                f.write(f"   ⚠️ Introduction tag'i yok\n")
            elif not a['checks']['has_main_analysis']:
                f.write(f"   ⚠️ Main Analysis tag'i yok\n")
            f.write("\n")
        
        # PARSE EDİLEBİLENLER (kısa özet)
        f.write("=" * 80 + "\n")
        f.write("✅ PARSE EDİLEBİLEN DOSYALAR (ÖZET)\n")
        f.write("=" * 80 + "\n")
        
        parseable_files = [a for a in analyses if a['can_parse']]
        for a in parseable_files[:50]:  # İlk 50
            f.write(f"✅ {a['key']} ({a['size_kb']} KB)\n")
        
        if len(parseable_files) > 50:
            f.write(f"\n... ve {len(parseable_files) - 50} dosya daha\n")
        
        # Sonuç özeti
        f.write("\n" + "=" * 80 + "\n")
        f.write("🔍 SONUÇ\n")
        f.write("=" * 80 + "\n")
        f.write(f"Makeup'ın parse edebilmesi için Introduction ve Main Analysis tag'leri ZORUNLU.\n")
        f.write(f"Bunlar olmadan split_article_content() çalışmaz ve content boş kalır.\n\n")
        
        if not_parseable > 0:
            f.write(f"⚠️ {not_parseable} dosyada Introduction veya Main Analysis tag'i EKSİK.\n")
            f.write(f"Bu dosyalar Publisher'da 'içi boş' görünecektir.\n")
        else:
            f.write(f"✅ Tüm dosyalar parse edilebilir durumda.\n")
    
    print(f"📄 Rapor kaydedildi: {output_path}")

def diagnostic_bot():
    print("\n" + "=" * 80)
    print("🔬 RAW-ARTICLES TANI BOTU V2 - MAKEPERSPEKTİFİ")
    print("   Sadece Makeup'ın parse etmesi için gerekenleri kontrol eder")
    print("=" * 80)
    
    print("\n📂 R2'den dosyalar listeleniyor...")
    files = list_all_files()
    print(f"   Toplam {len(files)} HTML dosyası bulundu.")
    
    print("\n🔍 Dosyalar analiz ediliyor...")
    analyses = []
    for i, f in enumerate(files):
        if i % 100 == 0 and i > 0:
            print(f"   İlerleme: {i}/{len(files)}")
        analysis = analyze_file(f)
        if analysis:
            analyses.append(analysis)
    
    print(f"\n   Analiz tamamlandı. {len(analyses)} dosya işlendi.")
    
    # Rapor yaz
    output_path = "diagnostic_report.txt"
    write_report(analyses, output_path)
    
    # Özeti ekrana yazdır
    parseable = sum(1 for a in analyses if a['can_parse'])
    print(f"\n📊 ÖZET:")
    print(f"   Toplam: {len(analyses)}")
    print(f"   Parse edilebilir: {parseable}")
    print(f"   Parse edilemez: {len(analyses) - parseable}")
    print(f"\n📄 Rapor: {output_path}")

if __name__ == "__main__":
    diagnostic_bot()
