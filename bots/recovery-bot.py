import os
import boto3
from botocore.client import Config

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

def move_object(old_key, new_key):
    """R2'de bir objeyi taşı (kopyala + sil)"""
    try:
        copy_source = {'Bucket': R2_BUCKET, 'Key': old_key}
        s3.copy_object(CopySource=copy_source, Bucket=R2_BUCKET, Key=new_key)
        s3.delete_object(Bucket=R2_BUCKET, Key=old_key)
        print(f"   ✅ Taşındı: {old_key} → {new_key}")
        return True
    except Exception as e:
        print(f"   ❌ Hata: {old_key} → {new_key} - {e}")
        return False

def delete_old_folders():
    """Eski klasörleri temizle"""
    prefixes = ['category-archive/', 'all-articles.html', 'categories.html']
    for prefix in prefixes:
        if prefix.endswith('/'):
            # Klasör silme (içindeki tüm dosyaları)
            continuation_token = None
            while True:
                if continuation_token:
                    response = s3.list_objects_v2(Bucket=R2_BUCKET, Prefix=prefix, ContinuationToken=continuation_token)
                else:
                    response = s3.list_objects_v2(Bucket=R2_BUCKET, Prefix=prefix)
                if 'Contents' not in response:
                    break
                for obj in response['Contents']:
                    s3.delete_object(Bucket=R2_BUCKET, Key=obj['Key'])
                    print(f"   🗑️ Silindi: {obj['Key']}")
                if response.get('IsTruncated'):
                    continuation_token = response.get('NextContinuationToken')
                else:
                    break
        else:
            # Tekil dosya
            try:
                s3.delete_object(Bucket=R2_BUCKET, Key=prefix)
                print(f"   🗑️ Silindi: {prefix}")
            except:
                pass

def migrate_explore():
    print("\n" + "="*60)
    print("📁 EXPLORE MIGRATION BOT")
    print("   category-archive/ → explore/category/")
    print("   all-articles.html → explore/all.html")
    print("   categories.html → explore/categories.html")
    print("="*60)

    # 1. category-archive/ altındaki tüm dosyaları explore/category/ taşı
    print("\n📦 AŞAMA 1: category-archive/ taşınıyor...")
    prefixes = ['category-archive/', 'de/category-archive/', 'es/category-archive/', 'fr/category-archive/']
    
    for prefix in prefixes:
        continuation_token = None
        while True:
            if continuation_token:
                response = s3.list_objects_v2(Bucket=R2_BUCKET, Prefix=prefix, ContinuationToken=continuation_token)
            else:
                response = s3.list_objects_v2(Bucket=R2_BUCKET, Prefix=prefix)
            if 'Contents' not in response:
                break
            for obj in response['Contents']:
                old_key = obj['Key']
                # category-archive/tech/index.html → explore/category/tech/index.html
                # de/category-archive/tech/index.html → de/explore/category/tech/index.html
                new_key = old_key.replace('category-archive/', 'explore/category/')
                move_object(old_key, new_key)
            if response.get('IsTruncated'):
                continuation_token = response.get('NextContinuationToken')
            else:
                break

    # 2. all-articles.html dosyalarını taşı
    print("\n📄 AŞAMA 2: all-articles.html taşınıyor...")
    all_articles_files = [
        ('all-articles.html', 'explore/all.html'),
        ('de/all-articles.html', 'de/explore/all.html'),
        ('es/all-articles.html', 'es/explore/all.html'),
        ('fr/all-articles.html', 'fr/explore/all.html')
    ]
    for old, new in all_articles_files:
        try:
            s3.head_object(Bucket=R2_BUCKET, Key=old)
            move_object(old, new)
        except:
            print(f"   ⚠️ {old} bulunamadı, atlanıyor.")

    # 3. categories.html dosyalarını taşı
    print("\n📂 AŞAMA 3: categories.html taşınıyor...")
    categories_files = [
        ('categories.html', 'explore/categories.html'),
        ('de/categories.html', 'de/explore/categories.html'),
        ('es/categories.html', 'es/explore/categories.html'),
        ('fr/categories.html', 'fr/explore/categories.html')
    ]
    for old, new in categories_files:
        try:
            s3.head_object(Bucket=R2_BUCKET, Key=old)
            move_object(old, new)
        except:
            print(f"   ⚠️ {old} bulunamadı, atlanıyor.")

    # 4. Eski klasörleri temizle
    print("\n🗑️ AŞAMA 4: Eski dosyalar temizleniyor...")
    delete_old_folders()

    print("\n" + "="*60)
    print("🏁 MIGRATION TAMAMLANDI")
    print("   ✅ explore/category/")
    print("   ✅ explore/all.html")
    print("   ✅ explore/categories.html")
    print("="*60)

if __name__ == "__main__":
    migrate_explore()
