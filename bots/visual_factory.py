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

# Rate limit koruması
request_times = []
time_lock = threading.Lock()

# ================= KATEGORİ BAZLI STİLLER =================
CATEGORY_STYLES = {
    "wellness": "warm, organic, human-centric, soft natural light, intimate moments, plants, nature, calm atmosphere, spa vibes, healthy living",
    "tech": "clean, futuristic, geometric, blue/silver tones, high-tech aesthetic, sleek surfaces, ambient glow, innovation focus",
    "future-economy": "corporate, data-driven, minimalist, glass and steel, professional, abstract financial metaphors, global perspective",
    "eco": "natural, green, sustainable, outdoor, golden hour, organic textures, renewable energy visuals, pristine environment",
    "elearning": "bright, photorealistic, real people in actual learning environments, natural lighting, authentic study moments, actual laptops and tablets, cozy warm atmosphere, documentary style, candid learner perspectives, modern campus areas, libraries, study halls, classrooms"
}

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
- 16:9 aspect ratio (landscape)
"""

COMPOSITION_RULES = """
COMPOSITION RULES (CRITICAL):
- Canvas is 16:9 aspect ratio (landscape format)
- The main subject MUST be positioned effectively within the wider frame
- The scene MUST fill the ENTIRE frame naturally
- NO empty spaces, NO solid color bars, NO letterboxing
- Use the horizontal space for environmental context
- EVERY part of the 16:9 canvas MUST contain meaningful visual content
"""

NEGATIVE_CONSTRAINTS = """
NEGATIVE PROMPT (STRICTLY FORBIDDEN):
- ANY text, letters, words, numbers, typography, captions, labels, headers
- ANY logo, brand, watermark, signature, stamp
- ANY chart, graph, diagram, infographic, data visualization, UI element, button, icon, progress bar
- ANY fake data, statistics, numbers, percentages
- ANY barcode, QR code, timestamp
- ANY frame, border, overlay, HUD element
- ANY exaggerated CGI, plastic-looking renders
- ANY distorted anatomy, unnatural proportions
- ANY blurry or pixelated areas

The image must be a CLEAN, PURE photograph with NO superimposed elements. Only natural scene content.
"""

DEFAULT_WIDTH = 1024
DEFAULT_HEIGHT = 576

def get_category_style(kategori):
    return CATEGORY_STYLES.get(kategori, "professional, clean, modern, versatile")

def is_valid_image(filepath):
    if not os.path.exists(filepath):
        return False
    if os.path.getsize(filepath) < 300000:
        return False
    try:
        with Image.open(filepath) as img:
            if img.size[0] < 512 or img.size[1] < 512:
                return False
            return True
    except:
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

def enrich_prompt(prompt_text, kategori):
    category_style = get_category_style(kategori)
    
    return f"""You are a world-class versatile visual photographer.

SUBJECT (MUST FOLLOW):
{prompt_text}

CATEGORY ATMOSPHERE:
{category_style}

{GLOBAL_STYLE}

{COMPOSITION_RULES}

{NEGATIVE_CONSTRAINTS}

IMPORTANT:
- The SUBJECT above is the main focus. DO NOT ignore it.
- The CATEGORY ATMOSPHERE only guides the mood and lighting.
- Create a photorealistic, cinematic landscape image in 16:9 format.
- The image must contain NO text, NO logos, NO charts, NO overlays of any kind.
"""

def rate_limit_wait():
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

def generate_image(prompt, model, width, height, output_png, attempt=1):
    print(f"🎨 [{output_png}] Deneme {attempt}/3: {width}x{height} (16:9) görsel üretiliyor...")
    
    rate_limit_wait()
    
    headers = {"Authorization": f"Bearer {CF_TOKEN}", "Content-Type": "application/json"}
    payload = {
        "prompt": prompt,
        "width": width,
        "height": height,
        "num_steps": 30,
        "guidance": 8.5
    }
    
    try:
        start_time = time.time()
        response = requests.post(f"{CF_AI_GATEWAY}{model}", headers=headers, json=payload, timeout=120)
        elapsed = time.time() - start_time
        
        print(f"   HTTP {response.status_code} - {elapsed:.1f}s")
        
        if response.status_code == 200:
            with open(output_png, "wb") as f:
                f.write(response.content)
            
            file_size_kb = os.path.getsize(output_png) // 1024
            print(f"   Dosya boyutu: {file_size_kb} KB")
            
            if is_valid_image(output_png):
                print(f"✅ {output_png} GEÇERLİ görsel ({file_size_kb} KB)")
                return True
            else:
                print(f"⚠️ {output_png} GEÇERSİZ (bozuk veya çok küçük)")
                os.remove(output_png)
                return False
        elif response.status_code == 429:
            print(f"⚠️ Rate limit (429), 5 saniye bekleniyor...")
            time.sleep(5)
            return False
        else:
            print(f"⚠️ HTTP {response.status_code}")
            try:
                error_data = response.json()
                print(f"   Hata detayı: {json.dumps(error_data, indent=2)[:500]}")
            except:
                print(f"   Yanıt: {response.text[:200]}")
            return False
    except Exception as e:
        print(f"⚠️ İstek hatası: {e}")
        return False

def process_single_image(image_type, prompt_text, hash_id, kategori, yil, ay, r2_folder, results):
    """Tek bir görseli işle - prompt_text DOĞRUDAN string"""
    print(f"\n🖼️ [{image_type.upper()}] Başlıyor...")
    print(f"   Prompt: {prompt_text[:100]}...")
    
    try:
        png_file = f"{hash_id}_{image_type}.png"
        webp_file = f"{hash_id}_{image_type}.webp"
        
        full_prompt = enrich_prompt(prompt_text, kategori)
        
        success = False
        for attempt in range(1, 4):
            if generate_image(full_prompt, "@cf/stabilityai/stable-diffusion-xl-base-1.0", DEFAULT_WIDTH, DEFAULT_HEIGHT, png_file, attempt):
                success = True
                break
            if attempt < 3:
                print(f"   {attempt}. deneme başarısız, 3 saniye bekleniyor...")
                time.sleep(3)
        
        if not success:
            print(f"❌ [{image_type.upper()}] 3 deneme sonunda BAŞARISIZ")
            results[image_type] = False
            return image_type, False
        
        # WebP dönüşümü ve R2 yükleme
        if convert_to_webp(png_file, webp_file):
            r2_key = f"{r2_folder}/{hash_id}_{image_type}.webp"
            upload_to_r2(webp_file, r2_key)
            os.remove(webp_file)
            print(f"✅ [{image_type.upper()}] TAMAMLANDI (R2'de)")
        else:
            print(f"⚠️ [{image_type.upper()}] WebP dönüşümü başarısız, PNG siliniyor")
        
        os.remove(png_file)
        results[image_type] = True
        return image_type, True
        
    except Exception as e:
        print(f"❌ [{image_type.upper()}] KRİTİK HATA: {e}")
        import traceback
        traceback.print_exc()
        results[image_type] = False
        return image_type, False

def visual_factory():
    print("\n" + "=" * 70)
    print("🎨 VISUAL FACTORY V16 - 16:9 MODE")
    print("=" * 70)
    
    if len(sys.argv) < 7:
        print("❌ Kullanım: python visual_factory.py <task_id> <hash> <visuals_json> <kategori> <yil> <ay>")
        return
    
    task_id = sys.argv[1]
    hash_id = sys.argv[2]
    visuals_json = sys.argv[3]
    kategori = sys.argv[4]
    yil = sys.argv[5]
    ay = sys.argv[6]
    
    print(f"\n📋 GÖREV BİLGİLERİ:")
    print(f"   Task ID: {task_id}")
    print(f"   Hash: {hash_id}")
    print(f"   Kategori: {kategori}")
    print(f"   Tarih: {yil}/{ay}")
    
    try:
        visuals = json.loads(visuals_json)
        print(f"   Görsel sayısı: {len(visuals)}")
        for key in visuals.keys():
            print(f"      - {key}")
    except Exception as e:
        print(f"❌ visuals JSON parse edilemedi: {e}")
        print(f"   Raw: {visuals_json[:200]}")
        return
    
    print(f"\n🖼️ Görsel üretimi başlıyor...")
    print(f"   🎯 Format: {DEFAULT_WIDTH}x{DEFAULT_HEIGHT} (16:9)")
    print(f"   🚀 Paralel işleme: 3 görsel aynı anda")
    
    r2_folder = f"images/{yil}/{ay}/{kategori}"
    
    # İşlenecek görseller - visuals[key] DOĞRUDAN string prompt
    images_to_process = []
    for img_type, prompt_text in visuals.items():
        if prompt_text and isinstance(prompt_text, str):
            images_to_process.append((img_type, prompt_text))
            print(f"   📝 {img_type}: prompt uzunluğu {len(prompt_text)} karakter")
        else:
            print(f"   ⚠️ {img_type}: geçersiz prompt (type: {type(prompt_text)})")
    
    if not images_to_process:
        print("❌ Hiç geçerli görsel prompt'u yok!")
        return
    
    print(f"\n🚀 {len(images_to_process)} görsel paralel işleniyor...")
    print("-" * 50)
    
    results = {}
    start_time = time.time()
    
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = []
        for img_type, prompt_text in images_to_process:
            future = executor.submit(
                process_single_image, 
                img_type, prompt_text, hash_id, kategori, yil, ay, r2_folder, results
            )
            futures.append(future)
        
        for future in as_completed(futures):
            img_type, success = future.result()
            status = "✅ BAŞARILI" if success else "❌ BAŞARISIZ"
            print(f"\n   {status}: {img_type}")
    
    elapsed = time.time() - start_time
    success_count = sum(1 for v in results.values() if v)
    fail_count = len(images_to_process) - success_count
    
    print("\n" + "=" * 70)
    print("📊 GÖRSEL ÜRETİM RAPORU")
    print(f"   ✅ Başarılı: {success_count}/{len(images_to_process)}")
    print(f"   ❌ Başarısız: {fail_count}/{len(images_to_process)}")
    print(f"   ⏱️ Toplam süre: {elapsed:.1f} saniye")
    print(f"   📁 R2 klasörü: {r2_folder}")
    print(f"   🎨 Kategori: {kategori}")
    print(f"   📐 Boyut: {DEFAULT_WIDTH}x{DEFAULT_HEIGHT} (16:9)")
    
    for img_type, success in results.items():
        print(f"   {img_type}: {'✅' if success else '❌'}")
    
    print("=" * 70)
    
    # Çıkış kodu: 3 görselin tamamı başarılıysa 0, değilse 1
    if success_count == 3:
        print("\n✅ TÜM GÖRSELLER BAŞARILI")
        sys.exit(0)
    elif success_count > 0:
        print(f"\n⚠️ KISMİ BAŞARI ({success_count}/3 görsel başarılı)")
        sys.exit(1)
    else:
        print("\n❌ HİÇBİR GÖRSEL ÜRETİLEMEDİ")
        sys.exit(1)

if __name__ == "__main__":
    visual_factory()
