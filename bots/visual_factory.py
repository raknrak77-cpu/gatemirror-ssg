import os
import sys
import json
import time
import requests
import boto3
from botocore.client import Config
from PIL import Image
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# ================= KONFIGURASYON =================
CF_TOKEN = os.getenv('CLOUDFLARE_API_TOKEN')
CF_ACCOUNT = os.getenv('CLOUDFLARE_ACCOUNT_ID')
CF_AI_GATEWAY = f"https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT}/ai/run/"

R2_ID = os.getenv('R2_ACCOUNT_ID')
R2_ACCESS_KEY = os.getenv('R2_ACCESS_KEY_ID')
R2_SECRET_KEY = os.getenv('R2_SECRET_ACCESS_KEY')
R2_BUCKET = os.getenv('R2_BUCKET_NAME')
R2_PUBLIC_URL = os.getenv('R2_PUBLIC_URL', '').rstrip('/')

s3 = boto3.client(
    's3',
    endpoint_url=f'https://{R2_ID}.r2.cloudflarestorage.com',
    aws_access_key_id=R2_ACCESS_KEY,
    aws_secret_access_key=R2_SECRET_KEY,
    config=Config(signature_version='s3v4'),
    region_name='auto'
)

# Rate limit koruması için token bucket
request_times = []
time_lock = threading.Lock()

# ================= KATEGORİ BAZLI STİLLER =================
CATEGORY_STYLES = {
    "wellness": "warm, organic, human-centric, soft natural light, intimate moments, plants, nature, calm atmosphere, spa vibes, healthy living",
    "tech": "clean, futuristic, geometric, blue/silver tones, high-tech aesthetic, sleek surfaces, ambient glow, innovation focus",
    "future-economy": "corporate, data-driven, minimalist, glass and steel, professional, abstract financial metaphors, global perspective",
    "eco": "natural, green, sustainable, outdoor, golden hour, organic textures, renewable energy visuals, pristine environment",
    "elearning": "bright, educational, approachable, modern, focused on people learning, books, digital interfaces, cozy study spaces"
}

# ================= GLOBAL STYLE =================
GLOBAL_STYLE = """
Style:
- photorealistic
- cinematic lighting
- shallow depth of field
- ultra-detailed
- natural color grading
- high dynamic range
- soft film grain

Technical:
- square format (1:1)
- 1024x1024 resolution
"""

NEGATIVE_CONSTRAINTS = """
Strict constraints:
- NO text, typography, letters, words, or symbols
- NO logos, brands, or watermarks
- NO diagrams, charts, infographics, UI elements, or overlays
- NO fake data or labels
- NO exaggerated CGI look
- NO distorted anatomy or unrealistic structures
"""

def get_category_style(kategori):
    return CATEGORY_STYLES.get(kategori, "professional, clean, modern, versatile")

# ================= YARDIMCI FONKSİYONLAR =================
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

def enrich_prompt(base_prompt, kategori):
    category_style = get_category_style(kategori)
    return f"""You are a world-class versatile visual photographer.

SUBJECT (MUST FOLLOW):
{base_prompt}

CATEGORY ATMOSPHERE:
{category_style}

{GLOBAL_STYLE}

{NEGATIVE_CONSTRAINTS}

IMPORTANT:
- The SUBJECT above is the main focus. DO NOT ignore it.
- The CATEGORY ATMOSPHERE only guides the mood and lighting, not the subject.
- Create a photorealistic, cinematic image that matches the SUBJECT with the appropriate ATMOSPHERE.
"""

def rate_limit_wait():
    """Rate limit koruması - son 10 saniyede 3 istekten fazla varsa bekle"""
    with time_lock:
        now = time.time()
        global request_times
        request_times = [t for t in request_times if now - t < 10]
        if len(request_times) >= 3:
            wait_time = 3
            print(f"⏳ Rate limit koruması: {wait_time} saniye bekleniyor...")
            time.sleep(wait_time)
            return rate_limit_wait()
        request_times.append(now)
    return True

def generate_image(prompt, model, width, height, output_png):
    print(f"🎨 [{output_png}] {width}x{height} formatında görsel üretiliyor...")
    
    # Rate limit kontrolü
    rate_limit_wait()
    
    headers = {"Authorization": f"Bearer {CF_TOKEN}", "Content-Type": "application/json"}
    payload = {
        "prompt": prompt,
        "width": width,
        "height": height,
        "num_steps": 20,
        "guidance": 7.5
    }
    
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
                    time.sleep(3)
                    continue
            elif response.status_code == 429:
                print(f"⚠️ Rate limit (429), 5 saniye bekleniyor...")
                time.sleep(5)
                continue
            else:
                print(f"⚠️ HTTP {response.status_code} (deneme {attempt+1}/3)")
        except Exception as e:
            print(f"⚠️ Hata (deneme {attempt+1}/3): {e}")
        
        if attempt < 2:
            wait = 3 if attempt == 0 else 5
            print(f"⏳ {wait} saniye bekleniyor...")
            time.sleep(wait)
    
    print(f"❌ {output_png} üretilemedi (3 deneme başarısız).")
    return False

def process_single_image(image_type, image_data, hash_id, kategori, yil, ay, r2_folder, results):
    """Tek bir görseli işle (parallel için)"""
    try:
        png_file = f"{hash_id}_{image_type}.png"
        webp_file = f"{hash_id}_{image_type}.webp"
        
        base_prompt = image_data.get("prompt", "")
        full_prompt = enrich_prompt(base_prompt, kategori)
        
        if generate_image(full_prompt, "@cf/stabilityai/stable-diffusion-xl-base-1.0", 1024, 1024, png_file):
            if convert_to_webp(png_file, webp_file):
                r2_key = f"{r2_folder}/{hash_id}_{image_type}.webp"
                upload_to_r2(webp_file, r2_key)
                os.remove(webp_file)
            os.remove(png_file)
            results[image_type] = True
            return image_type, True
        results[image_type] = False
        return image_type, False
    except Exception as e:
        print(f"⚠️ {image_type} işlenirken hata: {e}")
        results[image_type] = False
        return image_type, False

def visual_factory():
    if len(sys.argv) < 7:
        print("❌ Kullanım: python visual_factory.py <task_id> <hash> <visuals_json> <kategori> <yil> <ay>")
        return
    
    task_id = sys.argv[1]
    hash_id = sys.argv[2]
    visuals_json = sys.argv[3]
    kategori = sys.argv[4]
    yil = sys.argv[5]
    ay = sys.argv[6]
    
    try:
        visuals = json.loads(visuals_json)
    except:
        print("❌ visuals JSON parse edilemedi!")
        return
    
    print(f"\n🖼️ Görsel üretimi (Task: {task_id}, Hash: {hash_id}, Kategori: {kategori})")
    print(f"   🚀 PARALEL MOD: 3 görsel aynı anda işleniyor (rate limit korumalı)")
    
    r2_folder = f"images/{yil}/{ay}/{kategori}"
    
    # İşlenecek görselleri hazırla
    images_to_process = []
    
    if "kapak" in visuals:
        images_to_process.append(("kapak", visuals["kapak"]))
    if "icerik_1" in visuals:
        images_to_process.append(("icerik_1", visuals["icerik_1"]))
    if "icerik_2" in visuals:
        images_to_process.append(("icerik_2", visuals["icerik_2"]))
    
    if not images_to_process:
        print("⚠️ Hiç görsel prompt'u yok!")
        return
    
    # PARALEL işleme
    results = {}
    start_time = time.time()
    
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = []
        for img_type, img_data in images_to_process:
            future = executor.submit(
                process_single_image, 
                img_type, img_data, hash_id, kategori, yil, ay, r2_folder, results
            )
            futures.append(future)
        
        # Tüm işlemlerin tamamlanmasını bekle
        for future in as_completed(futures):
            img_type, success = future.result()
            status = "✅" if success else "❌"
            print(f"   {status} {img_type} tamamlandı")
    
    elapsed = time.time() - start_time
    success_count = sum(1 for v in results.values() if v)
    
    print(f"\n✅ Görsel işlemleri tamamlandı!")
    print(f"   📁 R2 klasörü: {r2_folder}")
    print(f"   📊 Başarılı: {success_count}/{len(images_to_process)}")
    print(f"   ⏱️ Toplam süre: {elapsed:.1f} saniye")
    print(f"   🎨 Kategori stili: {get_category_style(kategori)}")

if __name__ == "__main__":
    visual_factory()
