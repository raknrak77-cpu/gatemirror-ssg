import os
import boto3
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

def delete_folder(prefix):
    """R2'de bir klasörün içindeki tüm dosyaları sil"""
    continuation_token = None
    deleted_count = 0
    
    while True:
        try:
            if continuation_token:
                response = s3.list_objects_v2(
                    Bucket=R2_BUCKET,
                    Prefix=prefix,
                    ContinuationToken=continuation_token
                )
            else:
                response = s3.list_objects_v2(Bucket=R2_BUCKET, Prefix=prefix)
        except Exception as e:
            print(f"❌ Listeleme hatası: {e}")
            return False
        
        if 'Contents' not in response:
            break
        
        objects_to_delete = [{'Key': obj['Key']} for obj in response['Contents']]
        try:
            s3.delete_objects(Bucket=R2_BUCKET, Delete={'Objects': objects_to_delete})
            deleted_count += len(objects_to_delete)
            print(f"   🗑️ {deleted_count} dosya silindi...")
        except Exception as e:
            print(f"❌ Silme hatası: {e}")
            return False
        
        if response.get('IsTruncated'):
            continuation_token = response.get('NextContinuationToken')
        else:
            break
    
    print(f"✅ Toplam {deleted_count} dosya silindi: {prefix}")
    return True

def eraser():
    print("=" * 60)
    print("🧹 ERASER BOT - R2 ARTICLES SİLME")
    print("   ⚠️ SADECE /articles/ klasörünü siler")
    print("   ⚠️ raw-articles/ DOKUNULMAZ")
    print("=" * 60)
    
    print("\n📁 /articles/ klasörü taranıyor...")
    
    # Sadece articles/ sil
    success = delete_folder('articles/')
    
    if success:
        print("\n✅ ERASER TAMAMLANDI!")
        print("   ✅ /articles/ klasörü temizlendi")
        print("   ✅ raw-articles/ aynen duruyor")
    else:
        print("\n❌ ERASER BAŞARISIZ!")
    
    print("=" * 60)

if __name__ == "__main__":
    eraser()
