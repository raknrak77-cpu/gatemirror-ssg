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

def download_folder(prefix, local_dir):
    os.makedirs(local_dir, exist_ok=True)
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
            local_path = os.path.join(local_dir, key.replace(prefix, ''))
            local_path_dir = os.path.dirname(local_path)
            os.makedirs(local_path_dir, exist_ok=True)
            
            try:
                file_obj = s3.get_object(Bucket=R2_BUCKET, Key=key)
                with open(local_path, 'wb') as f:
                    f.write(file_obj['Body'].read())
                print(f"   📥 İndirildi: {key}")
                downloaded_count += 1
            except Exception as e:
                print(f"   ❌ Hata: {key} - {e}")
        
        if response.get('IsTruncated'):
            continuation_token = response.get('NextContinuationToken')
        else:
            break
    
    print(f"✅ Toplam {downloaded_count} dosya indirildi.")

def downloader():
    print("\n" + "="*60)
    print("📥 DOWNLOADER BOT - ilk_demo klasörü indiriliyor")
    print("="*60)
    # 🔥 DÜZELTİLDİ: ilk-demo → ilk_demo
    download_folder("ilk_demo/", "downloaded/ilk_demo")
    print("\n✅ İndirme tamamlandı.")

if __name__ == "__main__":
    downloader()
