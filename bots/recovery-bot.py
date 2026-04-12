import os
import re
import boto3
from bs4 import BeautifulSoup
from botocore.client import Config

# ================= R2 BAĞLANTISI =================
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

def remove_all_images_from_html(html_content):
    """HTML içindeki tüm <img> etiketlerini siler"""
    soup = BeautifulSoup(html_content, 'html.parser')
    for img in soup.find_all('img'):
        img.decompose()
    return str(soup)

def clean_and_sync_from_r2():
    """
    1. R2'deki recovered-articles/ içindeki HTML'lerden img etiketlerini siler
    2. R2'deki articles/ içindeki tüm dosyaları siler
    3. Temizlenmiş HTML'leri recovered-articles/ -> articles/ kopyalar (R2 üzerinde)
    """
    
    source_prefix = "recovered-articles/"
    target_prefix = "articles/"
    
    print("\n" + "="*60)
    print("🔧 RECOVERY BOT - R2 SENKRONİZASYON")
    print("="*60)
    
    # 1. recovered-articles/ içindeki tüm HTML dosyalarını bul
    print(f"\n🔍 {source_prefix} taranıyor...")
    
    html_files = []
    continuation_token = None
    
    while True:
        if continuation_token:
            response = s3.list_objects_v2(
                Bucket=R2_BUCKET,
                Prefix=source_prefix,
                ContinuationToken=continuation_token
            )
        else:
            response = s3.list_objects_v2(
                Bucket=R2_BUCKET,
                Prefix=source_prefix
            )
        
        if 'Contents' in response:
            for obj in response['Contents']:
                key = obj['Key']
                if key.endswith('.html'):
                    html_files.append(key)
        
        if response.get('IsTruncated'):
            continuation_token = response.get('NextContinuationToken')
        else:
            break
    
    print(f"📊 {len(html_files)} HTML dosyası bulundu.\n")
    
    if not html_files:
        print("❌ Hiç HTML dosyası bulunamadı!")
        return
    
    # 2. Tüm img etiketlerini sil (R2'den oku, sil, geri yaz)
    print("📷 AŞAMA 1: img etiketleri siliniyor...")
    
    success_count = 0
    for key in html_files:
        print(f"📖 İşleniyor: {key}")
        try:
            # R2'den oku
            file_obj = s3.get_object(Bucket=R2_BUCKET, Key=key)
            html_content = file_obj['Body'].read().decode('utf-8')
            
            # img'leri temizle
            clean_html = remove_all_images_from_html(html_content)
            
            # R2'ye geri yaz (üzerine yaz)
            s3.put_object(
                Bucket=R2_BUCKET,
                Key=key,
                Body=clean_html.encode('utf-8'),
                ContentType='text/html'
            )
            print(f"   ✅ img etiketleri silindi")
            success_count += 1
        except Exception as e:
            print(f"   ❌ Hata: {e}")
    
    print(f"\n📊 Temizlik: {success_count}/{len(html_files)} başarılı")
    
    # 3. articles/ içindeki tüm dosyaları sil
    print("\n🗑️ AŞAMA 2: articles/ klasörü temizleniyor...")
    
    deleted_count = 0
    continuation_token = None
    
    while True:
        if continuation_token:
            response = s3.list_objects_v2(
                Bucket=R2_BUCKET,
                Prefix=target_prefix,
                ContinuationToken=continuation_token
            )
        else:
            response = s3.list_objects_v2(
                Bucket=R2_BUCKET,
                Prefix=target_prefix
            )
        
        if 'Contents' in response:
            for obj in response['Contents']:
                key = obj['Key']
                if key.endswith('.html'):
                    s3.delete_object(Bucket=R2_BUCKET, Key=key)
                    print(f"   🗑️ Silindi: {key}")
                    deleted_count += 1
        
        if response.get('IsTruncated'):
            continuation_token = response.get('NextContinuationToken')
        else:
            break
    
    print(f"✅ {deleted_count} dosya silindi")
    
    # 4. Temizlenmiş dosyaları recovered-articles/ -> articles/ kopyala
    print("\n📋 AŞAMA 3: recovered-articles/ -> articles/ kopyalanıyor...")
    
    copy_count = 0
    for src_key in html_files:
        # recovered-articles/en/.../file.html -> articles/en/.../file.html
        dst_key = src_key.replace(source_prefix, target_prefix, 1)
        
        try:
            # Kaynağı oku
            file_obj = s3.get_object(Bucket=R2_BUCKET, Key=src_key)
            html_content = file_obj['Body'].read()
            
            # Hedefe yaz
            s3.put_object(
                Bucket=R2_BUCKET,
                Key=dst_key,
                Body=html_content,
                ContentType='text/html'
            )
            print(f"   ✅ Kopyalandı: {src_key} -> {dst_key}")
            copy_count += 1
        except Exception as e:
            print(f"   ❌ Kopyalama hatası ({src_key}): {e}")
    
    print("\n" + "="*60)
    print("🏁 İŞLEM TAMAMLANDI")
    print(f"📷 Temizlenen dosyalar: {success_count}")
    print(f"🗑️ Silinen dosyalar (articles/): {deleted_count}")
    print(f"📋 Kopyalanan dosyalar: {copy_count}")
    print("="*60)

if __name__ == "__main__":
    clean_and_sync_from_r2()
