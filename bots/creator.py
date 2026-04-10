import os
import sys
import json
import time
import uuid
import requests
import subprocess
from datetime import datetime

# API Key
GEMINI_KEY = os.getenv('GEMINI_API_KEY')
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={GEMINI_KEY}"

def create_hash():
    """Benzersiz 8 karakterli hash üretir (UUID'nin ilk 8 karakteri)"""
    return uuid.uuid4().hex[:8]

def markdown_yaz(hash_id, task, makale_html, kategori):
    """Markdown dosyasını content/en/{kategori}/{hash}.md olarak oluşturur"""
    
    topic = task['topic']
    date = task.get('display_date', datetime.now().strftime("%d %B %Y"))
    author = task.get('author_persona', 'Expert Analyst')
    
    summary_lines = ["  - Topic: " + topic, "  - Analysis: High-Fidelity"]
    summary_yaml = "\n".join(summary_lines)
    sources = task.get('reference_link', '')
    
    frontmatter = f"""---
title: "{topic}"
date: "{date}"
hash: "{hash_id}"
task_id: "{task.get('task_id')}"
category: "{kategori}"
author: "{author}"
summary: |
{summary_yaml}
sources: 
  - {sources}
---

![kapak](./assets/{hash_id}_kapak.png)

{makale_html}

![icerik_1](./assets/{hash_id}_icerik_1.png)

![icerik_2](./assets/{hash_id}_icerik_2.png)
"""
    
    md_dir = f"content/en/{kategori}"
    os.makedirs(md_dir, exist_ok=True)
    md_path = os.path.join(md_dir, f"{hash_id}.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(frontmatter)
    
    print(f"✅ Markdown kaydedildi: {md_path}")
    return md_path

def isle_gorev(task):
    """Tek bir görevi işler: makale üretir, görsel bot'u çağırır, .md yazar"""
    
    task_id = task.get('task_id', '0000')
    topic = task['topic']
    language = task.get('language', 'en')
    persona = task.get('author_persona', 'Expert Analyst')
    special_instructions = task.get('special_instructions', '')
    reference_link = task.get('reference_link', '')
    kategori = task.get('category', 'general').lower()
    
    print(f"🚀 HEDEF: {topic} (ID: {task_id})")
    print("🤖 Gemini'den yanıt bekleniyor (120sn limit)...")
    
    # GÜÇLENDİRİLMİŞ PROMPT
    prompt_emri = f"""
ROLE: You are an expert {persona}.

TASK: Write a comprehensive, deep-dive article in {language} about: '{topic}'.

REQUIREMENTS:
- Length: Minimum 1500 words, maximum 2500 words.
- Use ONLY HTML tags: <h2>, <h3>, <p>, <ul>, <li>, <strong>, <em>.
- DO NOT use Markdown (no **bold**, no ## headings).
- Start directly with the first HTML tag (no introductions).
- Write in a professional, analytical, yet engaging tone.
- Include real-world examples, data points, and case studies where relevant.
- Use short paragraphs (2-3 sentences) for better readability.
- Add a strong conclusion that summarizes key takeaways.

{f"REFERENCE: Use this as source material - {reference_link}" if reference_link else ""}

{f"SPECIAL INSTRUCTIONS: {special_instructions}" if special_instructions else ""}

OUTPUT FORMAT (start directly with HTML):
<h2>Introduction</h2>
<p>...</p>
<h3>Subheading</h3>
<p>...</p>
<ul><li>...</li></ul>
<h2>Conclusion</h2>
<p>...</p>
"""
    
    payload = {
        "contents": [{"parts": [{"text": prompt_emri}]}],
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 6000,
            "topP": 0.95
        }
    }
    
    try:
        response = requests.post(GEMINI_URL, json=payload, timeout=120)
        res_data = response.json()
        
        if 'candidates' in res_data and len(res_data['candidates']) > 0:
            makale_html = res_data['candidates'][0]['content']['parts'][0]['text']
            makale_html = makale_html.replace('```html', '').replace('```', '').replace('\n', '<br>')
            print(f"✅ Makale alındı: {len(makale_html)} karakter.")
            
            # BAŞARILI OLUNCA HASH ÜRET
            hash_id = create_hash()
            print(f"🔑 Üretilen hash: {hash_id} (Task ID: {task_id})")
            
            # Görsel bot'u çağır
            visuals = task.get('visuals', {})
            if visuals:
                print("🎨 Görsel bot çağrılıyor (visual_factory.py)...")
                try:
                    visuals_json = json.dumps(visuals)
                    subprocess.run(['python', 'bots/visual_factory.py', task_id, hash_id, visuals_json], timeout=180)
                    print("✅ Görsel bot tamamlandı.")
                except subprocess.TimeoutExpired:
                    print("⚠️ Görsel bot zaman aşımı, görseller olmadan devam...")
                except Exception as e:
                    print(f"⚠️ Görsel bot hatası: {e}")
            else:
                print("⚠️ Görsel açıklaması yok, görseller atlanıyor.")
            
            # Markdown dosyasını oluştur
            md_path = markdown_yaz(hash_id, task, makale_html, kategori)
            
            # Görevi güncelle (SADECE BAŞARILI OLUNCA)
            task["status"] = "processed"
            task["processed_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            task["hash"] = hash_id
            
            return True, hash_id
        else:
            print(f"❌ GEMINI HATASI: {json.dumps(res_data, indent=2)}")
            return False, None
    except Exception as e:
        print(f"❌ SİSTEM HATASI: {str(e)}")
        return False, None

def operasyon_baslat():
    print("🛰️ Creator Bot başlatılıyor...")
    
    if not os.path.exists("tasks.json"):
        print("❌ tasks.json bulunamadı!")
        sys.exit(1)
    
    with open("tasks.json", "r", encoding="utf-8") as f:
        tasks = json.load(f)
    
    pending_tasks = [t for t in tasks if t.get("status") == "pending"]
    
    if not pending_tasks:
        print("💤 Bekleyen görev yok.")
        return
    
    print(f"📋 Toplam {len(pending_tasks)} görev bulundu.")
    
    for i, task in enumerate(pending_tasks):
        print(f"\n--- Görev {i+1}/{len(pending_tasks)} (ID: {task.get('task_id')}) ---")
        basarili, hash_id = isle_gorev(task)
        
        if not basarili:
            print(f"❌ Görev {task.get('task_id')} başarısız, workflow durduruluyor.")
            task["status"] = "failed"
            task["error"] = "API hatası veya zaman aşımı"
            task["hash"] = None
            task["processed_at"] = ""
            with open("tasks.json", "w", encoding="utf-8") as f:
                json.dump(tasks, f, indent=4, ensure_ascii=False)
            sys.exit(1)
        
        # tasks.json'u güncelle
        with open("tasks.json", "w", encoding="utf-8") as f:
            json.dump(tasks, f, indent=4, ensure_ascii=False)
        
        if i < len(pending_tasks) - 1:
            print("⏳ 10 saniye bekleniyor...")
            time.sleep(10)
    
    print("\n🏁 Tüm görevler tamamlandı.")

if __name__ == "__main__":
    operasyon_baslat()
