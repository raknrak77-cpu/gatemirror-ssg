import os
import sys
import json
import time
import uuid
import re
import requests
import subprocess
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

GEMINI_KEY = os.getenv('GEMINI_API_KEY')
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={GEMINI_KEY}"

CLUSTERS_PATH = "task/clusters.json"

def log(msg, level="INFO"):
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    print(f"[{timestamp}] [{level}] {msg}")

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
        with open(CLUSTERS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        log(f"clusters.json yüklenemedi: {e}", "WARN")
        return {"categories": {}, "authors": {}}

def get_author_info(cluster_id, clusters):
    if not cluster_id or not clusters:
        return None
    
    for cat_name, cat_data in clusters.get("categories", {}).items():
        for cluster_name, cluster_data in cat_data.get("clusters", {}).items():
            if cluster_data.get("cluster_id") == cluster_id:
                author_id = cluster_data.get("author_id")
                if author_id:
                    authors = clusters.get("authors", {})
                    if author_id in authors:
                        return authors[author_id]
                return cluster_data.get("default_author")
    return None

def get_cluster_rules(cluster_id, clusters):
    if not cluster_id or not clusters:
        return {}
    
    for cat_name, cat_data in clusters.get("categories", {}).items():
        for cluster_name, cluster_data in cat_data.get("clusters", {}).items():
            if cluster_data.get("cluster_id") == cluster_id:
                return {
                    "cluster_name": cluster_name,
                    "category": cat_name,
                    "intent": cluster_data.get("intent", ""),
                    "cpc_min": cluster_data.get("cpc_min", ""),
                    "cpc_max": cluster_data.get("cpc_max", ""),
                    "monetization": cluster_data.get("monetization", ""),
                    "affiliate_ids": cluster_data.get("affiliate_ids", []),
                    "required_sections": cluster_data.get("required_sections", []),
                    "forbidden": cluster_data.get("forbidden", []),
                    "style_boost": cluster_data.get("style_boost", ""),
                    "keywords": cluster_data.get("keywords", [])
                }
    return {}

def get_first_pending_task():
    tasks_path = "task/tasks.json"
    
    if not os.path.exists(tasks_path):
        log("task/tasks.json bulunamadı!", "ERROR")
        return None
    
    with open(tasks_path, "r", encoding="utf-8") as f:
        tasks = json.load(f)
    
    if not tasks:
        log("task/tasks.json boş!", "ERROR")
        return None
    
    task = tasks[0]
    log(f"İlk pending task alındı: ID {task.get('task_id')}")
    return task

def html_yaz(hash_id, task, makale_html, kategori, lang, yil, ay, slug, author_info, cluster_rules_data, cluster_id):
    author_persona = task.get('author_persona', 'Expert Analyst')
    datetime_full = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    if author_info:
        author_name = author_info.get('name', author_persona)
        author_title = author_info.get('title', '')
        author_bio = author_info.get('bio', '').replace('\n', ' ').replace('"', '\\"')
        author_avatar = author_info.get('avatar', '')
    else:
        author_name = author_persona
        author_title = ''
        author_bio = ''
        author_avatar = ''
    
    meta_parts = [
        f"author={author_name}",
        f"author_title={author_title}",
        f"author_bio={author_bio}",
        f"author_avatar={author_avatar}",
        f"datetime={datetime_full}",
        f"task_id={task.get('task_id', '')}",
        f"category={kategori}",
        f"lang={lang}"
    ]
    
    if cluster_id:
        meta_parts.append(f"cluster_id={cluster_id}")
        meta_parts.append(f"cluster_name={cluster_rules_data.get('cluster_name', '')}")
        meta_parts.append(f"cluster_category={cluster_rules_data.get('category', '')}")
        meta_parts.append(f"intent={cluster_rules_data.get('intent', '')}")
        meta_parts.append(f"cpc_min={cluster_rules_data.get('cpc_min', '')}")
        meta_parts.append(f"cpc_max={cluster_rules_data.get('cpc_max', '')}")
        meta_parts.append(f"monetization={cluster_rules_data.get('monetization', '')}")
        
        if cluster_rules_data.get('affiliate_ids'):
            meta_parts.append(f"affiliate_ids={'|'.join(cluster_rules_data['affiliate_ids'])}")
        
        if cluster_rules_data.get('keywords'):
            meta_parts.append(f"keywords={'|'.join(cluster_rules_data['keywords'])}")
        
        if cluster_rules_data.get('required_sections'):
            meta_parts.append(f"required_sections={'|'.join(cluster_rules_data['required_sections'])}")
        
        if cluster_rules_data.get('forbidden'):
            meta_parts.append(f"forbidden={'|'.join(cluster_rules_data['forbidden'])}")
        
        if cluster_rules_data.get('style_boost'):
            style_boost_clean = cluster_rules_data['style_boost'].replace('\n', ' ').replace('"', '\\"')
            meta_parts.append(f"style_boost={style_boost_clean}")
    
    visuals = task.get('visuals', {})
    if visuals:
        visual_types = list(visuals.keys())
        meta_parts.append(f"visuals={'|'.join(visual_types)}")
    
    meta_comment = "<!-- META: " + ", ".join(meta_parts) + " -->\n"
    final_html = meta_comment + makale_html
    
    target_dir = os.path.join("content", lang, kategori, yil, ay)
    os.makedirs(target_dir, exist_ok=True)
    filename = f"{hash_id}-{slug}.html"
    target_path = os.path.join(target_dir, filename)
    
    with open(target_path, 'w', encoding='utf-8') as f:
        f.write(final_html)
    
    file_size = os.path.getsize(target_path) // 1024
    log(f"{lang.upper()} kaydedildi: {filename} ({file_size} KB)")
    return target_path

def run_visual_bot_parallel(task, hash_id, kategori, yil, ay):
    """Görsel bot'u paralel çalıştır - V16 uyumlu"""
    visuals = task.get('visuals', {})
    
    log("=" * 60)
    log("GÖRSEL ÜRETİM AŞAMASI (PARALEL)")
    log("=" * 60)
    log(f"Hash: {hash_id}")
    log(f"Kategori: {kategori}")
    log(f"Tarih: {yil}/{ay}")
    
    if not visuals:
        log("GÖRSEL PROMPT'U YOK!", "ERROR")
        return False
    
    log(f"Görsel tipleri: {list(visuals.keys())}")
    for img_type, prompt in visuals.items():
        log(f"  {img_type}: {len(prompt)} karakter")
        log(f"    {prompt[:80]}...")
    
    log("\nvisual_factory.py çağrılıyor (paralel mod)...")
    
    try:
        visuals_json = json.dumps(visuals)
        result = subprocess.run(
            ['python', 'bots/visual_factory.py', task.get('task_id'), hash_id, visuals_json, kategori, yil, ay],
            timeout=180,
            capture_output=True,
            text=True
        )
        
        log(f"Çıkış kodu: {result.returncode}")
        
        if result.stdout:
            log(f"STDOUT:\n{result.stdout}")
        
        if result.stderr:
            log(f"STDERR:\n{result.stderr[:500]}", "WARN")
        
        if result.returncode == 0:
            log("GÖRSEL ÜRETİMİ BAŞARILI!")
            return True
        else:
            log(f"GÖRSEL ÜRETİMİ BAŞARISIZ (exit code: {result.returncode})", "ERROR")
            return False
            
    except subprocess.TimeoutExpired:
        log("Görsel bot ZAMAN AŞIMI (180 saniye)", "ERROR")
        return False
    except Exception as e:
        log(f"Görsel bot hatası: {e}", "ERROR")
        return False

def call_gemini(prompt, task_id):
    """Gemini'yi çağır ve yanıtı döndür"""
    log(f"Gemini çağrılıyor (Task: {task_id})...")
    start_time = time.time()
    
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.85, "maxOutputTokens": 28000, "topP": 0.95}
    }
    
    try:
        response = requests.post(GEMINI_URL, json=payload, timeout=420)
        elapsed = time.time() - start_time
        log(f"Gemini yanıt süresi: {elapsed:.1f}s")
        
        if response.status_code != 200:
            log(f"Gemini HTTP {response.status_code}: {response.text[:200]}", "ERROR")
            return None
        
        res_data = response.json()
        
        if 'candidates' in res_data and len(res_data['candidates']) > 0:
            full_response = res_data['candidates'][0]['content']['parts'][0]['text']
            log(f"Gemini yanıt uzunluğu: {len(full_response)} karakter")
            return full_response
        else:
            log(f"Gemini hata: {json.dumps(res_data, indent=2)[:500]}", "ERROR")
            return None
            
    except Exception as e:
        log(f"Gemini bağlantı hatası: {e}", "ERROR")
        return None

def parse_gemini_response(full_response):
    """Gemini yanıtını parse et"""
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
        log(f"{lang_code.upper()}: {len(html_content)} karakter, slug={lang_slug.get(lang_code, 'auto')}")
    
    return lang_html, lang_slug

def build_prompt(task, cluster_rules_data):
    """Prompt oluştur"""
    topic = task['topic']
    persona = task.get('author_persona', 'Expert Analyst')
    special_instructions = task.get('special_instructions', '')
    reference_link = task.get('reference_link', '')
    
    cluster_rules = ""
    if cluster_rules_data:
        cluster_rules = f"""
## CLUSTER RULES:
- Required sections: {', '.join(cluster_rules_data.get('required_sections', []))}
- Forbidden: {', '.join(cluster_rules_data.get('forbidden', []))}
- Target keywords: {', '.join(cluster_rules_data.get('keywords', []))}
"""
    
    return f"""
ROLE: You are {persona} — a real expert with field experience, strong opinions, and a distinct editorial voice.

TASK: Write FOUR culturally independent articles about '{topic}'. Each version must stand alone.

{f"REFERENCE: {reference_link}" if reference_link else ""}
{f"INSTRUCTIONS: {special_instructions}" if special_instructions else ""}
{cluster_rules}

CULTURAL ADAPTATION:
- EN: Global perspective
- ES: Latin American/Spanish context
- DE: DACH region focus
- FR: French/Francophone context

CONTENT REQUIREMENTS (per language):
- MINIMUM: 2000 words per language
- Hook: Start Introduction with a bold claim or statistic

STRUCTURE:
<h1>[Title]</h1>
<div class="editors-note">[2-3 sentences, first-person]</div>
<h2>Introduction</h2>
<h2>Key Takeaways</h2>
<ul><li><strong>Takeaway 1:</strong> explanation</li></ul>
<h2>Main Analysis</h2>
[Min 4 subsections with <h3>]
<h2>Practical Implications</h2>
<h2>Conclusion</h2>
<h2>Frequently Asked Questions (FAQ)</h2>
<div class="sources"><h3>Sources</h3><ul><li>[Real URL]</li></ul></div>

OUTPUT FORMAT:
<!-- LANG:EN -->
<!-- SLUG:[slug] -->
[HTML]
<!-- LANG:ES -->
<!-- SLUG:[slug] -->
[HTML]
<!-- LANG:DE -->
<!-- SLUG:[slug] -->
[HTML]
<!-- LANG:FR -->
<!-- SLUG:[slug] -->
[HTML]

STRICT RULES:
- NO fake URLs
- NO markdown/code blocks
"""

def isle_gorev(task):
    task_id = task.get('task_id', '0000')
    topic = task['topic']
    kategori = task.get('category', 'general').lower()
    cluster_id = task.get('cluster_id')
    
    log("=" * 70)
    log(f"GÖREV BAŞLIYOR: {task_id}")
    log("=" * 70)
    log(f"Topic: {topic}")
    log(f"Kategori: {kategori}")
    log(f"Cluster ID: {cluster_id}")
    log(f"Yazar: {task.get('author_persona')}")
    
    clusters = load_clusters()
    author_info = get_author_info(cluster_id, clusters)
    cluster_rules_data = get_cluster_rules(cluster_id, clusters)
    
    if author_info:
        log(f"Yazar bulundu: {author_info.get('name')}")
    
    # 1. Prompt oluştur
    prompt = build_prompt(task, cluster_rules_data)
    
    # 2. Gemini'den makale üret
    full_response = call_gemini(prompt, task_id)
    if not full_response:
        return False, None, None
    
    # 3. Parse et
    lang_html, lang_slug = parse_gemini_response(full_response)
    
    expected = ['en', 'es', 'de', 'fr']
    for lang in expected:
        if lang not in lang_html:
            log(f"{lang.upper()} dili eksik!", "WARN")
    
    # 4. Hash oluştur
    hash_id = create_hash()
    log(f"Hash oluşturuldu: {hash_id}")
    
    now = datetime.now()
    yil = now.strftime("%Y")
    ay = now.strftime("%m")
    log(f"Tarih: {yil}/{ay}")
    
    # 5. Görsel üret (V16 ile, paralel)
    visual_success = run_visual_bot_parallel(task, hash_id, kategori, yil, ay)
    
    if not visual_success:
        log("=" * 70)
        log("GÖRSEL ÜRETİLEMEDİ - MAKALE KAYDEDİLMEYECEK", "ERROR")
        log("Workflow duracak, tasks.json değişmeyecek")
        log("=" * 70)
        return False, None, None
    
    # 6. Makaleleri kaydet
    log("\nMakaleler kaydediliyor...")
    
    saved_count = 0
    for lang, html in lang_html.items():
        if lang in expected:
            slug = lang_slug.get(lang, create_slug(topic))
            html_yaz(hash_id, task, html, kategori, lang, yil, ay, slug, author_info, cluster_rules_data, cluster_id)
            saved_count += 1
    
    log(f"Toplam {saved_count}/4 dil kaydedildi")
    
    return True, hash_id, task_id

def operasyon_baslat():
    log("=" * 70)
    log("CREATOR BOT V46 - V16 UYUMLU, PARALEL GÖRSEL")
    log("1. Gemini'den makale üret")
    log("2. Hash oluştur")
    log("3. Görsel üret (visual_factory V16)")
    log("4. Makaleleri kaydet")
    log("=" * 70)
    
    task = get_first_pending_task()
    if not task:
        log("İşlenecek görev yok!", "ERROR")
        sys.exit(1)
    
    basarili, hash_id, task_id = isle_gorev(task)
    
    if not basarili:
        log("=" * 70)
        log("WORKFLOW DURDURULUYOR", "ERROR")
        log("Sebep: Görsel üretilemedi")
        log("tasks.json DEĞİŞMEDİ")
        log("=" * 70)
        sys.exit(1)
    
    with open("task/current_hash.txt", "w") as f:
        f.write(hash_id)
    log(f"Hash kaydedildi: task/current_hash.txt -> {hash_id}")
    
    log("=" * 70)
    log(f"CREATOR V46 TAMAMLANDI!")
    log(f"Hash: {hash_id}")
    log(f"Task ID: {task_id}")
    log(f"Görsel formatı: 1024x576 (16:9)")
    log("=" * 70)

if __name__ == "__main__":
    operasyon_baslat()
