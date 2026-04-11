import os
import sys
import json
import time
import uuid
import re
import requests
import subprocess
from datetime import datetime

GEMINI_KEY = os.getenv('GEMINI_API_KEY')
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={GEMINI_KEY}"

def create_hash():
    return uuid.uuid4().hex[:8]

def create_slug(text):
    slug = text.lower()
    slug = re.sub(r'[^a-z0-9]+', '-', slug)
    slug = slug.strip('-')
    slug = re.sub(r'-+', '-', slug)
    return slug[:60]

def html_yaz(hash_id, task, makale_html, kategori, lang, yil, ay, slug):
    author = task.get('author_persona', 'Expert Analyst')
    datetime_full = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    meta_comment = f"<!-- META: author={author}, datetime={datetime_full} -->\n"
    final_html = meta_comment + makale_html
    
    target_dir = os.path.join("content", lang, kategori, yil, ay)
    os.makedirs(target_dir, exist_ok=True)
    filename = f"{hash_id}-{slug}.html"
    target_path = os.path.join(target_dir, filename)
    
    with open(target_path, 'w', encoding='utf-8') as f:
        f.write(final_html)
    print(f"✅ {lang.upper()} HTML kaydedildi: {target_path}")
    return target_path

def isle_gorev(task):
    task_id = task.get('task_id', '0000')
    topic = task['topic']
    persona = task.get('author_persona', 'Expert Analyst')
    special_instructions = task.get('special_instructions', '')
    reference_link = task.get('reference_link', '')
    kategori = task.get('category', 'general').lower()
    
    print(f"🚀 HEDEF: {topic} (ID: {task_id})")
    print("🤖 Gemini'den 4 dilde (EN, ES, DE, FR) yanıt bekleniyor...")
    
    prompt_emri = f"""
ROLE: You are an expert {persona}.

TASK: Write the SAME comprehensive, deep-dive article in FOUR languages: English (en), Spanish (es), German (de), French (fr).

TOPIC: '{topic}'

REQUIREMENTS FOR EACH LANGUAGE:
- Length: Minimum 1500 words, maximum 2500 words per language.
- Use ONLY HTML tags: <h1>, <h2>, <h3>, <p>, <ul>, <li>, <strong>, <em>, <div>.
- DO NOT use Markdown.
- Start directly with the first HTML tag for each language.
- Write in a professional, analytical, yet engaging tone.
- Include real-world examples, data points, and case studies.
- Add a strong conclusion.

{f"REFERENCE: Use this as source material - {reference_link}" if reference_link else ""}

{f"SPECIAL INSTRUCTIONS: {special_instructions}" if special_instructions else ""}

**REQUIRED SECTIONS (in this exact order) for EACH language:**

1. <h1>Title (translated appropriately)</h1>
2. <div class="editors-note">Editor's Note: ... (2-3 sentences, first-person singular, translated)</div>
3. <h2>Introduction</h2>
4. <h2>Key Takeaways</h2>
   <ul><li>Takeaway 1</li><li>Takeaway 2</li><li>Takeaway 3 (max 5 items)</li></ul>
5. <h2>Main Analysis</h2>
6. <h2>Conclusion</h2>
7. <div class="sources"><h3>Sources</h3><ul><li>Source 1</li><li>Source 2</li><li>Source 3</li></ul></div>

OUTPUT FORMAT:
Start with English version, then Spanish, then German, then French.
Separate each language with a marker line exactly like this:
<!-- LANG:EN -->
... English HTML ...
<!-- LANG:ES -->
... Spanish HTML ...
<!-- LANG:DE -->
... German HTML ...
<!-- LANG:FR -->
... French HTML ...

IMPORTANT:
- Do NOT add any extra explanations.
- Keep HTML structure identical across languages.
"""
    
    payload = {
        "contents": [{"parts": [{"text": prompt_emri}]}],
        "generationConfig": {"temperature": 0.7, "maxOutputTokens": 20000, "topP": 0.95}
    }
    
    try:
        response = requests.post(GEMINI_URL, json=payload, timeout=240)
        res_data = response.json()
        
        if 'candidates' in res_data and len(res_data['candidates']) > 0:
            full_response = res_data['candidates'][0]['content']['parts'][0]['text']
            print(f"✅ Yanıt alındı: {len(full_response)} karakter")
            
            parts = re.split(r'<!-- LANG:(EN|ES|DE|FR) -->', full_response)
            lang_html = {}
            for i in range(1, len(parts), 2):
                lang_code = parts[i].lower()
                html_content = parts[i+1].strip()
                html_content = html_content.replace('```html', '').replace('```', '')
                lang_html[lang_code] = html_content
            
            hash_id = create_hash()
            print(f"🔑 Üretilen hash: {hash_id} (Task ID: {task_id})")
            
            now = datetime.now()
            yil = now.strftime("%Y")
            ay = now.strftime("%m")
            slug = create_slug(topic)
            
            # Görsel bot tek sefer çağrılır (dilden bağımsız)
            visuals = task.get('visuals', {})
            if visuals:
                print("🎨 Görsel bot çağrılıyor...")
                try:
                    visuals_json = json.dumps(visuals)
                    subprocess.run(
                        ['python', 'bots/visual_factory.py', task_id, hash_id, visuals_json, kategori, yil, ay],
                        timeout=180, check=False
                    )
                    print("✅ Görsel bot tamamlandı.")
                except Exception as e:
                    print(f"⚠️ Görsel bot hatası: {e}")
            
            # Her dil için HTML kaydet
            for lang, html in lang_html.items():
                html_yaz(hash_id, task, html, kategori, lang, yil, ay, slug)
            
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
    print("🛰️ Creator Bot (4 Dil Tek Prompt) başlatılıyor...")
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
            with open("tasks.json", "w", encoding="utf-8") as f:
                json.dump(tasks, f, indent=4, ensure_ascii=False)
            sys.exit(1)
        with open("tasks.json", "w", encoding="utf-8") as f:
            json.dump(tasks, f, indent=4, ensure_ascii=False)
        if i < len(pending_tasks) - 1:
            print("⏳ 10 saniye bekleniyor...")
            time.sleep(10)
    print("\n🏁 Tüm görevler tamamlandı.")

if __name__ == "__main__":
    operasyon_baslat()
