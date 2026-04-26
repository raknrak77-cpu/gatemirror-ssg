#!/usr/bin/env python3
"""
MIGRATE TASKS - TEK SEFERLİK ÇALIŞTIRILACAK
Mevcut tasks.json'u task/ klasörüne ayrıştırır.
Ana dizindeki tasks.json'a DOKUNMAZ (yedek alır).
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
    
    # 1. YEDEK AL
    if os.path.exists("tasks.json"):
        backup_name = f"tasks.json.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        shutil.copy("tasks.json", backup_name)
        print(f"✅ Yedek alındı: {backup_name}")
    else:
        print("❌ tasks.json bulunamadı!")
        sys.exit(1)
    
    # 2. task/ KLASÖRÜNÜ OLUŞTUR
    os.makedirs("task", exist_ok=True)
    print("✅ task/ klasörü oluşturuldu")
    
    # 3. MEVCUT TASKS.JSON'U OKU
    with open("tasks.json", "r", encoding="utf-8") as f:
        all_tasks = json.load(f)
    
    print(f"📊 Toplam task: {len(all_tasks)}")
    
    # 4. AYRIŞTIR
    pending = []      # hash'siz + status pending
    processed = []    # status processed veya hash var + uploaded
    skipped = []      # status skipped veya hash var + pending (hatalı)
    
    for task in all_tasks:
        status = task.get("status")
        hash_id = task.get("hash")
        
        # Processed olanlar
        if status == "processed":
            processed.append(task)
            continue
        
        # Skipped olanlar
        if status == "skipped":
            skipped.append(task)
            continue
        
        # Pending olanlar
        if status == "pending":
            if hash_id:
                # Hash var ama pending = hatalı üretim
                print(f"   ⚠️ Task {task.get('task_id')}: hash={hash_id} var ama pending → skipped")
                skipped.append(task)
            else:
                pending.append(task)
            continue
        
        # Diğer status'ler (hash_created, uploaded, etc.)
        if hash_id:
            # Bunlar aslında tamamlanmış sayılır
            print(f"   📝 Task {task.get('task_id')}: status={status}, hash={hash_id} → processed")
            processed.append(task)
        else:
            print(f"   ⚠️ Task {task.get('task_id')}: status={status}, hash yok → pending")
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
