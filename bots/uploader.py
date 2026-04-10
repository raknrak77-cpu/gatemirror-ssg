import os
import re
import json
import time
import boto3
from datetime import datetime
from botocore.client import Config
from PIL import Image  # WebP dönüşümü için

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
            # RGB'a çevir (şeffaflık varsa beyaz arka plan)
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
        return f"{R2_PUBLIC_URL}/{r2_key}"
    else:
        print(f"⚠️ Dosya yok: {local_path}")
        return None

def process_image(local_path, hash_id, img_type, kategori):
    """Görseli WebP'ye dönüştürüp R2'ye yükler, R2 linkini döndürür"""
    
    # WebP dosya adı (kategori bazlı)
    webp_filename = f"{hash_id}_{img_type}.webp"
    r2_key = f"images/{kategori}/{webp_filename}"
    webp_path = f"assets/{webp_filename}"
    
    # Dönüştür ve yükle
    if convert_to_webp(local_path, webp_path):
        r2_url = upload_file_to_r2(webp_path, r2_key)
        os.remove(webp_path)  # Geçici WebP dosyasını sil
        return r2_url
    else:
        # Dönüşüm başarısızsa orijinal PNG'yi yükle
        r2_key = f"images/{kategori}/{hash_id}_{img_type}.png"
        return upload_file_to_r2(local_path, r2_key)

def markdown_oku_ve_guncelle(md_path, hash_id, kategori):
    """Markdown dosyasını okur, görsel linklerini R2 WebP linki ile değiştirir"""
    
    with open(md_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Görsel dosyalarını kontrol et ve R2'ye yükle (WebP olarak)
    for img_type in ['kapak', 'icerik_1', 'icerik_2']:
        local_path = f"assets/{hash_id}_{img_type}.png"
        if os.path.exists(local_path):
            r2_url = process_image(local_path, hash_id, img_type, kategori)
            if r2_url:
                # Markdown içindeki local linki R2 linki ile değiştir
                content = content.replace(f'./assets/{hash_id}_{img_type}.png', r2_url)
                content = content.replace(f'assets/{hash_id}_{img_type}.png', r2_url)
                content = content.replace(f'{hash_id}_{img_type}.png', r2_url)
                print(f"✅ {img_type} linki güncellendi: {r2_url}")
    
    # Güncellenmiş Markdown'u kaydet
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✅ Markdown güncellendi: {md_path}")

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
    
    print("🖼️ Görseller işleniyor (WebP dönüşümü ve yükleme)...")
    
    en_base = "content/en"
    if os.path.exists(en_base):
        for root, dirs, files in os.walk(en_base):
            for file in files:
                if file.endswith('.md'):
                    md_path = os.path.join(root, file)
                    hash_id = file.replace('.md', '')
                    kategori = os.path.basename(root)
                    print(f"\n📖 İşleniyor: {md_path} (Hash: {hash_id}, Kategori: {kategori})")
                    markdown_oku_ve_guncelle(md_path, hash_id, kategori)
                    time.sleep(1)
    else:
        print(f"⚠️ {en_base} klasörü yok, görsel işleme atlanıyor.")
    
    print("\n📄 Makaleler yükleniyor (HTML)...")
    upload_articles()
    
    print("\n🏁 Tüm içerik R2'ye yüklendi (görseller WebP, makaleler HTML).")

if __name__ == "__main__":
    uploader()
