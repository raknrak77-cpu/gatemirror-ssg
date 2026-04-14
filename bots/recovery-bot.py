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

def download_folder_to_github(prefix, local_backup_dir):
    """R2'deki bir klasörün içindeki tüm dosyaları local'e indir (GitHub'a commit için)"""
    import os
    os.makedirs(local_backup_dir, exist_ok=True)
    
    continuation_token = None
    downloaded_count = 0
    
    while True:
        if continuation_token:
            response = s3.list_objects_v2(Bucket=R2_BUCKET, Prefix=prefix, ContinuationToken=continuation_token)
        else:
            response = s3.list_objects_v2(Bucket=R2_BUCKET, Prefix=prefix)
        
        if 'Contents' not in response:
            break
        
        for obj in response['Contents']:
            key = obj['Key']
            # local path: backup/ilk-demo/articles/en/...
            local_path = os.path.join(local_backup_dir, key)
            local_dir = os.path.dirname(local_path)
            os.makedirs(local_dir, exist_ok=True)
            
            try:
                file_obj = s3.get_object(Bucket=R2_BUCKET, Key=key)
                with open(local_path, 'wb') as f:
                    f.write(file_obj['Body'].read())
                print(f"   📥 İndirildi: {key} → {local_path}")
                downloaded_count += 1
            except Exception as e:
                print(f"   ❌ İndirme hatası ({key}): {e}")
        
        if response.get('IsTruncated'):
            continuation_token = response.get('NextContinuationToken')
        else:
            break
    
    print(f"   ✅ Toplam {downloaded_count} dosya indirildi.")
    return downloaded_count

def delete_prefix(prefix):
    """R2'deki bir prefix'i tamamen sil (içindeki tüm dosyalar)"""
    continuation_token = None
    deleted_count = 0
    
    while True:
        if continuation_token:
            response = s3.list_objects_v2(Bucket=R2_BUCKET, Prefix=prefix, ContinuationToken=continuation_token)
        else:
            response = s3.list_objects_v2(Bucket=R2_BUCKET, Prefix=prefix)
        
        if 'Contents' not in response:
            break
        
        for obj in response['Contents']:
            key = obj['Key']
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
    
    print(f"   ✅ Toplam {deleted_count} dosya silindi.")
    return deleted_count

def cleanup_r2():
    print("\n" + "="*60)
    print("🧹 R2 TEMİZLİK BOTU")
    print("   Yedekle + Sil işlemleri")
    print("="*60)
    
    # ================= AŞAMA 1-2: YEDEKLE =================
    print("\n📦 AŞAMA 1-2: Yedekleme (ilk-demo + recovered-articles)")
    print("   📥 Dosyalar 'backup/' klasörüne indiriliyor...")
    
    download_folder_to_github("ilk-demo/", "backup/ilk-demo")
    download_folder_to_github("recovered-articles/", "backup/recovered-articles")
    
    # ================= AŞAMA 3: YEDEKLENEN KLASÖRLERİ SİL =================
    print("\n🗑️ AŞAMA 3: Yedeklenen klasörler R2'den siliniyor...")
    delete_prefix("ilk-demo/")
    delete_prefix("recovered-articles/")
    
    # ================= AŞAMA 4-7: DİĞER KARIŞIK KLASÖRLERİ SİL =================
    print("\n🗑️ AŞAMA 4-7: Karışık klasörler siliniyor...")
    
    to_delete = [
        "de/",
        "es/",
        "fr/",
        "explore/"
    ]
    
    for prefix in to_delete:
        print(f"\n   📁 Siliniyor: {prefix}")
        delete_prefix(prefix)
    
    print("\n" + "="*60)
    print("🏁 TEMİZLİK TAMAMLANDI")
    print("   ✅ Yedekler: backup/ilk-demo, backup/recovered-articles")
    print("   ✅ Silinenler: ilk-demo, recovered-articles, de, es, fr, explore")
    print("="*60)
    print("\n💡 NOT: backup/ klasörünü GitHub'a commit etmeyi unutma!")

if __name__ == "__main__":
    cleanup_r2()
