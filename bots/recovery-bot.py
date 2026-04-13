import os
import boto3
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

def copy_prefix_to_backup(source_prefix, backup_prefix):
    """Bir prefix'teki tüm dosyaları backup prefix'ine kopyala"""
    print(f"📦 Yedekleniyor: {source_prefix} -> {backup_prefix}")
    continuation_token = None
    copied_count = 0
    
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
        
        if 'Contents' not in response:
            break
            
        for obj in response['Contents']:
            src_key = obj['Key']
            # Hedef key: backup_prefix + göreceli yol
            rel_path = src_key.replace(source_prefix, '', 1)
            dst_key = f"{backup_prefix}{rel_path}"
            
            try:
                # Kaynağı oku
                copy_source = {'Bucket': R2_BUCKET, 'Key': src_key}
                s3.copy_object(
                    CopySource=copy_source,
                    Bucket=R2_BUCKET,
                    Key=dst_key
                )
                print(f"   ✅ Kopyalandı: {src_key} -> {dst_key}")
                copied_count += 1
            except Exception as e:
                print(f"   ❌ Kopyalama hatası ({src_key}): {e}")
        
        if response.get('IsTruncated'):
            continuation_token = response.get('NextContinuationToken')
        else:
            break
    
    print(f"   📊 Toplam {copied_count} dosya yedeklendi.")
    return copied_count

def delete_prefix_content(prefix, keep_folders=False):
    """Bir prefix'teki TÜM dosyaları sil (keep_folders=True ise sadece dosyaları sil, klasörleri tut)"""
    print(f"🗑️ Siliniyor: {prefix}")
    continuation_token = None
    deleted_count = 0
    
    while True:
        if continuation_token:
            response = s3.list_objects_v2(
                Bucket=R2_BUCKET,
                Prefix=prefix,
                ContinuationToken=continuation_token
            )
        else:
            response = s3.list_objects_v2(
                Bucket=R2_BUCKET,
                Prefix=prefix
            )
        
        if 'Contents' not in response:
            break
            
        for obj in response['Contents']:
            key = obj['Key']
            # Eğer sadece dosyaları silmek istiyorsak (klasörleri tutmak için)
            if keep_folders and key.endswith('/'):
                continue
            try:
                s3.delete_object(Bucket=R2_BUCKET, Key=key)
                print(f"   🗑️ Silindi: {key}")
                deleted_count += 1
            except Exception as e:
                print(f"   ❌ Silme hatası ({key}): {e}")
        
        if response.get('IsTruncated'):
            continuation_token = response.get('NextContinuationToken')
        else:
            break
    
    print(f"   📊 Toplam {deleted_count} dosya silindi.")
    return deleted_count

def create_empty_folder(folder_path):
    """R2'de boş bir klasör oluştur (sonuna / eklenmiş olmalı)"""
    try:
        s3.put_object(Bucket=R2_BUCKET, Key=folder_path, Body=b'')
        print(f"   ✅ Klasör oluşturuldu: {folder_path}")
    except Exception as e:
        print(f"   ❌ Klasör oluşturma hatası ({folder_path}): {e}")

def cleanup_and_setup():
    print("\n" + "="*60)
    print("🔧 TEMİZLİK VE YENİDEN YAPILANDIRMA BOTU")
    print("="*60)
    
    # 1. Mevcut articles/ ve images/ klasörlerini "ilk_demo/" altına yedekle
    print("\n📦 AŞAMA 1: Yedekleme (articles/ + images/ -> ilk_demo/)")
    copy_prefix_to_backup("articles/", "ilk_demo/articles/")
    copy_prefix_to_backup("images/", "ilk_demo/images/")
    
    # 2. articles/ içindeki TÜM dosyaları sil (klasör yapısı kalsın)
    print("\n🗑️ AŞAMA 2: articles/ içi temizleniyor (klasör yapısı kalacak)...")
    delete_prefix_content("articles/", keep_folders=True)
    
    # 3. images/ içindeki TÜM dosyaları sil (klasör yapısı kalsın)
    print("\n🗑️ AŞAMA 3: images/ içi temizleniyor (klasör yapısı kalacak)...")
    delete_prefix_content("images/", keep_folders=True)
    
    # 4. recovery/ klasörünü tamamen sil
    print("\n🗑️ AŞAMA 4: recovery/ klasörü tamamen siliniyor...")
    delete_prefix_content("recovery/", keep_folders=False)
    
    # 5. raw-articles/ klasörünü oluştur
    print("\n📁 AŞAMA 5: raw-articles/ klasörü oluşturuluyor...")
    create_empty_folder("raw-articles/")
    
    # 6. recovered-articles/ içindeki dosyaları raw-articles/ altına taşı (kopyala)
    print("\n📋 AŞAMA 6: recovered-articles/ -> raw-articles/ kopyalanıyor...")
    copy_prefix_to_backup("recovered-articles/", "raw-articles/")
    
    print("\n" + "="*60)
    print("🏁 İŞLEM TAMAMLANDI")
    print("📁 Yedekler: ilk_demo/articles/ ve ilk_demo/images/")
    print("📁 Yeni ham kaynak: raw-articles/")
    print("📁 Eski recovered-articles/ hala duruyor (istersen sonra sil)")
    print("="*60)

if __name__ == "__main__":
    cleanup_and_setup()
