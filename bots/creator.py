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

def load_clusters():
    try:
        with open("clusters.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {"categories": {}}

def get_author_info(cluster_id, clusters):
    if not cluster_id or not clusters:
        return None
    for cat_name, cat_data in clusters.get("categories", {}).items():
        for cluster_name, cluster_data in cat_data.get("clusters", {}).items():
            if cluster_data.get("cluster_id") == cluster_id:
                return cluster_data.get("default_author", {})
    return None

def html_yaz(hash_id, task, makale_html, kategori, lang, yil, ay, slug, author_info):
    author_persona = task.get('author_persona', 'Expert Analyst')
    datetime_full = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    if author_info:
        author_name = author_info.get('name', author_persona)
        author_title = author_info.get('title', '')
        author_bio = author_info.get('bio', '').replace('\n', ' ').replace('"', '\\"')
        author_avatar = author_info.get('avatar', '')
        meta_comment = f"<!-- META: author={author_name}, author_title={author_title}, author_bio={author_bio}, author_avatar={author_avatar}, datetime={datetime_full} -->\n"
        # 🔍 YENİ: META'ya yazılan yazar bilgisini göster
        print(f"   📝 META'ya yazılıyor: author={author_name}")
    else:
        meta_comment = f"<!-- META: author={author_persona}, datetime={datetime_full} -->\n"
        print(f"   📝 META'ya yazılıyor: author={author_persona} (varsayılan)")
    
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
    cluster_id = task.get('cluster_id')
    
    print(f"🚀 HEDEF: {topic} (ID: {task_id})")
    if cluster_id:
        print(f"📌 Cluster ID: {cluster_id}")
    print("🤖 Gemini'den 4 dilde (EN, ES, DE, FR) yanıt bekleniyor...")
    
    clusters = load_clusters()
    author_info = get_author_info(cluster_id, clusters)
    
    # 🔍 YENİ: Yazar bilgisi debug log'u
    if author_info:
        print(f"   ✅ Yazar bulundu: {author_info.get('name')} (cluster: {cluster_id})")
    else:
        if cluster_id:
            print(f"   ⚠️ Yazar bulunamadı: cluster_id={cluster_id} clusters.json'da yok")
        else:
            print(f"   ⚠️ Bu task'te cluster_id yok, varsayılan yazar kullanılacak (Gatemirror Expert)")
    
    cluster_rules = ""
    if cluster_id:
        for cat_name, cat_data in clusters.get("categories", {}).items():
            for cluster_name, cluster_data in cat_data.get("clusters", {}).items():
                if cluster_data.get("cluster_id") == cluster_id:
                    cluster_rules = f"""
## 🎯 CLUSTER RULES (MUST FOLLOW):
- Required sections: {', '.join(cluster_data.get('required_sections', []))}
- Forbidden: {', '.join(cluster_data.get('forbidden', []))}
- Style boost: {cluster_data.get('style_boost', '')}
- Target keywords: {', '.join(cluster_data.get('keywords', []))}
"""
                    break
            if cluster_rules:
                break
    
    prompt_emri = f"""
ROLE: You are {persona} — a real expert with field experience, strong opinions, and a distinct editorial voice. You write for Gatemirror, a premium multi-language analysis platform read by professionals globally.

TASK: Write ONE article about '{topic}' in FOUR culturally adapted versions.
This is NOT a translation job. Each version must feel ORIGINALLY WRITTEN for that audience.

{f"REFERENCE MATERIAL: {reference_link}" if reference_link else ""}
{f"SPECIAL INSTRUCTIONS: {special_instructions}" if special_instructions else ""}
{cluster_rules}

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
- Hook: ALWAYS start Introduction with a bold claim, surprising statistic, or provocative question.
- Avoid: "In today's rapidly evolving landscape", "It is worth noting", "In conclusion" — ban all AI filler phrases.

---

REQUIRED STRUCTURE (identical across all 4 languages):

<h1>[Title in target language]</h1>

<div class="editors-note">[2-3 sentences. First-person. Establish your credibility and why this topic is urgent RIGHT NOW.]</div>

<h2>Introduction</h2>
[Hook + problem + stakes + what reader will learn. Min 2 paragraphs.]

<h2>Key Takeaways</h2>
⚠️ CRITICAL: Write EXACTLY ONE <h2>Key Takeaways</h2> section per language.
Write 3-5 actual takeaways as <li> items.
<ul>
  <li><strong>First takeaway:</strong> Detailed explanation</li>
  <li><strong>Second takeaway:</strong> Detailed explanation</li>
</ul>

<h2>Main Analysis</h2>
[Minimum 4 subsections using <h3>. Structure: context → evidence → implication]

<h2>Practical Implications</h2>
[What should the reader DO? Concrete, actionable steps for their specific regional context]

<h2>Conclusion</h2>
[Synthesis + bold prediction for 2027-2028 + memorable closing line]

<h2>Frequently Asked Questions (FAQ)</h2>
<div itemscope="" itemtype="https://schema.org/Question">
  <h3 itemprop="name">[Question 1]</h3>
  <div itemscope="" itemprop="acceptedAnswer" itemtype="https://schema.org/Answer">
    <div itemprop="text">[Answer 1]</div>
  </div>
</div>
<div itemscope="" itemtype="https://schema.org/Question">
  <h3 itemprop="name">[Question 2]</h3>
  <div itemscope="" itemprop="acceptedAnswer" itemtype="https://schema.org/Answer">
    <div itemprop="text">[Answer 2]</div>
  </div>
</div>
<div itemscope="" itemtype="https://schema.org/Question">
  <h3 itemprop="name">[Question 3]</h3>
  <div itemscope="" itemprop="acceptedAnswer" itemtype="https://schema.org/Answer">
    <div itemprop="text">[Answer 3]</div>
  </div>
</div>

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
- 5-8 words max, lowercase, hyphens, no accents
- DIFFERENT for each language

STRICT RULES:
- "Key Takeaways" heading: NEVER translate, ALWAYS English
- "Frequently Asked Questions (FAQ)": ALWAYS in English heading
- NO fake URLs
- NO markdown/code blocks
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
            
            parts = re.split(r'<!-- LANG:(EN|ES|DE|FR) -->', full_response)
            lang_html = {}
            lang_slug = {}
            
            for i in range(1, len(parts), 2):
                lang_code = parts[i].lower()
                block = parts[i+1].strip()
                
                slug_match = re.search(r'<!-- SLUG:(.*?) -->', block)
                if slug_match:
                    lang_slug[lang_code] = slug_match.group(1).strip()
                    block = re.sub(r'<!-- SLUG:.*? -->', '', block).strip()
                
                html_content = block.replace('```html', '').replace('```', '')
                lang_html[lang_code] = html_content
            
            expected = ['en', 'es', 'de', 'fr']
            for lang in expected:
                if lang not in lang_html:
                    print(f"⚠️ {lang.upper()} dili eksik, atlanıyor.")
            
            hash_id = create_hash()
            print(f"🔑 Üretilen hash: {hash_id} (Task ID: {task_id})")
            
            now = datetime.now()
            yil = now.strftime("%Y")
            ay = now.strftime("%m")
            
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
            
            saved_count = 0
            for lang, html in lang_html.items():
                if lang in expected:
                    slug = lang_slug.get(lang, create_slug(topic))
                    html_yaz(hash_id, task, html, kategori, lang, yil, ay, slug, author_info)
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
    print("🛰️ Creator Bot (4 Dil + Cluster Boost + Yazar Desteği + FAQ) başlatılıyor...")
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
