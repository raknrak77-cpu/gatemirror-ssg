import os
import json
import re
from datetime import datetime

# ================= CLUSTER EŞLEME SÖZLÜĞÜ =================
# new_task.txt'deki "cluster:" satırını cluster_id'ye çevirir
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

# Tersine eşleme (id -> name) opsiyonel
CLUSTER_ID_TO_NAME = {v: k for k, v in CLUSTER_NAME_TO_ID.items()}

def resolve_cluster_id(cluster_input):
    """
    new_task.txt'den gelen cluster satırını cluster_id'ye çevirir.
    - Eğer doğrudan cluster_id (wl_01) gelirse onu döndürür
    - Eğer cluster adı (longevity_biohacking) gelirse eşleşen id'yi döndürür
    - Bulunamazsa None döndürür
    """
    if not cluster_input:
        return None
    
    cluster_input = cluster_input.strip().lower()
    
    # Eğer zaten cluster_id formatındaysa (örnek: wl_01, tech_03)
    if re.match(r'^[a-z]+_[0-9]+$', cluster_input):
        return cluster_input
    
    # Eşleme sözlüğünden ara
    if cluster_input in CLUSTER_NAME_TO_ID:
        return CLUSTER_NAME_TO_ID[cluster_input]
    
    # Bulunamadı
    print(f"⚠️ Uyarı: '{cluster_input}' için cluster_id bulunamadı.")
    return None

def get_next_task_id(tasks):
    """Mevcut task'lerden en büyük task_id'yi bul, +1 yap"""
    max_id = 0
    for task in tasks:
        tid = task.get('task_id', '0000')
        if tid.isdigit():
            max_id = max(max_id, int(tid))
    return str(max_id + 1).zfill(4)

def parse_task_block(block):
    """Tek bir task bloğunu dict haline getirir"""
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
    """new_task.txt dosyasındaki TÜM task'ları okur, liste halinde döndürür"""
    if not os.path.exists(filepath):
        print(f"❌ {filepath} bulunamadı!")
        return []
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Task'ları ayır: her task bir category: ile başlar
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

def add_tasks():
    """Yeni task'leri tasks.json'a ekler (toplu)"""
    
    # tasks.json yoksa oluştur
    if not os.path.exists("tasks.json"):
        print("⚠️ tasks.json bulunamadı, yeni dosya oluşturuluyor...")
        with open("tasks.json", "w", encoding="utf-8") as f:
            json.dump([], f)
    
    with open("tasks.json", "r", encoding="utf-8") as f:
        tasks = json.load(f)
    
    # new_task.txt'den TÜM task'ları oku
    all_task_data = parse_all_tasks("new_task.txt")
    if not all_task_data:
        print("❌ Hiç task bulunamadı! new_task.txt dosyasını kontrol et.")
        return
    
    print(f"📋 {len(all_task_data)} task bulundu, ekleniyor...")
    
    today_iso = datetime.now().strftime("%Y-%m-%d")
    today_display = datetime.now().strftime("%d %B %Y")
    
    added_count = 0
    for task_data in all_task_data:
        new_id = get_next_task_id(tasks)
        category = task_data.get('category', 'general')
        
        # 🔥 YENİ: cluster adını veya id'sini al, cluster_id'ye çevir
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
            "created_at": today_iso,
            "date": today_iso,
            "display_date": today_display,
            "processed_at": ""
        }
        
        tasks.append(new_task)
        cluster_info = f" (cluster: {cluster_id})" if cluster_id else " (cluster: yok)"
        print(f"   ✅ Task eklendi: ID {new_id} - {new_task['topic'][:50]}...{cluster_info}")
        added_count += 1
    
    with open("tasks.json", "w", encoding="utf-8") as f:
        json.dump(tasks, f, indent=4, ensure_ascii=False)
    
    print(f"\n✅ Toplam {added_count} task eklendi!")
    print(f"📋 Toplam task sayısı: {len(tasks)}")

if __name__ == "__main__":
    add_tasks()
