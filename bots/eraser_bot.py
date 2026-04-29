import os
import sys
import json
import boto3
from datetime import datetime
from botocore.client import Config

# ================= KONFIGURASYON =================
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

# ================= 36 HATALI HASH (TÜM DİLLERDE SİLİNECEK) =================
BAD_HASHES = [
    '158c7c69', '25aee45b', '4c988f7d', '525ab926', '63d0286d', '6c77c4fa',
    '8a39223e', '96e4ebc6', '9a47e00a', '9cd3e5e0', 'a76fe9e8', '3a005196',
    '70fc256d', '7bf1b5cf', 'a14db796', 'c7617f3e', '2af9e5c5', '62052711',
    '63f5b7f6', 'c634d6f4', '41673832', '41bd6fa7', '488e32cc', '53487723',
    '8656379e', 'cdf6da5f', 'fd7ad7e8', '4ea1c02c', '63d7d6e8', '8e83d2e2',
    '9ab72a1f', '9c81ffc4', '9fdc1fb2', 'b2401d49', 'c347e192', 'c548e2fc',
    '8209c1b4'
]

# TÜM DİLLER (EN, ES, DE, FR)
ALL_LANGS = ['en', 'es', 'de', 'fr']

# Kategoriler
CATEGORIES = ['wellness', 'tech', 'future-economy', 'eco', 'elearning']

# Yıl/Ay
YEAR = '2026'
MONTH = '04'


def log(msg, level="INFO"):
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    print(f"[{timestamp}] [{level}] {msg}")


def delete_file(key):
    try:
        s3.delete_object(Bucket=R2_BUCKET, Key=key)
        log(f"   🗑️ Silindi: {key}")
        return True
    except Exception as e:
        log(f"   ⚠️ Silinemedi: {key} - {e}", "WARN")
        return False


def list_files_with_prefix(prefix):
    files = []
    continuation_token = None
    try:
        while True:
            if continuation_token:
                response = s3.list_objects_v2(
                    Bucket=R2_BUCKET, 
                    Prefix=prefix, 
                    ContinuationToken=continuation_token
                )
            else:
                response = s3.list_objects_v2(Bucket=R2_BUCKET, Prefix=prefix)
            
            if 'Contents' not in response:
                break
                
            for obj in response['Contents']:
                files.append(obj['Key'])
            
            if response.get('IsTruncated'):
                continuation_token = response.get('NextContinuationToken')
            else:
                break
    except Exception as e:
        log(f"Listeleme hatası ({prefix}): {e}", "WARN")
    
    return files


def delete_raw_articles():
    log("\n" + "=" * 60)
    log("📁 RAW-ARTICLES TEMİZLİĞİ (TÜM DİLLER)")
    log("=" * 60)
    
    deleted_count = 0
    
    for hash_id in BAD_HASHES:
        for lang in ALL_LANGS:
            for category in CATEGORIES:
                prefixes = [
                    f"raw-articles/{lang}/{category}/{YEAR}/{MONTH}/",
                    f"raw-articles/{lang}/{category}/"
                ]
                
                for prefix in prefixes:
                    files = list_files_with_prefix(prefix)
                    for key in files:
                        filename = key.split('/')[-1]
                        if filename.startswith(hash_id) and filename.endswith('.html'):
                            delete_file(key)
                            deleted_count += 1
                            break
    
    log(f"\n📊 RAW-ARTICLES: {deleted_count} dosya silindi")
    return deleted_count


def delete_images():
    log("\n" + "=" * 60)
    log("📁 IMAGES TEMİZLİĞİ (TÜM DİLLER)")
    log("=" * 60)
    
    deleted_count = 0
    image_types = ['kapak', 'icerik_1', 'icerik_2']
    
    for hash_id in BAD_HASHES:
        for category in CATEGORIES:
            for img_type in image_types:
                key = f"images/{YEAR}/{MONTH}/{category}/{hash_id}_{img_type}.webp"
                try:
                    s3.head_object(Bucket=R2_BUCKET, Key=key)
                    delete_file(key)
                    deleted_count += 1
                except:
                    pass
    
    log(f"\n📊 IMAGES: {deleted_count} dosya silindi")
    return deleted_count


def delete_articles():
    log("\n" + "=" * 60)
    log("📁 ARTICLES TEMİZLİĞİ (TÜM DİLLER)")
    log("=" * 60)
    
    deleted_count = 0
    
    for hash_id in BAD_HASHES:
        for lang in ALL_LANGS:
            for category in CATEGORIES:
                prefixes = [
                    f"articles/{lang}/{category}/{YEAR}/{MONTH}/",
                    f"articles/{lang}/{category}/"
                ]
                
                for prefix in prefixes:
                    files = list_files_with_prefix(prefix)
                    for key in files:
                        filename = key.split('/')[-1]
                        if filename.startswith(hash_id) and filename.endswith('.html'):
                            delete_file(key)
                            deleted_count += 1
                            break
    
    log(f"\n📊 ARTICLES: {deleted_count} dosya silindi")
    return deleted_count


def generate_report(deleted_raw, deleted_images, deleted_articles):
    log("\n" + "=" * 60)
    log("📊 TEMİZLİK RAPORU")
    log("=" * 60)
    log(f"   raw-articles/ silinen: {deleted_raw}")
    log(f"   images/ silinen: {deleted_images}")
    log(f"   articles/ silinen: {deleted_articles}")
    log(f"   TOPLAM silinen: {deleted_raw + deleted_images + deleted_articles}")
    log("=" * 60)


def eraser_bot():
    print("\n" + "=" * 70)
    print("🧹 ERASER BOT - HATALI MAKALE TEMİZLİĞİ")
    print(f"   Toplam hash: {len(BAD_HASHES)}")
    print(f"   Silinecek diller: {', '.join(ALL_LANGS)} (TÜM DİLLER)")
    print(f"   Kategoriler: {', '.join(CATEGORIES)}")
    print("=" * 70)
    
    log("⚠️ DİKKAT! Bu bot aşağıdaki dosyaları silecek:")
    log(f"   - {len(BAD_HASHES)} hash için raw-articles/ dosyaları (TÜM DİLLER)")
    log(f"   - images/ altındaki görseller (TÜM DİLLER)")
    log(f"   - articles/ altındaki dosyalar (TÜM DİLLER)")
    log("")
    
    if len(sys.argv) > 1 and sys.argv[1] == '--force':
        log("🚀 FORCE modu ile çalışılıyor, hemen siliniyor...")
    else:
        log("❓ Devam etmek için 'yes' yazın: ")
        confirm = input()
        if confirm.lower() != 'yes':
            log("İşlem iptal edildi.")
            sys.exit(0)
    
    deleted_raw = delete_raw_articles()
    deleted_images = delete_images()
    deleted_articles = delete_articles()
    
    generate_report(deleted_raw, deleted_images, deleted_articles)
    
    log("\n✅ ERASER BOT TAMAMLANDI!")


if __name__ == "__main__":
    eraser_bot()
