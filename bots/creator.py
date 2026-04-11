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

def html_yaz(hash_id, task, makale_html, kategori):
    """
    Ham HTML dosyasını content/ altına yazar.
    - makale_html zaten tam HTML içeriğidir (başlık dahil).
    - Yazar ve tarih bilgisini yorum satırı olarak ekler.
    """
    topic = task['topic']
    author = task.get('author_persona', 'Expert Analyst')
    date = task.get('display_date', datetime.now().strftime("%d %B %Y"))
    
    # Yorum satırı olarak meta bilgisi (builder tarafından okunabilir)
    meta_comment = f"<!-- META: author={author}, date={date} -->\n"
    
    # İçeriğe meta yorumunu en üste ekle (başlıktan önce)
    final_html = meta_comment + makale_html
    
    # Hedef dizin: content/en/{kategori}/{hash_id}.html
    target_dir = os.path.join("content", "en", kategori)
    os.makedirs(target_dir, exist_ok=True)
    target_path = os.path.join(target_dir, f"{hash_id}.html")
    
    with open(target_path, 'w', encoding='utf-8') as f:
        f.write(final_html)
    
    print(f"✅ Ham HTML kaydedildi: {target_path} (yazar: {author}, tarih: {date})")
    return target_path

def isle_gorev(task):
    """Tek bir görevi işler: makale üretir, görsel bot'u çağırır, ham HTML yazar"""
    
    task_id = task.get('task_id', '0000')
    topic = task['topic']
    language = task.get('language', 'en')
    persona = task.get('author_persona', 'Expert Analyst')
    special_instructions = task.get('special_instructions', '')
    reference_link = task.get('reference_link', '')
    kategori = task.get('category', 'general').lower()
    
    print(f"🚀 HEDEF: {topic} (ID: {task_id})")
    print("🤖 Gemini'den yanıt bekleniyor (120sn limit)...")
    
    prompt_emri = f"""
ROLE: You are an expert {persona}.

TASK: Write a comprehensive, deep-dive article in {language} about: '{topic}'.

REQUIREMENTS:
- Length: Minimum 1500 words, maximum 2500 words.
- Use ONLY HTML tags: <h1>, <h2>, <h3>, <p>, <ul>, <li>, <strong>, <em>, <div>.
- DO NOT use Markdown.
- Start directly with the first HTML tag.
- Write in a professional, analytical, yet engaging tone.
- Include real-world examples, data points, and case studies.
- Add a strong conclusion.

{f"REFERENCE: Use this as source material - {reference_link}" if reference_link else ""}

{f"SPECIAL INSTRUCTIONS: {special_instructions}" if special_instructions else ""}

**REQUIRED SECTIONS (in this exact order):**

1. <h1>Title</h1>
2. <div class="editors-note">Editor's Note: ... (2-3 sentences, first-person singular)</div>
3. <h2>Introduction</h2>
   ... content ...
4. <h2>Key Takeaways</h2>
   <ul>
     <li>Takeaway 1</li>
     <li>Takeaway 2</li>
     <li>Takeaway 3 (max 5 items)</li>
   </ul>
5. <h2>Main Analysis</h2>
   ... (subsections with <h3> if needed) ...
6. <h2>Conclusion</h2>
   ... summary and final thoughts ...
7. <div class="sources">
     <h3>Sources</h3>
     <ul>
       <li>Source 1 (with URL or description)</li>
       <li>Source 2</li>
       <li>Source 3 (minimum 3, maximum 5)</li>
     </ul>
   </div>

IMPORTANT:
- Do NOT add any extra <h1> or duplicate title.
- Do NOT add a separate author/date line (we will handle it via meta).
- Keep the structure clean and semantic.
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
            # Temizlik: code block'ları kaldır
            makale_html = makale_html.replace('```html', '').replace('```', '')
            # Yeni satırları koru (ama <br> ekleme, çünkü HTML tag'ler var)
            print(f"✅ Makale alındı: {len(makale_html)} karakter.")
            
            # Hash üret
            hash_id = create_hash()
            print(f"🔑 Üretilen hash: {hash_id} (Task ID: {task_id})")
            
            # Görsel bot'u çağır (2 iç görsel + kapak)
            visuals = task.get('visuals', {})
            if visuals:
                print("🎨 Görsel bot çağrılıyor (visual_factory.py)...")
                try:
                    visuals_json = json.dumps(visuals)
                    subprocess.run(
                        ['python', 'bots/visual_factory.py', task_id, hash_id, visuals_json, kategori],
                        timeout=180,
                        check=False
                    )
                    print("✅ Görsel bot tamamlandı.")
                except Exception as e:
                    print(f"⚠️ Görsel bot hatası: {e}")
            else:
                print("ℹ️ Bu görev için görsel prompt'u yok, atlanıyor.")
            
            # Ham HTML dosyasını oluştur
            html_path = html_yaz(hash_id, task, makale_html, kategori)
            
            # Görevi güncelle
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
