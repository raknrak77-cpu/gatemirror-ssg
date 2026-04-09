import os
import sys
import json
import time
import requests

CF_TOKEN = os.getenv('CLOUDFLARE_API_TOKEN')
CF_ACCOUNT = os.getenv('CLOUDFLARE_ACCOUNT_ID')
CF_AI_GATEWAY = f"https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT}/ai/run/"

def is_valid_image(filepath):
    """Dosyanın geçerli bir resim olup olmadığını kontrol eder (PNG/JPEG/WebP)"""
    if not os.path.exists(filepath):
        return False
    if os.path.getsize(filepath) < 300000:  # 300 KB'dan küçükse bozuk
        return False
    try:
        with open(filepath, 'rb') as f:
            header = f.read(12)
            if header.startswith(b'\x89PNG\r\n\x1a\n'):
                return True
            if header.startswith(b'\xff\xd8\xff'):
                return True
            if header.startswith(b'RIFF') and header[8:12] == b'WEBP':
                return True
    except:
        pass
    return False

def generate_image(prompt, model, width, height, output_filename):
    """Belirtilen model ve formatta görsel üretir, geçersizse yeniden dener"""
    print(f"🎨 [{output_filename}] {width}x{height} formatında görsel üretiliyor...")
    
    headers = {"Authorization": f"Bearer {CF_TOKEN}", "Content-Type": "application/json"}
    payload = {"prompt": prompt, "width": width, "height": height, "num_steps": 20, "guidance": 7.5}
    
    if "flux" in model:
        payload["num_steps"] = 8
    
    for attempt in range(3):
        try:
            response = requests.post(f"{CF_AI_GATEWAY}{model}", headers=headers, json=payload, timeout=120)
            if response.status_code == 200:
                with open(output_filename, "wb") as f:
                    f.write(response.content)
                
                if is_valid_image(output_filename):
                    size_kb = os.path.getsize(output_filename) // 1024
                    print(f"✅ {output_filename} oluşturuldu (geçerli, {size_kb} KB)")
                    return True
                else:
                    print(f"⚠️ {output_filename} geçersiz (bozuk), yeniden deneniyor...")
                    os.remove(output_filename)
                    time.sleep(5)
                    continue
            else:
                print(f"⚠️ HTTP {response.status_code} (deneme {attempt+1}/3)")
        except Exception as e:
            print(f"⚠️ Hata (deneme {attempt+1}/3): {e}")
        
        if attempt < 2:
            print(f"⏳ 15 saniye bekleniyor...")
            time.sleep(15)
    
    print(f"❌ {output_filename} üretilemedi (3 deneme başarısız).")
    return False

def visual_factory():
    """
    Creator bot'tan gelen parametrelerle çalışır:
    - argv[1]: task_id (0007)
    - argv[2]: hash (a3f5c2d1)
    - argv[3]: visuals (JSON string)
    """
    
    if len(sys.argv) < 4:
        print("❌ Kullanım: python visual_factory.py <task_id> <hash> <visuals_json>")
        print("   Örnek: python visual_factory.py 0007 a3f5c2d1 '{\"kapak\":{...}}'")
        return
    
    task_id = sys.argv[1]
    hash_id = sys.argv[2]
    visuals_json = sys.argv[3]
    
    try:
        visuals = json.loads(visuals_json)
    except:
        print("❌ visuals JSON parse edilemedi!")
        return
    
    print(f"🖼️ Görsel üretimi başlatılıyor (Task: {task_id}, Hash: {hash_id})")
    
    # Görsel dosya adları (hash ile)
    kapak_dosya = f"{hash_id}_kapak.png"
    icerik1_dosya = f"{hash_id}_icerik_1.png"
    icerik2_dosya = f"{hash_id}_icerik_2.png"
    
    # 1. Kapak Görseli (16:9)
    kapak = visuals.get("kapak", {})
    if kapak:
        generate_image(
            kapak.get("prompt", ""),
            "@cf/black-forest-labs/flux-1-schnell",
            kapak.get("width", 1280),
            kapak.get("height", 720),
            kapak_dosya
        )
        time.sleep(5)
    
    # 2. İç Görsel 1 (Kare)
    icerik1 = visuals.get("icerik_1", {})
    if icerik1:
        generate_image(
            icerik1.get("prompt", ""),
            "@cf/stabilityai/stable-diffusion-xl-base-1.0",
            icerik1.get("width", 1024),
            icerik1.get("height", 1024),
            icerik1_dosya
        )
        time.sleep(5)
    
    # 3. İç Görsel 2 (Yatay)
    icerik2 = visuals.get("icerik_2", {})
    if icerik2:
        generate_image(
            icerik2.get("prompt", ""),
            "@cf/bytedance/stable-diffusion-xl-lightning",
            icerik2.get("width", 1280),
            icerik2.get("height", 720),
            icerik2_dosya
        )
    
    # Metadata JSON (uploader bot için)
    metadata = {
        "task_id": task_id,
        "hash": hash_id,
        "kapak": kapak_dosya,
        "icerik_1": icerik1_dosya,
        "icerik_2": icerik2_dosya
    }
    with open(f"{hash_id}_gorseller.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=4)
    
    print(f"\n✅ Tüm görsel işlemleri tamamlandı. Metadata: {hash_id}_gorseller.json")

if __name__ == "__main__":
    visual_factory()
