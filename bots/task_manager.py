import os
import sys
import json
from datetime import datetime

def get_next_task_id(tasks):
    """Mevcut task'lerden en büyük task_id'yi bul, +1 yap"""
    max_id = 0
    for task in tasks:
        tid = task.get('task_id', '0000')
        if tid.isdigit():
            max_id = max(max_id, int(tid))
    return str(max_id + 1).zfill(4)

def parse_task_file(filepath):
    """new_task.txt dosyasını oku, dict haline getir"""
    if not os.path.exists(filepath):
        print(f"❌ {filepath} bulunamadı!")
        return None
    
    task_data = {}
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if ':' in line:
                key, value = line.split(':', 1)
                task_data[key.strip()] = value.strip()
    
    # Gerekli alanlar var mı kontrol et
    required = ['topic', 'category']
    for req in required:
        if req not in task_data:
            print(f"❌ {req} alanı eksik!")
            return None
    
    return task_data

def add_task():
    """Yeni task'i tasks.json'a ekler"""
    
    if not os.path.exists("tasks.json"):
        print("❌ tasks.json bulunamadı!")
        return
    
    with open("tasks.json", "r", encoding="utf-8") as f:
        tasks = json.load(f)
    
    # Yeni task_id oluştur
    new_id = get_next_task_id(tasks)
    
    # new_task.txt'den verileri oku
    task_data = parse_task_file("new_task.txt")
    if not task_data:
        return
    
    # ISO formatında bugünün tarihi
    today_iso = datetime.now().strftime("%Y-%m-%d")
    today_display = datetime.now().strftime("%d %B %Y")
    
    # Yeni task objesini oluştur
    new_task = {
        "task_id": new_id,
        "category": task_data.get('category', 'general'),
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
        "created_at": today_iso,           # ISO formatı "2026-04-11"
        "date": today_iso,                 # ✅ Creator'ın beklediği alan (ISO)
        "display_date": today_display,     # Görüntüleme için "11 April 2026"
        "processed_at": ""
    }
    
    # tasks.json'a ekle
    tasks.append(new_task)
    
    with open("tasks.json", "w", encoding="utf-8") as f:
        json.dump(tasks, f, indent=4, ensure_ascii=False)
    
    print(f"✅ Yeni task eklendi: ID {new_id} - {new_task['topic']}")
    print(f"   📅 Tarih (ISO): {today_iso}")
    print(f"   📅 Tarih (görüntüleme): {today_display}")
    print(f"📋 Toplam task sayısı: {len(tasks)}")

if __name__ == "__main__":
    add_task()
