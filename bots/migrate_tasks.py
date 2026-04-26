#!/usr/bin/env python3
"""
MIGRATE TASKS - TEK SEFERLİK ÇALIŞTIRILACAK
Konum: bots/migrate_tasks.py
"""

import json
import os
import shutil
from datetime import datetime

def main():
    print("=" * 60)
    print("🔄 MIGRATE TASKS - TEK SEFERLİK")
    print("   tasks.json → task/ klasörüne ayrıştırma")
    print("=" * 60)
    
    # Ana dizine git (bots/ altından çık)
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(base_dir)
    print(f"📁 Çalışma dizini: {os.getcwd()}")
    
    # 1. YEDEK AL
    if os.path.exists("tasks.json"):
        backup_name = f"tasks.json.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        shutil.copy("tasks.json", backup_name)
        print(f"✅ Yedek alındı: {backup_name}")
    else:
        print("❌ tasks.json bulunamadı!")
        return
    
    # 2. task/ KLASÖRÜNÜ OLUŞTUR
    os.makedirs("task", exist_ok=True)
    print("✅ task/ klasörü oluşturuldu")
    
    # 3. MEVCUT TASKS.JSON'U OKU
    with open("tasks.json", "r", encoding="utf-8") as f:
        all_tasks = json.load(f)
    
    print(f"📊 Toplam task: {len(all_tasks)}")
    
    # 4. AYRIŞTIR
    pending = []
    processed = []
    skipped = []
    
    for task in all_tasks:
        status = task.get("status")
        hash_id = task.get("hash")
        
        if status == "processed":
            processed.append(task)
        elif status == "skipped":
            skipped.append(task)
        elif status == "pending":
            if hash_id:
                print(f"   ⚠️ Task {task.get('task_id')}: hash={hash_id} var ama pending → skipped")
                skipped.append(task)
            else:
                pending.append(task)
        else:
            if hash_id:
                processed.append(task)
            else:
                pending.append(task)
    
    # 5. DOSYALARA YAZ
    with open("task/tasks.json", "w", encoding="utf-8") as f:
        json.dump(pending, f, indent=4, ensure_ascii=False)
    
    with open("task/processed.json", "w", encoding="utf-8") as f:
        json.dump(processed, f, indent=4, ensure_ascii=False)
    
    with open("task/skipped.json", "w", encoding="utf-8") as f:
        json.dump(skipped, f, indent=4, ensure_ascii=False)
    
    # 6. RAPOR
    print("\n" + "=" * 40)
    print("📊 MIGRATION RAPORU:")
    print(f"   ✅ Pending (işlenecek): {len(pending)}")
    print(f"   ✅ Processed (tamam): {len(processed)}")
    print(f"   ⚠️ Skipped (hatalı): {len(skipped)}")
    print("=" * 40)
    print("\n📁 Dosyalar:")
    print("   task/tasks.json")
    print("   task/processed.json")
    print("   task/skipped.json")
    print("\n⚠️ Mevcut tasks.json DEĞİŞTİRİLMEDİ (yedek alındı)")
    print("=" * 60)

if __name__ == "__main__":
    main()
