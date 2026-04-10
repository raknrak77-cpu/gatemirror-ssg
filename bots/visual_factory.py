import os
import sys
import json
import time
import requests
import boto3
from botocore.client import Config
from PIL import Image

# Cloudflare AI
CF_TOKEN = os.getenv('CLOUDFLARE_API_TOKEN')
CF_ACCOUNT = os.getenv('CLOUDFLARE_ACCOUNT_ID')
CF_AI_GATEWAY = f"https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT}/ai/run/"

# R2
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

def is_valid_image(filepath):
    if not os.path.exists(filepath):
        return False
    if os.path.getsize(filepath) < 300000:
        return False
    try:
        with open(filepath, 'rb') as f:
            header = f.read(12)
            if header.startswith(b'\x89PNG\r\n\x1a\n'):
                return True
            if header.startswith(b'\xff\xd8\xff'):
                return True
    except:
        pass
    return False

def convert_to_webp(input_path, output_path):
    try:
        with Image.open(input_path) as img:
            if img.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = background
            img.save(output_path, 'WEBP', quality=85)
        return True
    except Exception as e:
        print(f"⚠️ WebP dönüşüm hatası: {e}")
        return False

def upload_to_r2(local_path, r2_key):
    if os.path.exists(local_path):
        s3.upload_file(local_path, R2_BUCKET, r2_key)
        print(f"✅ R2'ye yüklendi: {r2_key}")
        return True
    return False

def generate_image(prompt, model, width, height, output_png):
    print(f"🎨 [{output_png}] {width}x{height} formatında görsel üretiliyor...")
    
    headers = {"Authorization": f"Bearer {CF_TOKEN}", "Content-Type": "application/json"}
    payload = {"prompt": prompt, "width": width, "height": height, "num_steps": 20, "guidance": 7.5}
    
    for attempt in range(3):
        try:
            response = requests.post(f"{CF_AI_GATEWAY}{model}", headers=headers, json=payload, timeout=120)
            if response.status_code == 200:
                with open(output_png, "wb") as f:
                    f.write(response.content)
                
                if is_valid_image(output_png):
                    size_kb = os.path.getsize(output_png) // 1024
                    print(f"✅ {output_png} oluşturuldu (geçerli, {size_kb} KB)")
                    return True
                else:
                    print(f"⚠️ {output_png} geçersiz (bozuk), yeniden deneniyor...")
                    os.remove(output_png)
                    time.sleep(5)
                    continue
            else:
                print(f"⚠️ HTTP {response.status_code} (deneme {attempt+1}/3)")
        except Exception as e:
            print(f"⚠️ Hata (deneme {attempt+1}/3): {e}")
        
        if attempt < 2:
            print(f"⏳ 15 saniye bekleniyor...")
            time.sleep(15)
    
    print(f"❌ {output_png} üretilemedi (3 deneme başarısız).")
    return False

def visual_factory():
    if len(sys.argv) < 5:
        print("❌ Kullanım: python visual_factory.py <task_id> <hash> <visuals_json> <kategori>")
        return
    
    task_id = sys.argv[1]
    hash_id = sys.argv[2]
    visuals_json = sys.argv[3]
    kategori = sys.argv[4]
    
    try:
        visuals = json.loads(visuals_json)
    except:
        print("❌ visuals JSON parse edilemedi!")
        return
    
    print(f"🖼️ Görsel üretimi (Task: {task_id}, Hash: {hash_id}, Kategori: {kategori})")
    
    # Geçici PNG dosyaları
    kapak_png = f"{hash_id}_kapak.png"
    icerik_png = f"{hash_id}_icerik.png"
    
    # 1. Kapak Görseli (1024x1024, Stable Diffusion)
    kapak = visuals.get("kapak", {})
    if kapak:
        if generate_image(kapak.get("prompt", ""), "@cf/stabilityai/stable-diffusion-xl-base-1.0", 1024, 1024, kapak_png):
            kapak_webp = f"{hash_id}_kapak.webp"
            if convert_to_webp(kapak_png, kapak_webp):
                r2_key = f"images/{kategori}/{hash_id}_kapak.webp"
                upload_to_r2(kapak_webp, r2_key)
                os.remove(kapak_webp)
            os.remove(kapak_png)
        time.sleep(5)
    
    # 2. İç Görsel (640x640, Stable Diffusion)
    icerik = visuals.get("icerik_1", {})
    if icerik:
        if generate_image(icerik.get("prompt", ""), "@cf/stabilityai/stable-diffusion-xl-base-1.0", 640, 640, icerik_png):
            icerik_webp = f"{hash_id}_icerik.webp"
            if convert_to_webp(icerik_png, icerik_webp):
                r2_key = f"images/{kategori}/{hash_id}_icerik.webp"
                upload_to_r2(icerik_webp, r2_key)
                os.remove(icerik_webp)
            os.remove(icerik_png)
    
    print(f"\n✅ Görsel işlemleri tamamlandı. (WebP, R2'de)")

if __name__ == "__main__":
    visual_factory()
