import os
import re
import boto3
import requests
from datetime import datetime
from botocore.client import Config
from bs4 import BeautifulSoup

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

def clean_article(html_content):
    """
    Bozuk HTML'den sadece temiz içeriği ayıklar.
    - Başlık (<h1>)
    - Editor's Note (<div class="editors-note">)
    - İçerik (<div class="article-content">)
    - Kaynaklar (<div class="sources">)
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Başlık
    title_tag = soup.find('h1')
    title = str(title_tag) if title_tag else ""
    
    # Editor's Note
    editors_note_tag = soup.find('div', class_='editors-note')
    editors_note = str(editors_note_tag) if editors_note_tag else ""
    
    # İçerik (asıl makale metni)
    content_tag = soup.find('div', class_='article-content')
    content = str(content_tag) if content_tag else ""
    
    # Kaynaklar
    sources_tag = soup.find('div', class_='sources')
    sources = str(sources_tag) if sources_tag else ""
    
    # Ham HTML'i oluştur
    clean_html = f"""{title}

{editors_note}

{content}

{sources}
"""
    return clean_html

def get_all_articles_from_r2():
    """R2'deki tüm makalelerin listesini alır"""
    all_articles = []
    languages = ['en', 'es', 'de', 'fr']
    
    for lang in languages:
        prefix = f"articles/{lang}/"
        try:
            response = s3.list_objects_v2(Bucket=R2_BUCKET, Prefix=prefix)
            if 'Contents' not in response:
                continue
        except Exception as e:
            print(f"⚠️ R2 listeleme hatası ({lang}): {e}")
            continue
        
        for obj in response['Contents']:
            key = obj['Key']
            if not key.endswith('.html') or key.endswith('index.html'):
                continue
            all_articles.append({
                'key': key,
                'lang': lang,
                'last_modified': obj['LastModified']
            })
    
    return all_articles

def recovery_bot():
    print("\n" + "="*60)
    print("🔧 RECOVERY BOT BAŞLATILIYOR")
    print("📋 Görev: R2'deki bozuk makaleleri temizle, recovered/ klasörüne kaydet")
    print("⚠️ NOT: R2'den dosya silinmez, sadece okunur ve yeni klasöre yazılır.")
    print("="*60 + "\n")
    
    # R2'deki tüm makaleleri bul
    print("🔍 R2 taranıyor...")
    all_articles = get_all_articles_from_r2()
    print(f"📊 Toplam {len(all_articles)} makale bulundu.\n")
    
    if not all_articles:
        print("❌ Hiç makale bulunamadı!")
        return
    
    # Local recovery klasörünü oluştur
    recovery_dir = "recovered"
    os.makedirs(recovery_dir, exist_ok=True)
    
    success_count = 0
    fail_count = 0
    
    for article in all_articles:
        key = article['key']
        print(f"📖 İşleniyor: {key}")
        
        try:
            # R2'den dosyayı oku
            file_obj = s3.get_object(Bucket=R2_BUCKET, Key=key)
            html_content = file_obj['Body'].read().decode('utf-8')
            
            # Temizle
            clean_html = clean_article(html_content)
            
            # Local'e kaydet (aynı klasör yapısıyla)
            # key: articles/en/wellness/2026/04/hash-slug.html
            # local: recovered/en/wellness/2026/04/hash-slug.html
            local_path = key.replace('articles/', 'recovered/')
            local_dir = os.path.dirname(local_path)
            os.makedirs(local_dir, exist_ok=True)
            
            with open(local_path, 'w', encoding='utf-8') as f:
                f.write(clean_html)
            
            print(f"   ✅ Kaydedildi: {local_path}")
            success_count += 1
            
        except Exception as e:
            print(f"   ❌ Hata: {e}")
            fail_count += 1
    
    print("\n" + "="*60)
    print(f"🏁 RECOVERY BOT TAMAMLANDI")
    print(f"📊 Başarılı: {success_count}, Başarısız: {fail_count}")
    print(f"📁 Temizlenmiş dosyalar 'recovered/' klasöründe")
    print("="*60 + "\n")

if __name__ == "__main__":
    recovery_bot()
