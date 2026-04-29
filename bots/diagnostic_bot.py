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

# Makeup'ın aradığı İngilizce pattern'ler
MAKEUP_PATTERNS = {
    'intro': r'<h2>Introduction</h2>',
    'main_analysis': r'<h2>Main Analysis</h2>',
    'practical': r'<h2>Practical Implications</h2>',
    'conclusion': r'<h2>Conclusion</h2>',
    'key_takeaways': r'<h2>Key Takeaways</h2>',
    'faq': r'<h2>Frequently Asked Questions</h2>'
}

# Alternatif başlıklar (dillere göre)
ALTERNATIVE_HEADERS = {
    'es': {
        'intro': [r'<h2>Introducción</h2>', r'<h2>Introducción:</h2>', r'<h2>Contexto</h2>', r'<h2>El problema</h2>'],
        'main_analysis': [r'<h2>Análisis Principal</h2>', r'<h2>Análisis:</h2>', r'<h2>Desarrollo</h2>', r'<h2>Metodología</h2>'],
        'practical': [r'<h2>Implicaciones Prácticas</h2>', r'<h2>Aplicaciones</h2>'],
        'conclusion': [r'<h2>Conclusión</h2>', r'<h2>Conclusiones</h2>']
    },
    'de': {
        'intro': [r'<h2>Einleitung</h2>', r'<h2>Einleitung:</h2>', r'<h2>Hintergrund</h2>'],
        'main_analysis': [r'<h2>Hauptanalyse</h2>', r'<h2>Analyse</h2>', r'<h2>Methodik</h2>'],
        'practical': [r'<h2>Praktische Auswirkungen</h2>', r'<h2>Anwendung</h2>'],
        'conclusion': [r'<h2>Fazit</h2>', r'<h2>Schlussfolgerung</h2>']
    },
    'fr': {
        'intro': [r'<h2>Introduction</h2>', r'<h2>Contexte</h2>', r'<h2>Problématique</h2>'],
        'main_analysis': [r'<h2>Analyse principale</h2>', r'<h2>Analyse</h2>', r'<h2>Méthodologie</h2>'],
        'practical': [r'<h2>Implications pratiques</h2>', r'<h2>Applications</h2>'],
        'conclusion': [r'<h2>Conclusion</h2>', r'<h2>Conclusions</h2>']
    }
}

def list_all_files():
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

def extract_hash_from_key(key):
    filename = key.split('/')[-1]
    if '-' in filename:
        return filename.split('-')[0]
    return filename.replace('.html', '')

def get_file_info(key):
    try:
        response = s3.get_object(Bucket=R2_BUCKET, Key=key)
        content = response['Body'].read().decode('utf-8')
        size_kb = len(content.encode('utf-8')) / 1024
        return size_kb, content
    except Exception as e:
        return 0, None

def analyze_file(key):
    size_kb, content = get_file_info(key)
    if not content:
        return None
    
    filename = key.split('/')[-1]
    hash_id = extract_hash_from_key(key)
    lang = key.split('/')[1] if len(key.split('/')) >= 2 else 'unknown'
    category = key.split('/')[2] if len(key.split('/')) >= 3 else 'unknown'
    
    # 1. Makeup'ın aradığı İngilizce başlıklar var mı?
    makeup_found = {}
    for check_name, pattern in MAKEUP_PATTERNS.items():
        makeup_found[check_name] = re.search(pattern, content, re.IGNORECASE) is not None
    
    # 2. Alternatif başlıklar var mı? (dil bazlı)
    alternatives_found = {}
    if lang in ALTERNATIVE_HEADERS:
        for section, patterns in ALTERNATIVE_HEADERS[lang].items():
            found = False
            found_pattern = None
            for pattern in patterns:
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    found = True
                    found_pattern = pattern
                    break
            alternatives_found[section] = {'found': found, 'pattern': found_pattern}
    
    # 3. En yaygın hata: GERÇEKTE ne var? (tüm h2 tag'lerini bul)
    all_h2_tags = re.findall(r'<h2>(.*?)</h2>', content, re.DOTALL)
    all_h2_tags = [tag.strip() for tag in all_h2_tags[:10]]  # ilk 10
    
    # 4. Makeup parse edebilir mi?
    # Makeup için INTRO ve MAIN_ANALYSIS ZORUNLU (İngilizce)
    can_parse = makeup_found['intro'] and makeup_found['main_analysis']
    
    # 5. Neden parse edemiyor?
    reason = None
    if not can_parse:
        if not makeup_found['intro'] and not makeup_found['main_analysis']:
            if lang in ALTERNATIVE_HEADERS:
                has_alt_intro = alternatives_found.get('intro', {}).get('found', False)
                has_alt_main = alternatives_found.get('main_analysis', {}).get('found', False)
                if has_alt_intro and has_alt_main:
                    reason = f"Alternatif başlık kullanılmış (bulunan: intro:{alternatives_found.get('intro',{}).get('pattern','?')}, main:{alternatives_found.get('main_analysis',{}).get('pattern','?')})"
                elif has_alt_intro:
                    reason = f"Giriş bölümü farklı başlık: '{alternatives_found.get('intro',{}).get('pattern','?')}' (Makeup 'Introduction' arıyor)"
                elif has_alt_main:
                    reason = f"Ana analiz bölümü farklı başlık: '{alternatives_found.get('main_analysis',{}).get('pattern','?')}' (Makeup 'Main Analysis' arıyor)"
                else:
                    reason = "Ne İngilizce ne de alternatif başlık bulunamadı"
            else:
                reason = f"İngilizce başlık yok ve {lang} için alternatif tanımlı değil"
        elif not makeup_found['intro']:
            reason = "Introduction tag'i eksik"
        elif not makeup_found['main_analysis']:
            reason = "Main Analysis tag'i eksik"
    
    return {
        'key': key,
        'hash': hash_id,
        'lang': lang,
        'category': category,
        'size_kb': round(size_kb, 2),
        'can_parse': can_parse,
        'reason': reason,
        'makeup_found': makeup_found,
        'alternatives_found': alternatives_found if lang in ALTERNATIVE_HEADERS else None,
        'actual_h2_tags': all_h2_tags
    }

def write_report(analyses, output_path):
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("=" * 100 + "\n")
        f.write("DIAGNOSTIC BOT V3 - MAKEPARSE TEŞHİS RAPORU\n")
        f.write(f"Oluşturulma: {datetime.now().isoformat()}\n")
        f.write("=" * 100 + "\n\n")
        
        # İstatistikler
        total = len(analyses)
        parseable = sum(1 for a in analyses if a['can_parse'])
        not_parseable = total - parseable
        
        f.write("📊 GENEL İSTATİSTİKLER\n")
        f.write("-" * 50 + "\n")
        f.write(f"Toplam dosya: {total}\n")
        f.write(f"Parse edilebilir: {parseable}\n")
        f.write(f"Parse edilemez: {not_parseable}\n\n")
        
        # Dil bazında
        f.write("📊 DİL BAZINDA DURUM\n")
        f.write("-" * 50 + "\n")
        for lang in LANGUAGES:
            lang_files = [a for a in analyses if a['lang'] == lang]
            lang_parseable = sum(1 for a in lang_files if a['can_parse'])
            f.write(f"{lang.upper()}: {len(lang_files)} dosya, {lang_parseable} parse edilebilir, {len(lang_files)-lang_parseable} parse edilemez\n")
        f.write("\n")
        
        # ================================================================
        # PARSE EDİLEMEYENLER - DETAYLI TEŞHİS
        # ================================================================
        f.write("=" * 100 + "\n")
        f.write("🔬 PARSE EDİLEMEYEN DOSYALAR - DETAYLI TEŞHİS\n")
        f.write("=" * 100 + "\n\n")
        
        not_parseable_files = [a for a in analyses if not a['can_parse']]
        for a in not_parseable_files:
            f.write(f"📁 {a['key']}\n")
            f.write(f"   Hash: {a['hash']} | Dil: {a['lang'].upper()} | Kategori: {a['category']} | Boyut: {a['size_kb']} KB\n")
            f.write(f"\n   ❌ Makeup parse edemiyor çünkü:\n")
            f.write(f"      {a['reason']}\n")
            f.write(f"\n   📌 Makeup'ın aradığı İngilizce başlıklar:\n")
            for section, found in a['makeup_found'].items():
                f.write(f"      - {section}: {'✅' if found else '❌'}\n")
            
            if a['alternatives_found']:
                f.write(f"\n   🌐 {a['lang'].upper()} dilinde alternatif başlıklar:\n")
                for section, info in a['alternatives_found'].items():
                    if info['found']:
                        f.write(f"      - {section}: ✅ bulundu ('{info['pattern']}')\n")
                    else:
                        f.write(f"      - {section}: ❌ bulunamadı\n")
            
            f.write(f"\n   📝 Gerçek <h2> başlıkları (ilk 5):\n")
            for i, tag in enumerate(a['actual_h2_tags'][:5]):
                f.write(f"      {i+1}. {tag}\n")
            
            # Çözüm önerisi
            f.write(f"\n   🔧 ÇÖZÜM ÖNERİSİ:\n")
            if a['alternatives_found']:
                has_alt = any(info['found'] for info in a['alternatives_found'].values())
                if has_alt:
                    f.write(f"      Makeup'ın çok dilli başlıkları tanıması için ALTERNATIVE_HEADERS güncellenmeli.\n")
                    f.write(f"      Veya bu dosyadaki başlıklar İngilizce'ye çevrilmeli.\n")
                else:
                    f.write(f"      Dosyada hiçbir başlık bulunamadı. Gemini yanıtı eksik olabilir.\n")
            else:
                f.write(f"      {a['lang'].upper()} için ALTERNATIVE_HEADERS tanımlı değil. Önce tanımlanmalı.\n")
            f.write("\n" + "-" * 80 + "\n\n")
        
        # ================================================================
        # ÇÖZÜM ÖZETİ
        # ================================================================
        f.write("=" * 100 + "\n")
        f.write("✅ ÇÖZÜM ÖZETİ\n")
        f.write("=" * 100 + "\n\n")
        
        # Hata türlerine göre gruplandır
        reason_counts = {}
        for a in not_parseable_files:
            reason = a['reason']
            if reason not in reason_counts:
                reason_counts[reason] = 0
            reason_counts[reason] += 1
        
        f.write("Hata türlerine göre dağılım:\n")
        for reason, count in reason_counts.items():
            f.write(f"   - {reason}: {count} dosya\n")
        
        f.write("\n🔧 ÖNERİLEN AKSİYONLAR:\n")
        f.write("   1. Makeup'a çok dilli başlık desteği ekle (ALTERNATIVE_HEADERS)\n")
        f.write("   2. Veya Creator'dan İngilizce başlık zorla (her dil için Introduction kullan)\n")
        f.write("   3. Veya bu 54 dosyayı manuel düzelt\n")
        
        f.write("\n" + "=" * 100 + "\n")
        f.write("🏁 RAPOR SONU\n")
        f.write("=" * 100 + "\n")

def diagnostic_bot():
    print("\n" + "=" * 100)
    print("🔬 DIAGNOSTIC BOT V3 - MAKEPARSE TEŞHİS")
    print("   Amaç: Makeup'ın neden parse edemediğini tespit etmek")
    print("=" * 100)
    
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
    
    output_path = "diagnostic_report.txt"
    write_report(analyses, output_path)
    
    parseable = sum(1 for a in analyses if a['can_parse'])
    print(f"\n📊 ÖZET:")
    print(f"   Toplam: {len(analyses)}")
    print(f"   Parse edilebilir: {parseable}")
    print(f"   Parse edilemez: {len(analyses) - parseable}")
    print(f"\n📄 Rapor: {output_path}")

if __name__ == "__main__":
    diagnostic_bot()
