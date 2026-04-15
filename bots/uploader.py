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

def upload_file_to_r2(local_path, r2_key, content_type=None):
    if os.path.exists(local_path):
        print(f"🚀 Yükleniyor: {local_path} -> {r2_key}")
        extra_args = {}
        if content_type:
            extra_args['ContentType'] = content_type
        s3.upload_file(local_path, R2_BUCKET, r2_key, ExtraArgs=extra_args)
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
        print(f"⚠️ {templates_dir} klasörü yok, atlanıyor.")
        return
    
    for file in os.listdir(templates_dir):
        local_path = os.path.join(templates_dir, file)
        if os.path.isfile(local_path):
            r2_key = f"templates/{file}"
            upload_file_to_r2(local_path, r2_key)

def upload_hero_json():
    """Github ana dizininden hero.json'u alıp R2 templates/ klasörüne yükler"""
    local_path = "hero.json"
    r2_key = "templates/hero.json"
    
    if os.path.exists(local_path):
        print(f"\n🎨 Hero JSON yükleniyor...")
        return upload_file_to_r2(local_path, r2_key, content_type='application/json')
    else:
        print(f"\n⚠️ hero.json dosyası ana dizinde bulunamadı, atlanıyor.")
        return False

def uploader():
    """content/ altındaki HTML'leri R2'ye (raw-articles/) yükler, sonra siler"""
    
    # 1. Önce template'leri yedekle
    print("\n📁 TEMPLATE YEDEKLEME")
    print("-" * 40)
    upload_templates()
    
    # 2. Hero JSON'u yedekle (templates/ klasörüne)
    upload_hero_json()
    
    # 3. articles/ içini tamamen temizle
    print("\n📁 ARTICLES TEMİZLİĞİ")
    print("-" * 40)
    delete_all_articles()
    
    # 4. content/ altındaki ham HTML'leri raw-articles/ altına yükle
    content_base = "content"
    if not os.path.exists(content_base):
        print(f"❌ {content_base} klasörü yok!")
        return
    
    print("\n📁 İÇERİK YÜKLEME")
    print("-" * 40)
    
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
    
    # 5. Local dosyaları temizle
    print("\n🗑️ LOCAL TEMİZLİK")
    print("-" * 40)
    for file_path in uploaded_files:
        try:
            os.remove(file_path)
            print(f"   🗑️ Silindi: {file_path}")
        except Exception as e:
            print(f"   ⚠️ Silinemedi: {file_path} - {e}")
    
    # 6. Boş klasörleri temizle (opsiyonel)
    for root, dirs, files in os.walk(content_base, topdown=False):
        for dir_name in dirs:
            dir_path = os.path.join(root, dir_name)
            try:
                if not os.listdir(dir_path):
                    os.rmdir(dir_path)
                    print(f"   🗑️ Boş klasör silindi: {dir_path}")
            except:
                pass
    
    print("\n" + "=" * 60)
    print("🏁 UPLOADER TAMAMLANDI!")
    print("   ✅ Template'ler → R2/templates/")
    print("   ✅ hero.json → R2/templates/hero.json")
    print("   ✅ articles/ klasörü temizlendi")
    print("   ✅ content/ → R2/raw-articles/")
    print("   ✅ Local HTML'ler temizlendi")
    print("=" * 60)

if __name__ == "__main__":
    uploader()
