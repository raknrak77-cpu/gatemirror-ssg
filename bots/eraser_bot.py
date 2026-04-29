import sys
import boto3
from datetime import datetime
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

BAD_HASHES = [
    '158c7c69', '25aee45b', '4c988f7d', '525ab926', '63d0286d', '6c77c4fa',
    '8a39223e', '96e4ebc6', '9a47e00a', '9cd3e5e0', 'a76fe9e8', '3a005196',
    '70fc256d', '7bf1b5cf', 'a14db796', 'c7617f3e', '2af9e5c5', '62052711',
    '63f5b7f6', 'c634d6f4', '41673832', '41bd6fa7', '488e32cc', '53487723',
    '8656379e', 'cdf6da5f', 'fd7ad7e8', '4ea1c02c', '63d7d6e8', '8e83d2e2',
    '9ab72a1f', '9c81ffc4', '9fdc1fb2', 'b2401d49', 'c347e192', 'c548e2fc',
    '8209c1b4'
]

ALL_LANGS = ['en', 'es', 'de', 'fr']
CATEGORIES = ['wellness', 'tech', 'future-economy', 'eco', 'elearning']
YEAR, MONTH = '2026', '04'

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def delete_file(key):
    try:
        s3.delete_object(Bucket=R2_BUCKET, Key=key)
        log(f"🗑️ {key}")
        return True
    except:
        return False

def delete_raw_articles():
    deleted = 0
    for h in BAD_HASHES:
        for lang in ALL_LANGS:
            for cat in CATEGORIES:
                for prefix in [f"raw-articles/{lang}/{cat}/{YEAR}/{MONTH}/", f"raw-articles/{lang}/{cat}/"]:
                    try:
                        resp = s3.list_objects_v2(Bucket=R2_BUCKET, Prefix=prefix)
                        if 'Contents' not in resp: continue
                        for obj in resp['Contents']:
                            if obj['Key'].split('/')[-1].startswith(h) and obj['Key'].endswith('.html'):
                                if delete_file(obj['Key']): deleted += 1
                    except: pass
    return deleted

def delete_images():
    deleted = 0
    for h in BAD_HASHES:
        for cat in CATEGORIES:
            for typ in ['kapak', 'icerik_1', 'icerik_2']:
                key = f"images/{YEAR}/{MONTH}/{cat}/{h}_{typ}.webp"
                try:
                    s3.head_object(Bucket=R2_BUCKET, Key=key)
                    if delete_file(key): deleted += 1
                except: pass
    return deleted

def delete_articles():
    deleted = 0
    for h in BAD_HASHES:
        for lang in ALL_LANGS:
            for cat in CATEGORIES:
                for prefix in [f"articles/{lang}/{cat}/{YEAR}/{MONTH}/", f"articles/{lang}/{cat}/"]:
                    try:
                        resp = s3.list_objects_v2(Bucket=R2_BUCKET, Prefix=prefix)
                        if 'Contents' not in resp: continue
                        for obj in resp['Contents']:
                            if obj['Key'].split('/')[-1].startswith(h) and obj['Key'].endswith('.html'):
                                if delete_file(obj['Key']): deleted += 1
                    except: pass
    return deleted

def main():
    print("🧹 ERASER BOT - ONAYSIZ SİLİNİYOR")
    print(f"37 hash, tüm diller, tüm kategoriler\n")
    d1 = delete_raw_articles()
    d2 = delete_images()
    d3 = delete_articles()
    print(f"\n✅ Silindi: raw:{d1}, images:{d2}, articles:{d3}, TOPLAM:{d1+d2+d3}")

if __name__ == "__main__":
    main()
