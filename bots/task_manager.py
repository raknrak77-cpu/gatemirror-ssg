import os
import json
import re
from datetime import datetime

# ================= CLUSTER EŞLEME SÖZLÜĞÜ (clusters.json'dan otomatik) =================
# Not: Bu sözlük clusters.json'dan sync edilmelidir.
# Manuel senkronizasyon için aşağıdaki yapı clusters.json version 3.1 baz alınarak oluşturulmuştur.

CLUSTER_NAME_TO_ID = {
    # TECH (7 cluster)
    "ai_trading_bots": "tech_01",
    "cybersecurity_ai": "tech_02",
    "ai_productivity_tools": "tech_03",
    "cloud_computing_ai": "tech_04",
    "generative_search": "tech_05",
    "quantum_computing_trends": "tech_06",
    "wearable_tech_2026": "tech_07",
    
    # FUTURE-ECONOMY (9 cluster)
    "crypto_exchanges": "fe_01",
    "rwa_tokenization": "fe_02",
    "digital_banking": "fe_03",
    "defi_staking": "fe_04",
    "wealth_management": "fe_05",
    "depin_networks": "fe_06",
    "cbdc": "fe_07",
    "gig_economy_3_0": "fe_08",
    "impact_investing_esg": "fe_09",
    
    # WELLNESS (7 cluster)
    "longevity_biohacking": "wl_01",
    "mental_health_apps": "wl_02",
    "telemedicine_tech": "wl_03",
    "sleep_optimization": "wl_04",
    "personalized_nutrition": "wl_05",
    "holistic_biohacking": "wl_06",
    "regenerative_fitness": "wl_07",
    
    # ELEARNING (10 cluster)
    "coding_bootcamps": "el_01",
    "exec_education": "el_02",
    "language_apps": "el_03",
    "cloud_certifications": "el_04",
    "sidehustle_skills": "el_05",
    "corporate_ar_training": "el_06",
    "adaptive_lms_ai": "el_07",
    "vr_ar_classrooms": "el_08",
    "skill_based_nanodegrees": "el_09",
    "ai_tutors_personalized": "el_10",
    
    # ECO (9 cluster)
    "ev_infrastructure": "eco_01",
    "solar_energy": "eco_02",
    "climate_finance": "eco_03",
    "smart_home_energy": "eco_04",
    "circular_economy": "eco_05",
    "ocean_cleanup_tech": "eco_06",
    "regenerative_agriculture": "eco_07",
    "green_hydrogen": "eco_08",
    "sustainable_fashion": "eco_09",
    
    # ALIASLAR (eski task'ler için uyumluluk)
    "longevity_protocols": "wl_01",
    "personalized_nutrition_ai": "wl_05",
    "mental_health_tech": "wl_02",
    "de_pin_networks": "fe_06",
    "central_bank_digital_currencies": "fe_07",
    "gig_economy_3_0": "fe_08",
    "quantum_computing_trends": "tech_06",
    "wearable_tech_2026": "tech_07",
    "impact_investing_esg": "fe_09",
    "regenerative_agriculture": "eco_07",
    "green_hydrogen_energy": "eco_08",
    "sustainable_fashion_innovation": "eco_09",
    "vr_ar_classrooms": "el_08",
    "skill_based_nanodegrees": "el_09",
    "ai_tutors_personalized_learning": "el_10"
}

CLUSTER_ID_TO_NAME = {v: k for k, v in CLUSTER_NAME_TO_ID.items()}

def resolve_cluster_id(cluster_input):
    if not cluster_input:
        return None
    cluster_input = cluster_input.strip().lower()
    # Eğer zaten cluster_id formatındaysa (örn: tech_01)
    if re.match(r'^[a-z]+_[0-9]+$', cluster_input):
        return cluster_input
    # Sözlükten bul
    if cluster_input in CLUSTER_NAME_TO_ID:
        return CLUSTER_NAME_TO_ID[cluster_input]
    print(f"⚠️ Uyarı: '{cluster_input}' için cluster_id bulunamadı. (Lütfen CLUSTER_NAME_TO_ID sözlüğünü kontrol edin)")
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
            key = parts[0].strip().lower()
            # Key'i temizle (sadece alfanumeric ve underscore)
            key = re.sub(r'[^a-z0-9_]', '', key)
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
    
    # YENİ: task/new_task.txt dosyasını oku
    new_task_path = "task/new_task.txt"
    if not os.path.exists(new_task_path):
        print(f"❌ {new_task_path} bulunamadı! Önce task/new_task.txt dosyasını oluşturun.")
        print("   Örnek format:\n")
        print("""category: tech
cluster: ai_trading_bots
topic: AI Trading Bots 2026
reference_link: https://example.com
author_persona: Expert
special_instructions: Write content...
kapak_prompt: A high-tech trading screen...
icerik_1_prompt: A dashboard showing...
icerik_2_prompt: A mobile app interface...
""")
        return
    
    all_task_data = parse_all_tasks(new_task_path)
    if not all_task_data:
        print("❌ Hiç task bulunamadı! task/new_task.txt dosyasını kontrol et.")
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
        
        # Görseller: direkt string olarak al, width/height kaldırıldı
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
                "kapak": task_data.get('kapak_prompt', task_data['topic']),
                "icerik_1": task_data.get('icerik_1_prompt', task_data['topic']),
                "icerik_2": task_data.get('icerik_2_prompt', task_data['topic'])
            },
            "status": "pending",
            "hash": None,
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
    
    # İsteğe bağlı: new_task.txt'yi temizle (backup al)
    if added_count > 0:
        backup_path = f"task/new_task_backup_{today_iso}.txt"
        with open(new_task_path, "r", encoding="utf-8") as f_src:
            with open(backup_path, "w", encoding="utf-8") as f_dst:
                f_dst.write(f_src.read())
        print(f"📦 Yeni task'lerin yedeği alındı: {backup_path}")
        
        # new_task.txt'yi temizle (opsiyonel - yorum satırı yapıldı)
        # with open(new_task_path, "w", encoding="utf-8") as f:
        #     f.write("# Task dosyası temizlendi. Yeni task'ler için buraya ekleme yapın.\n")

if __name__ == "__main__":
    add_tasks()
