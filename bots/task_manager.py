import os
import json
import re
from datetime import datetime

# ================= CLUSTER EŞLEME SÖZLÜĞÜ =================
CLUSTER_NAME_TO_ID = {
    # TECH
    "ai_trading_bots": "tech_01",
    "cybersecurity_ai": "tech_02",
    "ai_productivity_tools": "tech_03",
    "cloud_computing_ai": "tech_04",
    "generative_search": "tech_05",
    # FUTURE-ECONOMY
    "crypto_exchanges": "fe_01",
    "rwa_tokenization": "fe_02",
    "digital_banking": "fe_03",
    "defi_staking": "fe_04",
    "wealth_management": "fe_05",
    # WELLNESS
    "longevity_biohacking": "wl_01",
    "mental_health_apps": "wl_02",
    "telemedicine_tech": "wl_03",
    "sleep_optimization": "wl_04",
    "personalized_nutrition": "wl_05",
    # ELEARNING
    "coding_bootcamps": "el_01",
    "exec_education": "el_02",
    "language_apps": "el_03",
    "cloud_certifications": "el_04",
    "sidehustle_skills": "el_05",
    # ECO
    "ev_infrastructure": "eco_01",
    "solar_energy": "eco_02",
    "climate_finance": "eco_03",
    "smart_home_energy": "eco_04",
    "circular_economy": "eco_05"
}

CLUSTER_ID_TO_NAME = {v: k for k, v in CLUSTER_NAME_TO_ID.items()}

def resolve_cluster_id(cluster_input):
    if not cluster_input:
        return None
    cluster_input = cluster_input.strip().lower()
    if re.match(r'^[a-z]+_[0-9]+$', cluster_input):
        return cluster_input
    if cluster_input in CLUSTER_NAME_TO_ID:
        return CLUSTER_NAME_TO_ID[cluster_input]
    print(f"⚠️ Uyarı: '{cluster_input}' için cluster_id bulunamadı.")
    return None

def get_next_task_id(pending_tasks, processed_tasks):
    """pending ve processed task'lerden en büyük task_id'yi bul, +1 yap"""
    max_id = 0
    
    for task in pending_tasks:
        tid = task.get('task_id', '0000')
        if tid.isdigit():
            max_id = max(max_id, int(tid))
    
    for task in processed_tasks:
        tid = task.get('task_id', '0000')
        if tid.isdigit():
            max_id = max(max_id, int(tid))
    
    return str(max_id + 1).zfill(4)

def parse_task_block(block):
    task_data = {}
    for line in block.split('\n'):
        line = line.strip()
        if not line:
            continue
        if ':' in line:
            parts = line.split(':', 1)
            key = re.sub(r'[^a-z0-9_]', '', parts[0].strip().lower())
            value = parts[1].strip()
            task_data[key] = value
    return task_data

def parse_all_tasks(filepath):
    if not os.path.exists(filepath):
        print(f"❌ {filepath} bulunamadı!")
        return []
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    blocks = []
    current_block = []
    lines = content.split('\n')
    
    for line in lines:
        line_stripped = line.strip()
        if line_stripped.startswith('category:'):
            if current_block:
                blocks.append('\n'.join(current_block))
            current_block = [line]
        elif current_block:
            current_block.append(line)
    
    if current_block:
        blocks.append('\n'.join(current_block))
    
    tasks_data = []
    for block in blocks:
        task_data = parse_task_block(block)
        if task_data.get('topic') and task_data.get('category'):
            tasks_data.append(task_data)
        else:
            print(f"⚠️ Eksik task bloğu atlandı (topic veya category yok)")
    
    return tasks_data

def load_existing_ids(pending_tasks, processed_tasks):
    """Mevcut task_id'lerin set'ini döndürür"""
    existing_ids = set()
    for task in pending_tasks:
        existing_ids.add(task.get('task_id'))
    for task in processed_tasks:
        existing_ids.add(task.get('task_id'))
    return existing_ids

def add_tasks():
    """Yeni task'leri task/tasks.json'a ekler (toplu)"""
    
    # task/ klasörünü kontrol et
    if not os.path.exists("task"):
        os.makedirs("task", exist_ok=True)
        print("✅ task/ klasörü oluşturuldu")
    
    # Pending task'leri yükle
    pending_path = "task/tasks.json"
    if not os.path.exists(pending_path):
        with open(pending_path, "w", encoding="utf-8") as f:
            json.dump([], f)
        print("⚠️ task/tasks.json yoktu, yeni dosya oluşturuldu")
    
    with open(pending_path, "r", encoding="utf-8") as f:
        pending_tasks = json.load(f)
    
    # Processed task'leri yükle
    processed_path = "task/processed.json"
    if not os.path.exists(processed_path):
        with open(processed_path, "w", encoding="utf-8") as f:
            json.dump([], f)
        print("⚠️ task/processed.json yoktu, yeni dosya oluşturuldu")
    
    with open(processed_path, "r", encoding="utf-8") as f:
        processed_tasks = json.load(f)
    
    # Skipped task'leri de kontrol et (opsiyonel)
    skipped_path = "task/skipped.json"
    if os.path.exists(skipped_path):
        with open(skipped_path, "r", encoding="utf-8") as f:
            skipped_tasks = json.load(f)
    else:
        skipped_tasks = []
    
    # new_task.txt'den TÜM task'ları oku
    all_task_data = parse_all_tasks("new_task.txt")
    if not all_task_data:
        print("❌ Hiç task bulunamadı! new_task.txt dosyasını kontrol et.")
        return
    
    # Mevcut task_id'leri topla
    existing_ids = load_existing_ids(pending_tasks, processed_tasks)
    for task in skipped_tasks:
        existing_ids.add(task.get('task_id'))
    
    print(f"📋 {len(all_task_data)} task bulundu, ekleniyor...")
    print(f"📊 Mevcut task_id'ler: {len(existing_ids)} adet")
    
    today_iso = datetime.now().strftime("%Y-%m-%d")
    today_display = datetime.now().strftime("%d %B %Y")
    
    added_count = 0
    duplicate_count = 0
    
    for task_data in all_task_data:
        # Önce new_task.txt'de task_id var mı kontrol et
        task_id_from_file = task_data.get('task_id', '')
        
        if task_id_from_file and task_id_from_file in existing_ids:
            print(f"   ⚠️ Task ID {task_id_from_file} zaten var, atlanıyor (topic: {task_data['topic'][:40]}...)")
            duplicate_count += 1
            continue
        
        # Yeni task_id oluştur
        if task_id_from_file:
            new_id = task_id_from_file
        else:
            new_id = get_next_task_id(pending_tasks, processed_tasks)
        
        category = task_data.get('category', 'general')
        cluster_input = task_data.get('cluster', '')
        cluster_id = resolve_cluster_id(cluster_input)
        
        new_task = {
            "task_id": new_id,
            "category": category,
            "cluster_id": cluster_id,
            "topic": task_data['topic'],
            "reference_link": task_data.get('reference_link', ''),
            "language": "en",
            "author_persona": task_data.get('author_persona', 'Expert Analyst'),
            "special_instructions": task_data.get('special_instructions', ''),
            "visuals": {
                "kapak": {
                    "prompt": task_data.get('kapak_prompt', task_data['topic']),
                    "width": 1024,
                    "height": 1024
                },
                "icerik_1": {
                    "prompt": task_data.get('icerik_1_prompt', task_data['topic']),
                    "width": 1024,
                    "height": 1024
                },
                "icerik_2": {
                    "prompt": task_data.get('icerik_2_prompt', task_data['topic']),
                    "width": 1024,
                    "height": 1024
                }
            },
            "status": "pending",
            "hash": None,  # Creator tarafından doldurulacak
            "created_at": today_iso,
            "date": today_iso,
            "display_date": today_display,
            "processed_at": ""
        }
        
        pending_tasks.append(new_task)
        existing_ids.add(new_id)
        cluster_info = f" (cluster: {cluster_id})" if cluster_id else " (cluster: yok)"
        print(f"   ✅ Task eklendi: ID {new_id} - {new_task['topic'][:50]}...{cluster_info}")
        added_count += 1
    
    # Değişiklikleri kaydet
    with open(pending_path, "w", encoding="utf-8") as f:
        json.dump(pending_tasks, f, indent=4, ensure_ascii=False)
    
    print(f"\n✅ Toplam {added_count} task eklendi! ( {duplicate_count} duplicate atlandı )")
    print(f"📋 Toplam pending task sayısı: {len(pending_tasks)}")
    print(f"📋 Toplam processed task sayısı: {len(processed_tasks)}")

if __name__ == "__main__":
    add_tasks()
