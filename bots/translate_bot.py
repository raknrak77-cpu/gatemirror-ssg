import os
import re
import json
import time
import requests
from datetime import datetime
from bs4 import BeautifulSoup
import boto3
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

# Gemini API
GEMINI_KEY = os.getenv('GEMINI_API_KEY')
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={GEMINI_KEY}"

LOOKBACK_MINUTES = 10  # Son 10 dakika

# ================= YARDIMCI FONKSİYONLAR =================
def is_recent_file(last_modified):
    """R2 objesinin son LOOKBACK_MINUTES dakika içinde değişip değişmediğini kontrol eder"""
    now = datetime.now().astimezone()
    cutoff = now - timedelta(minutes=LOOKBACK_MINUTES)
    return last_modified > cutoff

def create_spanish_slug(title):
    """İngilizce başlıktan İspanyolca slug üretir (özel karakterleri temizler)"""
    # Basit bir yaklaşım: başlığı küçült, özel karakterleri temizle
    # İleride Gemini ile de üretebiliriz ama şimdilik bu yeterli
    slug = title.lower()
    slug = re.sub(r'[^a-z0-9]+', '-', slug)
    slug = slug.strip('-')
    slug = re.sub(r'-+', '-', slug)
    return slug[:60]

def rewrite_article_to_spanish(en_html, en_title, en_slug):
    """
    Tek API çağrısı ile tüm makaleyi İspanyolca'ya yeniden yazar.
    HTML yapısını korur, sadece metin içeriğini çevirir/uyarlar.
    Ayrıca İspanyolca slug üretir.
    """
    print(f"   🌐 API çağrısı başlıyor: {en_title}")
    
    prompt = f"""You are a professional **content rewriter and cultural adaptation expert**, not a translator.

TASK: Rewrite the ENTIRE English article below in NATURAL, AUTHENTIC SPANISH (es-ES).

CRITICAL RULES:
- This is a REWRITE, not translation. Adapt all examples and cultural references for Spanish speakers.
- Preserve ALL HTML tags exactly as they are: <h1>, <h2>, <h3>, <p>, <ul>, <li>, <div>, etc.
- Keep the EXACT same HTML structure. Do NOT add or remove any tags.
- Only translate/rewrite the TEXT content inside the tags.
- Do NOT add any introductory phrases or explanations. Start directly with the first tag.
- The rewritten article must be complete and ready to use.

ORIGINAL ENGLISH HTML:
{en_html}

SPANISH REWRITE (start directly with <h1>):
"""
    
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.8,
            "maxOutputTokens": 8000,
            "topP": 0.95
        }
    }
    
    try:
        response = requests.post(GEMINI_URL, json=payload, timeout=180)
        res_data = response.json()
        
        if 'candidates' in res_data and len(res_data['candidates']) > 0:
            es_html = res_data['candidates'][0]['content']['parts'][0]['text']
            print(f"   ✅ API başarılı, yanıt uzunluğu: {len(es_html)} karakter")
            return es_html
        else:
            error_msg = res_data.get('error', {}).get('message', 'Bilinmeyen hata')
            print(f"   ❌ API hatası: {error_msg}")
            return None
    except Exception as e:
        print(f"   ❌ İstek hatası: {e}")
        return None

def translate_bot():
    """
    Son LOOKBACK_MINUTES dakika içinde değişen /en/ makalelerini /es/ altına çevirir.
    Sadece İspanyolca, tek API çağrısı, eski makaleler çevrilmez.
    """
    print(f"\n{'#'*60}")
    print(f"🔄 TRANSLATE BOT BAŞLATILIYOR")
    print(f"⏰ Başlangıç: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📋 Son {LOOKBACK_MINUTES} dakikada değişen İngilizce makaleler işlenecek")
    print(f"🎯 Hedef dil: İspanyolca (es)")
    print(f"{'#'*60}\n")
    
    # R2'den son 10 dakikada değişen İngilizce makaleleri bul
    prefix = "articles/en/"
    recent_articles = []
    
    try:
        response = s3.list_objects_v2(Bucket=R2_BUCKET, Prefix=prefix)
        if 'Contents' not in response:
            print("❌ Hiç makale bulunamadı.")
            return
    except Exception as e:
        print(f"⚠️ R2 listeleme hatası: {e}")
        return
    
    for obj in response['Contents']:
        key = obj['Key']
        if not key.endswith('.html') or key.endswith('index.html'):
            continue
        
        last_modified = obj['LastModified']
        if is_recent_file(last_modified):
            recent_articles.append({
                'key': key,
                'last_modified': last_modified
            })
            print(f"   ✅ Yeni makale: {key}")
        else:
            print(f"   ⏭️ Eski makale atlanıyor: {key}")
    
    if not recent_articles:
        print(f"\nℹ️ Son {LOOKBACK_MINUTES} dakikada yeni makale bulunamadı. Çeviri botu kapatılıyor.")
        return
    
    print(f"\n📋 Son {LOOKBACK_MINUTES} dakikada {len(recent_articles)} yeni makale bulundu.\n")
    
    translated_count = 0
    for article in recent_articles:
        en_key = article['key']
        print(f"\n{'='*60}")
        print(f"📖 İşleniyor: {en_key}")
        print(f"⏰ Son değişiklik: {article['last_modified']}")
        
        # İngilizce HTML'i oku
        try:
            file_obj = s3.get_object(Bucket=R2_BUCKET, Key=en_key)
            en_html = file_obj['Body'].read().decode('utf-8')
        except Exception as e:
            print(f"   ❌ Okuma hatası: {e}")
            continue
        
        # Başlığı bul (slug için)
        title_match = re.search(r'<h1>(.*?)</h1>', en_html, re.DOTALL)
        en_title = title_match.group(1).strip() if title_match else "article"
        
        # İspanyolca slug üret
        es_slug = create_spanish_slug(en_title)
        
        # Path bilgilerini çıkar
        # Örnek: articles/en/wellness/2026/04/33015fba-mindfulness.html
        rel_path = en_key.replace("articles/en/", "")
        parts = rel_path.split('/')
        if len(parts) >= 4:
            category = parts[0]
            yil = parts[1]
            ay = parts[2]
            filename = parts[3]
            # Eski dosya adından hash'i al
            if '-' in filename:
                hash_id = filename.split('-')[0]
            else:
                hash_id = filename.replace('.html', '')
        else:
            # Eski format (düz hash.html)
            parts = rel_path.split('/')
            if len(parts) >= 2:
                category = parts[0]
                yil = None
                ay = None
                hash_id = parts[1].replace('.html', '')
            else:
                print(f"   ❌ Path parse edilemedi: {rel_path}")
                continue
        
        # İspanyolca HTML'i yeniden yaz
        es_html = rewrite_article_to_spanish(en_html, en_title, es_slug)
        if not es_html:
            print(f"   ❌ Çeviri başarısız, atlanıyor.")
            continue
        
        # İspanyolca dosya yolunu oluştur
        if yil and ay:
            es_key = f"articles/es/{category}/{yil}/{ay}/{hash_id}-{es_slug}.html"
        else:
            es_key = f"articles/es/{category}/{hash_id}-{es_slug}.html"
        
        # R2'ye kaydet
        try:
            s3.put_object(
                Bucket=R2_BUCKET,
                Key=es_key,
                Body=es_html.encode('utf-8'),
                ContentType='text/html'
            )
            print(f"   ✅ Kaydedildi: {es_key}")
            translated_count += 1
        except Exception as e:
            print(f"   ❌ Kayıt hatası: {e}")
        
        # API kotası koruma
        print("   ⏳ 5 saniye bekleniyor...")
        time.sleep(5)
    
    print(f"\n{'#'*60}")
    print(f"🏁 TRANSLATE BOT TAMAMLANDI")
    print(f"📊 İstatistik: {translated_count} makale çevrildi, {len(recent_articles) - translated_count} başarısız")
    print(f"⏰ Bitiş: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'#'*60}\n")

if __name__ == "__main__":
    from datetime import timedelta
    translate_bot()
