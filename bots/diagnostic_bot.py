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

# Çok dilli başlık pattern'leri
HEADER_PATTERNS = {
    'introduction': {
        'en': ['Introduction'],
        'es': ['Introducción'],
        'de': ['Einleitung'],
        'fr': ['Introduction']
    },
    'main_analysis': {
        'en': ['Main Analysis'],
        'es': ['Análisis Principal'],
        'de': ['Hauptanalyse'],
        'fr': ['Analyse principale']
    },
    'practical': {
        'en': ['Practical Implications'],
        'es': ['Implicaciones Prácticas'],
        'de': ['Praktische Auswirkungen'],
        'fr': ['Implications pratiques']
    },
    'conclusion': {
        'en': ['Conclusion'],
        'es': ['Conclusión'],
        'de': ['Fazit'],
        'fr': ['Conclusion']
    },
    'key_takeaways': {
        'en': ['Key Takeaways'],
        'es': ['Key Takeaways', 'Puntos Clave'],
        'de': ['Key Takeaways', 'Wichtige Erkenntnisse'],
        'fr': ['Key Takeaways', 'À retenir']
    },
    'faq': {
        'en': ['Frequently Asked Questions', 'FAQ'],
        'es': ['Frequently Asked Questions', 'FAQ', 'Preguntas Frecuentes'],
        'de': ['Frequently Asked Questions', 'FAQ', 'Häufig gestellte Fragen'],
        'fr': ['Frequently Asked Questions', 'FAQ', 'Questions fréquentes']
    }
}

def list_all_html_files():
    """R2'deki tüm HTML dosyalarını listeler"""
    all_files = []
    for lang in LANGUAGES:
        prefix = f"raw-articles/{lang}/"
        try:
            response = s3.list_objects_v2(Bucket=R2_BUCKET, Prefix=prefix)
            if 'Contents' not in response:
                continue
            for obj in response['Contents']:
                key = obj['Key']
                if key.endswith('.html') and not key.endswith('index.html'):
                    all_files.append(key)
        except Exception as e:
            print(f"⚠️ {lang} listelenemedi: {e}")
    return all_files

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
    """Dosya yolundan kategoriyi çıkarır"""
    parts = key.split('/')
    if len(parts) >= 3:
        return parts[2]
    return 'unknown'

def get_file_size_and_char_count(key):
    """Dosya boyutu ve karakter sayısını alır"""
    try:
        response = s3.get_object(Bucket=R2_BUCKET, Key=key)
        content = response['Body'].read().decode('utf-8')
        size_kb = len(content.encode('utf-8')) / 1024
        char_count = len(content)
        return size_kb, char_count, content
    except Exception as e:
        return 0, 0, None

def find_headers(html_content, lang):
    """HTML içinde başlıkları bulur - hangileri var, hangileri yok"""
    result = {}
    
    for section, patterns in HEADER_PATTERNS.items():
        section_patterns = patterns.get(lang, patterns['en'])
        found = False
        found_pattern = None
        
        for pattern in section_patterns:
            # <h2> veya <h3> olarak ara
            if re.search(rf'<h[23]>{pattern}</h[23]>', html_content, re.IGNORECASE):
                found = True
                found_pattern = pattern
                break
        
        result[section] = {
            'found': found,
            'pattern': found_pattern,
            'expected_patterns': section_patterns
        }
    
    return result

def parse_meta_simple(html_content):
    """META yorum satırını basitçe parse et - başarılı mı değil mi"""
    meta_match = re.search(r'<!-- META: (.*?) -->', html_content, re.DOTALL)
    if not meta_match:
        return {'exists': False, 'error': 'META yorum satırı yok'}
    
    meta_content = meta_match.group(1)
    
    # Temel alanları kontrol et
    required_fields = ['author', 'datetime', 'category', 'lang']
    missing_fields = []
    
    for field in required_fields:
        if not re.search(rf'{field}=', meta_content):
            missing_fields.append(field)
    
    return {
        'exists': True,
        'length': len(meta_content),
        'missing_fields': missing_fields,
        'has_cluster': 'cluster_id' in meta_content
    }

def check_html_structure(html_content):
    """HTML yapısının temel bütünlüğünü kontrol eder"""
    issues = []
    
    # h1 kontrolü
    if not re.search(r'<h1>.*?</h1>', html_content, re.DOTALL):
        issues.append('h1 etiketi yok')
    
    # editors-note kontrolü
    if not re.search(r'<div class="editors-note">.*?</div>', html_content, re.DOTALL):
        issues.append('editors-note yok')
    
    # sources kontrolü
    if not re.search(r'<div class="sources">.*?</div>', html_content, re.DOTALL):
        issues.append('sources yok')
    
    # Body içeriği var mı?
    body_match = re.search(r'<body>(.*?)</body>', html_content, re.DOTALL)
    if body_match:
        body_content = body_match.group(1).strip()
        if len(body_content) < 500:
            issues.append(f'body içeriği çok kısa: {len(body_content)} karakter')
    else:
        issues.append('body etiketi yok')
    
    return issues

def detect_language_headers(html_content):
    """Makalenin kendi içindeki başlıkları dillerine göre tespit et"""
    detected = {
        'has_english_headers': False,
        'has_spanish_headers': False,
        'has_german_headers': False,
        'has_french_headers': False,
        'actual_headers_found': []
    }
    
    # Her dil için başlıkları ara
    for lang, patterns in HEADER_PATTERNS.items():
        found_any = False
        for section, section_patterns in patterns.items():
            for pattern in section_patterns:
                if re.search(rf'<h[23]>{pattern}</h[23]>', html_content, re.IGNORECASE):
                    found_any = True
                    detected['actual_headers_found'].append(f"{lang}:{section}:{pattern}")
        if lang == 'en' and found_any:
            detected['has_english_headers'] = True
        elif lang == 'es' and found_any:
            detected['has_spanish_headers'] = True
        elif lang == 'de' and found_any:
            detected['has_german_headers'] = True
        elif lang == 'fr' and found_any:
            detected['has_french_headers'] = True
    
    return detected

def analyze_single_file(key):
    """Tek bir dosyayı analiz eder"""
    size_kb, char_count, content = get_file_size_and_char_count(key)
    
    if not content:
        return None
    
    hash_id = extract_hash_from_key(key)
    lang = extract_lang_from_key(key)
    category = extract_category_from_key(key)
    
    # Başlık kontrolü (dil bazlı)
    headers = find_headers(content, lang)
    
    # Kaç başlık bulundu?
    found_headers_count = sum(1 for v in headers.values() if v['found'])
    
    # META kontrolü
    meta_info = parse_meta_simple(content)
    
    # HTML yapı sorunları
    structure_issues = check_html_structure(content)
    
    # Dil tespiti (makale hangi dilde yazılmış)
    language_detection = detect_language_headers(content)
    
    return {
        'key': key,
        'hash': hash_id,
        'lang': lang,
        'category': category,
        'size_kb': round(size_kb, 2),
        'char_count': char_count,
        'found_headers_count': found_headers_count,
        'headers': headers,
        'meta': meta_info,
        'structure_issues': structure_issues,
        'language_detection': language_detection,
        'is_valid': found_headers_count >= 3 and len(structure_issues) == 0
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

def detect_anomalies(grouped):
    """Anomali tespiti yapar"""
    anomalies = []
    
    for hash_id, items in grouped.items():
        lang_map = {item['lang']: item for item in items}
        
        # Eksik dil kontrolü
        missing_langs = [lang for lang in LANGUAGES if lang not in lang_map]
        if missing_langs:
            anomalies.append({
                'hash': hash_id,
                'type': 'MISSING_LANGUAGE',
                'description': f'Eksik diller: {missing_langs}',
                'details': {lang: 'dosya yok' for lang in missing_langs}
            })
        
        # Karakter sayısı anomali (bir dil diğerlerinden çok farklı)
        if len(lang_map) >= 3:
            sizes = {lang: item['char_count'] for lang, item in lang_map.items()}
            avg_size = sum(sizes.values()) / len(sizes)
            for lang, size in sizes.items():
                if size < avg_size * 0.5:  # %50 daha kısa
                    anomalies.append({
                        'hash': hash_id,
                        'type': 'SHORT_CONTENT',
                        'description': f'{lang.upper()} dili diğerlerinden çok kısa',
                        'details': {
                            'lang': lang,
                            'size': size,
                            'average': round(avg_size, 2),
                            'ratio': round(size / avg_size, 2)
                        }
                    })
        
        # Header anomali kontrolü
        for lang, item in lang_map.items():
            if item['found_headers_count'] < 3:
                # Hangi başlıklar eksik?
                missing_headers = [h for h, v in item['headers'].items() if not v['found']]
                if missing_headers:
                    anomalies.append({
                        'hash': hash_id,
                        'type': 'MISSING_HEADERS',
                        'description': f'{lang.upper()} dilinde eksik başlıklar: {missing_headers}',
                        'details': {
                            'lang': lang,
                            'missing_headers': missing_headers,
                            'found_headers': item['found_headers_count'],
                            'headers_detail': item['headers']
                        }
                    })
        
        # META anomali kontrolü
        for lang, item in lang_map.items():
            if not item['meta']['exists']:
                anomalies.append({
                    'hash': hash_id,
                    'type': 'MISSING_META',
                    'description': f'{lang.upper()} dilinde META yorum satırı yok',
                    'details': {'lang': lang}
                })
            elif item['meta']['missing_fields']:
                anomalies.append({
                    'hash': hash_id,
                    'type': 'INCOMPLETE_META',
                    'description': f'{lang.upper()} dilinde META eksik alanlar: {item["meta"]["missing_fields"]}',
                    'details': {'lang': lang, 'missing_fields': item['meta']['missing_fields']}
                })
        
        # Yapı anomali kontrolü
        for lang, item in lang_map.items():
            if item['structure_issues']:
                anomalies.append({
                    'hash': hash_id,
                    'type': 'STRUCTURE_ISSUE',
                    'description': f'{lang.upper()} dilinde yapı sorunları: {item["structure_issues"]}',
                    'details': {'lang': lang, 'issues': item['structure_issues']}
                })
        
        # Dil uyumsuzluğu (makale başlıkları ile dosya dili farklı)
        for lang, item in lang_map.items():
            detection = item['language_detection']
            if lang == 'en' and not detection['has_english_headers']:
                anomalies.append({
                    'hash': hash_id,
                    'type': 'LANGUAGE_MISMATCH',
                    'description': f'EN dosyasında İngilizce başlık bulunamadı',
                    'details': {'lang': lang, 'detected': detection}
                })
            elif lang == 'es' and not detection['has_spanish_headers']:
                anomalies.append({
                    'hash': hash_id,
                    'type': 'LANGUAGE_MISMATCH',
                    'description': f'ES dosyasında İspanyolca başlık bulunamadı',
                    'details': {'lang': lang, 'detected': detection}
                })
            elif lang == 'de' and not detection['has_german_headers']:
                anomalies.append({
                    'hash': hash_id,
                    'type': 'LANGUAGE_MISMATCH',
                    'description': f'DE dosyasında Almanca başlık bulunamadı',
                    'details': {'lang': lang, 'detected': detection}
                })
            elif lang == 'fr' and not detection['has_french_headers']:
                anomalies.append({
                    'hash': hash_id,
                    'type': 'LANGUAGE_MISMATCH',
                    'description': f'FR dosyasında Fransızca başlık bulunamadı',
                    'details': {'lang': lang, 'detected': detection}
                })
    
    return anomalies

def print_report(analyses, grouped, anomalies):
    """Rapor yazdırır"""
    print("\n" + "=" * 80)
    print("📊 RAW-ARTICLES TANI BOTU RAPORU")
    print("=" * 80)
    
    # Genel istatistik
    valid_count = sum(1 for a in analyses if a and a['is_valid'])
    total_count = len([a for a in analyses if a])
    
    print(f"\n📈 GENEL İSTATİSTİK:")
    print(f"   Toplam dosya: {total_count}")
    print(f"   Geçerli dosya: {valid_count}")
    print(f"   Geçersiz dosya: {total_count - valid_count}")
    
    # Hash istatistikleri
    print(f"\n🔑 HASH İSTATİSTİKLERİ:")
    print(f"   Toplam hash: {len(grouped)}")
    
    complete_hashes = sum(1 for items in grouped.values() if len(items) == 4)
    print(f"   4 dil tamam: {complete_hashes}")
    print(f"   Eksik dil: {len(grouped) - complete_hashes}")
    
    # Anomaliler
    print(f"\n⚠️ ANOMALİLER ({len(anomalies)} adet):")
    print("-" * 60)
    
    for anomaly in anomalies:
        print(f"\n🔴 [{anomaly['type']}] Hash: {anomaly['hash']}")
        print(f"   {anomaly['description']}")
        if 'details' in anomaly:
            for k, v in anomaly['details'].items():
                print(f"   └─ {k}: {v}")
    
    # Detaylı dosya bazlı rapor (sadece problemli olanlar)
    print("\n" + "=" * 80)
    print("📄 PROBLEMLİ DOSYALAR (DETAYLI)")
    print("=" * 80)
    
    problem_files = [a for a in analyses if a and not a['is_valid']]
    for pf in problem_files[:20]:  # İlk 20 problemli dosya
        print(f"\n📁 {pf['key']}")
        print(f"   Hash: {pf['hash']} | Dil: {pf['lang'].upper()} | Kategori: {pf['category']}")
        print(f"   Boyut: {pf['size_kb']} KB | Karakter: {pf['char_count']}")
        print(f"   Bulunan başlık sayısı: {pf['found_headers_count']}/6")
        
        if pf['structure_issues']:
            print(f"   🏗️ Yapı sorunları: {pf['structure_issues']}")
        
        if not pf['meta']['exists']:
            print(f"   🔖 META: YOK")
        elif pf['meta']['missing_fields']:
            print(f"   🔖 META: Eksik alanlar {pf['meta']['missing_fields']}")
        
        # Eksik başlıkları göster
        missing = [h for h, v in pf['headers'].items() if not v['found']]
        if missing:
            print(f"   📌 Eksik başlıklar: {missing}")
            for h in missing:
                expected = pf['headers'][h]['expected_patterns']
                print(f"      - {h}: aranan {expected}")
    
    # Özet JSON çıktısı
    print("\n" + "=" * 80)
    print("📋 ÖZET JSON (anomaliler)")
    print("=" * 80)
    summary = {
        "generated": datetime.now().isoformat(),
        "total_files": total_count,
        "valid_files": valid_count,
        "total_hashes": len(grouped),
        "complete_hashes": complete_hashes,
        "anomalies": anomalies[:50]  # İlk 50 anomali
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))

def diagnostic_bot():
    """Ana teşhis botu"""
    print("\n" + "=" * 80)
    print("🔬 RAW-ARTICLES TANI BOTU V1")
    print("   Amaç: Makeup/Publisher'ın neden parse edemediğini tespit etmek")
    print("=" * 80)
    
    print("\n📂 R2'den dosyalar listeleniyor...")
    files = list_all_html_files()
    print(f"   Toplam {len(files)} HTML dosyası bulundu.")
    
    print("\n🔍 Dosyalar analiz ediliyor...")
    analyses = []
    for i, file_key in enumerate(files):
        if i % 100 == 0 and i > 0:
            print(f"   İlerleme: {i}/{len(files)}")
        analysis = analyze_single_file(file_key)
        if analysis:
            analyses.append(analysis)
    
    print(f"\n   Analiz tamamlandı. {len(analyses)} dosya başarıyla işlendi.")
    
    # Hash bazında grupla
    grouped = group_by_hash(analyses)
    
    # Anomali tespiti
    anomalies = detect_anomalies(grouped)
    
    # Rapor yazdır
    print_report(analyses, grouped, anomalies)
    
    print("\n" + "=" * 80)
    print("🏁 TANI BOTU TAMAMLANDI!")
    print("   Yukarıdaki anomaliler, Makeup/Publisher'ın neden parse edemediğini gösterir.")
    print("=" * 80)

if __name__ == "__main__":
    diagnostic_bot()
