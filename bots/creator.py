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
    """Fallback slug üretici (topic'ten)"""
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
    print(f"✅ {lang.upper()} HTML kaydedildi: {target_path} (slug: {slug})")
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
ROLE: You are {persona} — a real expert with field experience, strong opinions, and a distinct editorial voice. You write for Gatemirror, a premium multi-language analysis platform read by professionals globally.

TASK: Write ONE article about '{topic}' in FOUR culturally adapted versions.
This is NOT a translation job. Each version must feel ORIGINALLY WRITTEN for that audience.

{f"REFERENCE MATERIAL: {reference_link}" if reference_link else ""}
{f"SPECIAL INSTRUCTIONS: {special_instructions}" if special_instructions else ""}

---

CULTURAL ADAPTATION RULES:
- EN: Global perspective, US/UK/Australian examples, data from Western institutions
- ES: Latin American OR Spanish context — use cities like Mexico City, Buenos Aires, Madrid; local brands and regional statistics
- DE: DACH region focus — Germany, Austria, Switzerland examples; European regulatory angle (EU, DACH market data)
- FR: French OR Francophone context — Paris, Montreal, Dakar where relevant; French institutional references

---

CONTENT REQUIREMENTS (per language):
- STRICT MINIMUM: 2000 words per language. MAXIMUM: 2500 words per language.
- Total output (4 languages combined) MUST exceed 56,000 characters.
- DO NOT stop before reaching 2000 words per language. Write MORE, not less.
- If you finish early, add more examples, case studies, or a deeper analysis section.
- Quality and quantity are BOTH required.
- Hook: ALWAYS start Introduction with a bold claim, surprising statistic, or provocative question — never a generic statement
- Tone: Analytical, opinionated, human — slightly varied rhythm and flow per language
- Include: Named companies, real case studies, specific data points, expert perspectives
- Avoid: "In today's rapidly evolving landscape", "It is worth noting", "In conclusion, it is clear that" — ban all AI filler phrases
- E-E-A-T: Write from genuine expertise — share opinions, challenge industry assumptions, make bold predictions

---

REQUIRED STRUCTURE (identical across all 4 languages):

<h1>[Title in target language]</h1>

<div class="editors-note">[2-3 sentences. First-person. Establish your credibility and why this topic is urgent RIGHT NOW. In target language.]</div>

<h2>Introduction</h2>
[Hook + problem + stakes + what reader will learn. Min 2 paragraphs.]

<h2>Key Takeaways</h2>
⚠️ CRITICAL: Write EXACTLY <h2>Key Takeaways</h2> — do NOT translate this heading in ANY language version
<ul>
  <li><strong>[Bold key concept]:</strong> [One sharp, specific sentence]</li>
  [3-5 items only]
</ul>

<h2>Main Analysis</h2>
[Minimum 4 subsections using <h3>. Structure each as: context → evidence → implication]

<h2>Practical Implications</h2>
[What should the reader DO? Concrete, actionable steps for their specific regional context]

<h2>Conclusion</h2>
[Synthesis + bold prediction for 2027-2028 + memorable closing line that sticks]

<div class="sources">
<h3>Sources</h3>
<ul>
  <li>[Real, verifiable source — institution name + actual URL. Min 3, max 5. NO fake links.]</li>
</ul>
</div>

---

SEO RULES:
- Naturally integrate topic keywords in <h1>, first paragraph, and 2-3 subheadings
- Use semantic variations — avoid exact keyword repetition
- Each language targets its own regional search intent

---

OUTPUT FORMAT (exact — no deviation):
<!-- LANG:EN -->
<!-- SLUG:[english-url-slug-here] -->
[Full EN HTML here]
<!-- LANG:ES -->
<!-- SLUG:[spanish-url-slug-here] -->
[Full ES HTML here]
<!-- LANG:DE -->
<!-- SLUG:[german-url-slug-here] -->
[Full DE HTML here]
<!-- LANG:FR -->
<!-- SLUG:[french-url-slug-here] -->
[Full FR HTML here]

SLUG RULES:
- Generate a URL-friendly slug for EACH language separately
- 5-8 words max, lowercase, use hyphens, no special characters, no accents
- Must be DIFFERENT for each language (culturally adapted to search intent)
- Example EN: "neurowellness-revolution", ES: "revolucion-neuro-bienestar"

---

STRICT RULES:
- "Key Takeaways" heading: NEVER translate, ALWAYS keep in English across ALL 4 languages
- <h1> title: NEVER repeat anywhere in body text
- Author/date: NEVER add
- Fake URLs: NEVER use — if unsure, cite institution name only
- Markdown/code blocks: NEVER use
- Explanations outside HTML blocks: NEVER add
"""
    
    payload = {
        "contents": [{"parts": [{"text": prompt_emri}]}],
        "generationConfig": {"temperature": 0.7, "maxOutputTokens": 28000, "topP": 0.95}
    }
    
    try:
        response = requests.post(GEMINI_URL, json=payload, timeout=420)
        res_data = response.json()
        
        if 'candidates' in res_data and len(res_data['candidates']) > 0:
            full_response = res_data['candidates'][0]['content']['parts'][0]['text']
            print(f"✅ Yanıt alındı: {len(full_response)} karakter")
            
            # Parse et: LANG ve SLUG'u birlikte al
            parts = re.split(r'<!-- LANG:(EN|ES|DE|FR) -->', full_response)
            lang_html = {}
            lang_slug = {}
            
            for i in range(1, len(parts), 2):
                lang_code = parts[i].lower()
                block = parts[i+1].strip()
                
                # SLUG satırını bul
                slug_match = re.search(r'<!-- SLUG:(.*?) -->', block)
                if slug_match:
                    lang_slug[lang_code] = slug_match.group(1).strip()
                    # SLUG satırını HTML'den temizle
                    block = re.sub(r'<!-- SLUG:.*? -->', '', block).strip()
                
                # HTML içeriğini temizle
                html_content = block.replace('```html', '').replace('```', '')
                lang_html[lang_code] = html_content
            
            # Tüm dillerin geldiğini kontrol et
            expected = ['en', 'es', 'de', 'fr']
            for lang in expected:
                if lang not in lang_html:
                    print(f"⚠️ {lang.upper()} dili eksik, atlanıyor.")
            
            hash_id = create_hash()
            print(f"🔑 Üretilen hash: {hash_id} (Task ID: {task_id})")
            
            now = datetime.now()
            yil = now.strftime("%Y")
            ay = now.strftime("%m")
            
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
            else:
                print("ℹ️ Bu görev için görsel prompt'u yok, atlanıyor.")
            
            # Her dil için HTML kaydet (her dil KENDİ slug'ı ile)
            saved_count = 0
            for lang, html in lang_html.items():
                if lang in expected:
                    # Her dilin kendi slug'ını kullan, yoksa fallback
                    slug = lang_slug.get(lang, create_slug(topic))
                    html_yaz(hash_id, task, html, kategori, lang, yil, ay, slug)
                    saved_count += 1
            
            print(f"📁 Toplam {saved_count} dil kaydedildi (EN/ES/DE/FR)")
            
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
    print("🛰️ Creator Bot (4 Dil + Her Dil Kendi Slug'ı) başlatılıyor...")
    if not os.path.exists("tasks.json"):
        print("❌ tasks.json bulunamadı!")
        sys.exit(1)
    with open("tasks.json", "r", encoding="utf-8") as f:
        tasks = json.load(f)
    pending_tasks = [t for t in tasks if t.get("status") == "pending"]
    if not pending_tasks:
        print("💤 Bekleyen görev yok.")
        return
    print(f"📋 Toplam {len(pending_tasks)} pending görev var. Sadece 1 tanesi işlenecek.")
    
    # SADECE İLK PENDING TASK'İ İŞLE
    task = pending_tasks[0]
    print(f"\n--- Görev {task.get('task_id')} işleniyor ---")
    
    basarili, hash_id = isle_gorev(task)
    
    if not basarili:
        print(f"❌ Görev {task.get('task_id')} başarısız, workflow durduruluyor.")
        task["status"] = "failed"
        with open("tasks.json", "w", encoding="utf-8") as f:
            json.dump(tasks, f, indent=4, ensure_ascii=False)
        sys.exit(1)
    
    with open("tasks.json", "w", encoding="utf-8") as f:
        json.dump(tasks, f, indent=4, ensure_ascii=False)
    
    print("\n🏁 Görev tamamlandı. Kalan pending görevler için workflow'u tekrar çalıştır.")

if __name__ == "__main__":
    operasyon_baslat()
