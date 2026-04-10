import os
import time
import boto3
from botocore.client import Config
from PIL import Image

# R2 Secrets
R2_ID = os.getenv('R2_ACCOUNT_ID')
R2_ACCESS_KEY = os.getenv('R2_ACCESS_KEY_ID')
R2_SECRET_KEY = os.getenv('R2_SECRET_ACCESS_KEY')
R2_BUCKET = os.getenv('R2_BUCKET_NAME')
R2_PUBLIC_URL = os.getenv('R2_PUBLIC_URL').rstrip('/')

# R2 Bağlantı
s3 = boto3.client(
    's3',
    endpoint_url=f'https://{R2_ID}.r2.cloudflarestorage.com',
    aws_access_key_id=R2_ACCESS_KEY,
    aws_secret_access_key=R2_SECRET_KEY,
    config=Config(signature_version='s3v4'),
    region_name='auto'
)

def convert_to_webp(input_path, output_path):
    """PNG/JPEG dosyasını WebP'ye dönüştürür"""
    try:
        with Image.open(input_path) as img:
            if img.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = background
            img.save(output_path, 'WEBP', quality=85)
        return True
    except Exception as e:
        print(f"⚠️ WebP dönüşüm hatası: {e}")
        return False

def upload_file_to_r2(local_path, r2_key):
    """Dosyayı R2'ye yükler"""
    if os.path.exists(local_path):
        print(f"🚀 Yükleniyor: {local_path} -> {r2_key}")
        s3.upload_file(local_path, R2_BUCKET, r2_key)
        print(f"✅ Yüklendi: {r2_key}")
        return True
    else:
        print(f"⚠️ Dosya yok: {local_path}")
        return False

def upload_images():
    """assets/ altındaki görselleri WebP'ye dönüştürüp R2'ye yükler"""
    
    assets_dir = "assets"
    if not os.path.exists(assets_dir):
        print(f"⚠️ {assets_dir} klasörü yok, görsel yükleme atlanıyor.")
        return
    
    for file in os.listdir(assets_dir):
        if file.endswith('.png'):
            # Dosya adından hash ve tipi çıkar (örn: 6af03d83_kapak.png)
            parts = file.replace('.png', '').split('_')
            if len(parts) == 2:
                hash_id, img_type = parts
            else:
                print(f"⚠️ {file} adı hatalı, atlanıyor.")
                continue
            
            # Kategori? Görselin kategorisini nereden alacağız?
            # Şimdilik 'general' kullan, ileride düzenlenebilir
            kategori = "general"
            
            local_path = os.path.join(assets_dir, file)
            webp_path = os.path.join(assets_dir, f"{hash_id}_{img_type}.webp")
            
            # WebP'ye dönüştür
            if convert_to_webp(local_path, webp_path):
                # R2'ye yükle
                r2_key = f"images/{kategori}/{hash_id}_{img_type}.webp"
                upload_file_to_r2(webp_path, r2_key)
                os.remove(webp_path)
            else:
                # Dönüşüm başarısızsa orijinal PNG'yi yükle
                r2_key = f"images/{kategori}/{hash_id}_{img_type}.png"
                upload_file_to_r2(local_path, r2_key)

def upload_articles():
    """public/ altındaki tüm HTML dosyalarını R2'ye yükler"""
    
    public_base = "public"
    if not os.path.exists(public_base):
        print(f"⚠️ {public_base} klasörü yok, makale yükleme atlanıyor.")
        return
    
    for root, dirs, files in os.walk(public_base):
        for file in files:
            if file.endswith('.html'):
                local_path = os.path.join(root, file)
                # R2'de articles/ altında aynı klasör yapısını koru
                r2_key = local_path.replace("public/", "articles/")
                upload_file_to_r2(local_path, r2_key)

def uploader():
    """Tüm içeriği R2'ye yükler: görseller (WebP) + HTML makaleler"""
    
    print("🖼️ Görseller yükleniyor (WebP dönüşümü)...")
    upload_images()
    
    print("\n📄 Makaleler yükleniyor (HTML)...")
    upload_articles()
    
    print("\n🏁 Tüm içerik R2'ye yüklendi.")

if __name__ == "__main__":
    uploader()
