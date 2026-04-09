import os
import re
import json
import time
import boto3
from datetime import datetime
from botocore.client import Config

# R2 Secrets (eski projeden aynen kullan)
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

def markdown_oku_ve_guncelle(md_path, hash_id, kategori):
    """Markdown dosyasını okur, görsel linklerini R2 ile değiştirir, kaydeder"""
    
    with open(md_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Görsel dosyalarını kontrol et ve R2'ye yükle
    for img_type in ['kapak', 'icerik_1', 'icerik_2']:
        local_path = f"assets/{hash_id}_{img_type}.png"
        if os.path.exists(local_path):
            # R2'ye yükle
            r2_key = f"{hash_id}_{img_type}.png"
            print(f"🚀 {img_type} R2'ye yükleniyor: {r2_key}")
            s3.upload_file(local_path, R2_BUCKET, r2_key)
            r2_url = f"{R2_PUBLIC_URL}/{r2_key}"
            
            # Markdown içindeki local linki R2 linki ile değiştir
            content = content.replace(f'./assets/{hash_id}_{img_type}.png', r2_url)
            content = content.replace(f'assets/{hash_id}_{img_type}.png', r2_url)
            print(f"✅ {img_type} linki güncellendi: {r2_url}")
    
    # Güncellenmiş Markdown'u kaydet
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✅ Markdown güncellendi: {md_path}")

def uploader():
    """content/en/ altındaki tüm .md dosyalarını tarar, görselleri R2'ye yükler"""
    
    en_base = "content/en"
    
    if not os.path.exists(en_base):
        print(f"❌ {en_base} klasörü bulunamadı!")
        return
    
    for root, dirs, files in os.walk(en_base):
        for file in files:
            if file.endswith('.md'):
                md_path = os.path.join(root, file)
                hash_id = file.replace('.md', '')  # Dosya adı hash
                
                print(f"\n📖 İşleniyor: {md_path} (Hash: {hash_id})")
                
                # Kategoriyi yoldan al (content/en/{kategori}/hash.md)
                kategori = os.path.basename(root)
                
                markdown_oku_ve_guncelle(md_path, hash_id, kategori)
                
                # Kısa bekle (R2 rate limit için)
                time.sleep(1)
    
    print("\n🏁 Tüm Markdown dosyaları işlendi, görseller R2'ye yüklendi.")

if __name__ == "__main__":
    uploader()
