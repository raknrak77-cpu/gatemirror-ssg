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

def delete_folder(prefix):
    """R2'deki bir klasörü tamamen sil (içindeki tüm dosyalar)"""
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
                print(f"   ❌ Hata: {key} - {e}")
        
        if response.get('IsTruncated'):
            continuation_token = response.get('NextContinuationToken')
        else:
            break
    
    print(f"✅ Toplam {deleted_count} dosya silindi.")
    return deleted_count

def delete_ilk_demo():
    print("\n" + "="*60)
    print("🗑️ SİLME BOTU - ilk_demo klasörü siliniyor")
    print("="*60)
    
    delete_folder("ilk_demo/")
    
    print("\n✅ ilk_demo klasörü R2'den tamamen silindi.")

if __name__ == "__main__":
    delete_ilk_demo()
