import os
import boto3
from botocore.client import Config

# R2 Secrets
R2_ID = os.getenv('R2_ACCOUNT_ID')
R2_ACCESS_KEY = os.getenv('R2_ACCESS_KEY_ID')
R2_SECRET_KEY = os.getenv('R2_SECRET_ACCESS_KEY')
R2_BUCKET = os.getenv('R2_BUCKET_NAME')
R2_PUBLIC_URL = os.getenv('R2_PUBLIC_URL').rstrip('/')

s3 = boto3.client(
    's3',
    endpoint_url=f'https://{R2_ID}.r2.cloudflarestorage.com',
    aws_access_key_id=R2_ACCESS_KEY,
    aws_secret_access_key=R2_SECRET_KEY,
    config=Config(signature_version='s3v4'),
    region_name='auto'
)

def upload_string_as_file(content, r2_key):
    """String içeriği doğrudan R2'ye dosya olarak yükler"""
    try:
        s3.put_object(Bucket=R2_BUCKET, Key=r2_key, Body=content.encode('utf-8'), ContentType='text/plain')
        print(f"✅ {r2_key} oluşturuldu")
        return True
    except Exception as e:
        print(f"❌ {r2_key} oluşturulamadı: {e}")
        return False

def upload_local_file(local_path, r2_key):
    """Yerel dosyayı R2'ye yükler"""
    if os.path.exists(local_path):
        try:
            s3.upload_file(local_path, R2_BUCKET, r2_key)
            print(f"✅ {r2_key} yüklendi")
            return True
        except Exception as e:
            print(f"❌ {r2_key} yüklenemedi: {e}")
            return False
    else:
        print(f"⚠️ {local_path} bulunamadı")
        return False

def create_folder_structure():
    """R2'de klasör yapısını oluştur (info.txt ile)"""
    
    # Klasör yapısı (her klasöre bir info.txt)
    folders = [
        "articles/en/wellness",
        "articles/en/tech",
        "articles/en/future-economy",
        "articles/en/eco",
        "articles/en/elearning",
        "articles/es/wellness",
        "articles/es/tech",
        "articles/es/future-economy",
        "articles/es/eco",
        "articles/es/elearning",
        "articles/de/wellness",
        "articles/de/tech",
        "articles/de/future-economy",
        "articles/de/eco",
        "articles/de/elearning",
        "articles/fr/wellness",
        "articles/fr/tech",
        "articles/fr/future-economy",
        "articles/fr/eco",
        "articles/fr/elearning",
        "images/wellness",
        "images/tech",
        "images/future-economy",
        "images/eco",
        "images/elearning"
    ]
    
    info_content = "This directory was created by Gatemirror SSG system."
    
    for folder in folders:
        r2_key = f"{folder}/info.txt"
        upload_string_as_file(info_content, r2_key)
    
    print("\n📁 Klasör yapısı oluşturuldu.")

def upload_static_pages():
    """Statik sayfaları yükler (sadece bir kere)"""
    
    static_files = [
        ("public/about-us.html", "articles/about-us.html"),
        ("public/contact.html", "articles/contact.html"),
        ("public/privacy-policy.html", "articles/privacy-policy.html"),
        ("public/index.html", "articles/index.html")  # Ana yönlendirme
    ]
    
    print("\n📄 Statik sayfalar yükleniyor...")
    for local, remote in static_files:
        upload_local_file(local, remote)

def create_root_index():
    """Kök dizine yönlendirme dosyası oluşturur"""
    redirect_html = """<!DOCTYPE html>
<html>
<head>
    <meta http-equiv="refresh" content="0; url=/articles/en/">
    <title>Gatemirror</title>
</head>
<body>
    <a href="/articles/en/">Gatemirror</a>
</body>
</html>
"""
    upload_string_as_file(redirect_html, "index.html")
    print("✅ Kök yönlendirme oluşturuldu (index.html)")

def bootstrap():
    """Ana fonksiyon"""
    print("🚀 R2 Bootstrap başlatılıyor...")
    print("=" * 50)
    
    create_folder_structure()
    upload_static_pages()
    create_root_index()
    
    print("\n" + "=" * 50)
    print(f"🎉 R2 hazır! Bucket: {R2_BUCKET}")
    print(f"🔗 Public URL: {R2_PUBLIC_URL}")

if __name__ == "__main__":
    bootstrap()
