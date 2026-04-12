import os
import re
import boto3
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

# ================= YARDIMCI FONKSİYONLAR =================
def download_all_articles():
    """R2'deki tüm makale HTML'lerini local 'recovery/' klasörüne indirir."""
    base_dir = "recovery"
    os.makedirs(base_dir, exist_ok=True)
    
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
            
            local_path = os.path.join(base_dir, key)
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            
            try:
                file_obj = s3.get_object(Bucket=R2_BUCKET, Key=key)
                with open(local_path, 'wb') as f:
                    f.write(file_obj['Body'].read())
                print(f"✅ İndirildi: {key} -> {local_path}")
            except Exception as e:
                print(f"❌ İndirme hatası {key}: {e}")

def extract_clean_html(html_content):
    """
    Bozuk HTML'den sadece ham içeriği ayıklar.
    Dönen içerik şu parçalardan oluşur:
    - <h1>Başlık</h1>
    - <div class="editors-note">...</div> (varsa)
    - <div class="article-content">...</div>
    - <div class="sources">...</div> (varsa)
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Başlık
    title_tag = soup.find('h1')
    title_html = str(title_tag) if title_tag else ""
    
    # Editor's note
    editors_note = soup.find('div', class_='editors-note')
    editors_html = str(editors_note) if editors_note else ""
    
    # Ana içerik (article-content)
    article_content = soup.find('div', class_='article-content')
    if article_content:
        # İçerikteki gereksiz img'lerin src'lerini temizleme (ama görseller korunsun)
        content_html = str(article_content)
    else:
        content_html = ""
    
    # Kaynaklar
    sources = soup.find('div', class_='sources')
    sources_html = str(sources) if sources else ""
    
    # Birleştir
    clean_html = f"{title_html}\n{editors_html}\n{content_html}\n{sources_html}".strip()
    return clean_html

def clean_all_recovered():
    """recovery/ klasöründeki tüm HTML'leri oku, temizle, recovered_clean/ klasörüne yaz."""
    recovery_dir = "recovery"
    clean_dir = "recovered_clean"
    
    if not os.path.exists(recovery_dir):
        print("❌ recovery/ klasörü bulunamadı. Önce download işlemini çalıştır.")
        return
    
    for root, dirs, files in os.walk(recovery_dir):
        for file in files:
            if not file.endswith('.html'):
                continue
            src_path = os.path.join(root, file)
            rel_path = os.path.relpath(src_path, recovery_dir)
            dst_path = os.path.join(clean_dir, rel_path)
            os.makedirs(os.path.dirname(dst_path), exist_ok=True)
            
            try:
                with open(src_path, 'r', encoding='utf-8') as f:
                    html = f.read()
                clean_html = extract_clean_html(html)
                with open(dst_path, 'w', encoding='utf-8') as f:
                    f.write(clean_html)
                print(f"✅ Temizlendi: {rel_path}")
            except Exception as e:
                print(f"❌ Temizleme hatası {rel_path}: {e}")

def upload_clean_to_r2():
    """recovered_clean/ klasöründeki temiz HTML'leri R2'ye articles/ klasörüne yükler."""
    clean_dir = "recovered_clean"
    if not os.path.exists(clean_dir):
        print("❌ recovered_clean/ klasörü bulunamadı.")
        return
    
    for root, dirs, files in os.walk(clean_dir):
        for file in files:
            if not file.endswith('.html'):
                continue
            local_path = os.path.join(root, file)
            # relative path: recovered_clean/articles/en/tech/2026/04/hash.html
            r2_key = local_path.replace(clean_dir + os.sep, "")
            try:
                with open(local_path, 'rb') as f:
                    s3.put_object(Bucket=R2_BUCKET, Key=r2_key, Body=f.read(), ContentType='text/html')
                print(f"✅ Yüklendi: {r2_key}")
            except Exception as e:
                print(f"❌ Yükleme hatası {r2_key}: {e}")

def recovery_bot():
    print("🚀 Recovery Bot başlatılıyor...")
    print("📥 1. Adım: R2'deki tüm makaleler 'recovery/' klasörüne indiriliyor...")
    download_all_articles()
    print("\n🧹 2. Adım: İndirilen dosyalar temizleniyor (sadece ham içerik bırakılıyor)...")
    clean_all_recovered()
    print("\n📤 3. Adım: Temizlenmiş dosyalar 'recovered_clean/' klasörüne kaydedildi.")
    print("🔁 NOT: R2'ye otomatik yükleme YAPILMADI. İstersen manuel yükle veya upload_clean_to_r2() çağır.")
    print("🏁 Recovery Bot tamamlandı.")

if __name__ == "__main__":
    recovery_bot()
