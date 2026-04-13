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

def upload_file_to_r2(local_path, r2_key):
    if os.path.exists(local_path):
        print(f"🚀 Yükleniyor: {local_path} -> {r2_key}")
        s3.upload_file(local_path, R2_BUCKET, r2_key)
        print(f"✅ Yüklendi: {r2_key}")
        return True
    return False

def delete_all_articles():
    """articles/ klasöründeki TÜM dosyaları sil (Publisher temiz başlasın)"""
    print("\n🗑️ articles/ içindeki tüm dosyalar siliniyor...")
    continuation_token = None
    deleted_count = 0
    while True:
        if continuation_token:
            response = s3.list_objects_v2(
                Bucket=R2_BUCKET,
                Prefix='articles/',
                ContinuationToken=continuation_token
            )
        else:
            response = s3.list_objects_v2(Bucket=R2_BUCKET, Prefix='articles/')
        
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
    
    print(f"   ✅ Toplam {deleted_count} dosya silindi.\n")

def upload_templates():
    """templates/ klasöründeki dosyaları R2'ye yedekler"""
    templates_dir = "templates"
    if not os.path.exists(templates_dir):
        return
    
    for file in os.listdir(templates_dir):
        if file.endswith('.html'):
            local_path = os.path.join(templates_dir, file)
            r2_key = f"templates/{file}"
            upload_file_to_r2(local_path, r2_key)

def uploader():
    """content/ altındaki HTML'leri R2'ye (raw-articles/) yükler, sonra siler"""
    
    # 1. Önce template'leri yedekle
    upload_templates()
    
    # 2. articles/ içini tamamen temizle
    delete_all_articles()
    
    # 3. content/ altındaki ham HTML'leri raw-articles/ altına yükle
    content_base = "content"
    if not os.path.exists(content_base):
        print(f"❌ {content_base} klasörü yok!")
        return
    
    uploaded_files = []
    
    for root, dirs, files in os.walk(content_base):
        for file in files:
            if not file.endswith('.html'):
                continue
            
            local_path = os.path.join(root, file)
            # content/en/wellness/hash.html → raw-articles/en/wellness/hash.html
            r2_key = local_path.replace("content/", "raw-articles/")
            if upload_file_to_r2(local_path, r2_key):
                uploaded_files.append(local_path)
    
    # 4. Local dosyaları temizle
    for file_path in uploaded_files:
        try:
            os.remove(file_path)
            print(f"🗑️ Silindi: {file_path}")
        except Exception as e:
            print(f"⚠️ Silinemedi: {file_path} - {e}")
    
    print("\n🏁 Tüm içerik R2'ye yüklendi (raw-articles/) ve local HTML'ler temizlendi.")
    print("📁 articles/ klasörü temizlendi, Publisher sıfırdan yazacak.")

if __name__ == "__main__":
    uploader()
