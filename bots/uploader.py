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
    """content/ altındaki HTML'leri R2'ye yükler, sonra siler"""
    
    # Önce template'leri yedekle
    upload_templates()
    
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
            r2_key = local_path.replace("content/", "articles/")
            if upload_file_to_r2(local_path, r2_key):
                uploaded_files.append(local_path)
    
    for file_path in uploaded_files:
        try:
            os.remove(file_path)
            print(f"🗑️ Silindi: {file_path}")
        except Exception as e:
            print(f"⚠️ Silinemedi: {file_path} - {e}")
    
    print("\n🏁 Tüm içerik R2'ye yüklendi ve local HTML'ler temizlendi.")

if __name__ == "__main__":
    uploader()
