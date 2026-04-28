import os
import sys
import json
import time
import uuid
import re
import requests
import subprocess
from datetime import datetime
import traceback

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
    """HTML'i META bilgileriyle birlikte yazar - yorum satırı olarak"""
    author_persona = task.get('author_persona', 'Expert Analyst')
    datetime_full = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Yazar bilgileri
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
    
    # META parçalarını hazırla
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
    
    # Cluster bilgileri varsa ekle
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
    
    # Görsel bilgileri
    visuals = task.get('visuals', {})
    if visuals:
        visual_types = list(visuals.keys())
        meta_parts.append(f"visuals={'|'.join(visual_types)}")
    
    # META yorum satırı
    meta_comment = "<!-- META: " + ", ".join(meta_parts) + " -->\n"
    final_html = meta_comment + makale_html
    
    # Kaydet
    target_dir = os.path.join("content", lang, kategori, yil, ay)
    os.makedirs(target_dir, exist_ok=True)
    filename = f"{hash_id}-{slug}.html"
    target_path = os.path.join(target_dir, filename)
    
    with open(target_path, 'w', encoding='utf-8') as f:
        f.write(final_html)
    
    file_size = os.path.getsize(target_path) // 1024
    
    # MAKALE DETAYLARINI LOGLA
    log(f"✅ {lang.upper()} kaydedildi: {filename} ({file_size} KB)")
    
    # Makale başlığını bul (h1'den)
    title_match = re.search(r'<h1>(.*?)</h1>', makale_html, re.DOTALL)
    title = title_match.group(1).strip() if title_match else "Başlık bulunamadı"
    log(f"   📌 Başlık: {title[:80]}...")
    
    # Kelime sayısı ve okuma süresi
    text_clean = re.sub(r'<[^>]+>', ' ', makale_html)
    words = re.findall(r'\b\w+\b', text_clean)
    word_count = len(words)
    reading_time = max(1, word_count // 200)
    log(f"   📊 Kelime: {word_count} | Okuma: {reading_time} dk | Karakter: {len(makale_html)}")
    
    # META başlıklarını logla
    log(f"   📝 META: author={author_name}, cluster_id={cluster_id}, intent={cluster_rules_data.get('intent', '-')}, monetization={cluster_rules_data.get('monetization', '-')}, visuals={visual_types if visuals else '-'}")
    
    return target_path

def run_visual_bot(task, hash_id, kategori, yil, ay):
    """Görsel bot'u çalıştır - V16 uyumlu, görsel boyutlarını log'lar"""
    visuals = task.get('visuals', {})
    
    log("=" * 60)
    log("GÖRSEL ÜRETİM AŞAMASI")
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
        log(f"    Prompt: {prompt[:80]}...")
    
    log("\nvisual_factory.py çağrılıyor...")
    
    try:
        visuals_json = json.dumps(visuals)
        result = subprocess.run(
            ['python', 'bots/visual_factory.py', task.get('task_id'), hash_id, visuals_json, kategori, yil, ay],
            timeout=180,
            capture_output=True,
            text=True
        )
        
        log(f"Çıkış kodu: {result.returncode}")
        
        # Görsel boyutlarını yakalamak için stdout'u parse et
        if result.stdout:
            lines = result.stdout.strip().split('\n')
            for line in lines:
                # Görsel başarı mesajlarını ve boyutlarını yakala
                if 'GEÇERLİ görsel' in line or 'tamamlandı' in line.lower() or 'R2\'ye yüklendi' in line:
                    log(f"  {line}")
                # Özet satırlarını da göster
                if 'BAŞARILI:' in line or 'TAMAMLANDI' in line:
                    log(f"  {line}")
        
        if result.stderr:
            log(f"STDERR (ilk 500): {result.stderr[:500]}", "WARN")
        
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

def isle_gorev(task):
    task_id = task.get('task_id', '0000')
    topic = task['topic']
    persona = task.get('author_persona', 'Expert Analyst')
    special_instructions = task.get('special_instructions', '')
    reference_link = task.get('reference_link', '')
    kategori = task.get('category', 'general').lower()
    cluster_id = task.get('cluster_id')
    
    log("=" * 70)
    log(f"GÖREV BAŞLIYOR: {task_id}")
    log("=" * 70)
    log(f"Topic: {topic}")
    log(f"Kategori: {kategori}")
    log(f"Cluster ID: {cluster_id}")
    log(f"Yazar: {persona}")
    
    clusters = load_clusters()
    author_info = get_author_info(cluster_id, clusters)
    cluster_rules_data = get_cluster_rules(cluster_id, clusters)
    
    if author_info:
        log(f"Yazar bulundu: {author_info.get('name')}")
    
    # Prompt oluştur
    cluster_rules = ""
    if cluster_rules_data:
        cluster_rules = f"""
## CLUSTER RULES:
- Required sections: {', '.join(cluster_rules_data.get('required_sections', []))}
- Forbidden: {', '.join(cluster_rules_data.get('forbidden', []))}
- Target keywords: {', '.join(cluster_rules_data.get('keywords', []))}
"""

    prompt_emri = f"""
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
<div class="sources">
<h3>Sources</h3>
<ul>
<li>[REAL URL ONLY. Use ONLY: .gov, .edu, .org, reuters.com, bloomberg.com, ft.com, wsj.com, nature.com, science.org, arxiv.org, github.com, or official corporate domains. ABSOLUTELY NO: example.com, domain.com, placeholder.com, or ANY fake/placeholder URLs. If you cannot provide a real URL, write "Source: [Institution Name] (no URL available)". Min 3, max 5 sources.]</li>
</ul>
</div>

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
- NO fake URLs (example.com, domain.com, placeholder.com STRICTLY FORBIDDEN)
- NO markdown/code blocks
- If URL cannot be verified, use fallback: "Source: [Institution Name] (no URL available)"
"""
    
    # Gemini çağrısı
    log("Gemini çağrılıyor (EN/ES/DE/FR)...")
    start_time = time.time()
    
    payload = {
        "contents": [{"parts": [{"text": prompt_emri}]}],
        "generationConfig": {"temperature": 0.85, "maxOutputTokens": 28000, "topP": 0.95}
    }
    
    try:
        response = requests.post(GEMINI_URL, json=payload, timeout=420)
        res_data = response.json()
        
        if 'candidates' in res_data and len(res_data['candidates']) > 0:
            full_response = res_data['candidates'][0]['content']['parts'][0]['text']
            elapsed = time.time() - start_time
            log(f"Gemini yanıtı: {len(full_response)} karakter, {elapsed:.1f}s")
            
            # Parse et
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
                log(f"  {lang_code.upper()}: {len(html_content)} karakter, slug={lang_slug.get(lang_code, 'auto')}")
            
            hash_id = create_hash()
            log(f"Hash oluşturuldu: {hash_id}")
            
            now = datetime.now()
            yil = now.strftime("%Y")
            ay = now.strftime("%m")
            
            # Görsel üret
            visual_success = run_visual_bot(task, hash_id, kategori, yil, ay)
            
            if not visual_success:
                log("=" * 70)
                log("GÖRSEL ÜRETİLEMEDİ - MAKALE KAYDEDİLMEYECEK", "ERROR")
                log("Workflow duracak, tasks.json değişmeyecek")
                log("=" * 70)
                return False, None, None
            
            # Makaleleri kaydet
            log("\nMakaleler kaydediliyor...")
            
            saved_count = 0
            for lang, html in lang_html.items():
                if lang in ['en', 'es', 'de', 'fr']:
                    slug = lang_slug.get(lang, create_slug(topic))
                    html_yaz(hash_id, task, html, kategori, lang, yil, ay, slug, author_info, cluster_rules_data, cluster_id)
                    saved_count += 1
            
            log(f"Toplam {saved_count}/4 dil kaydedildi")
            
            return True, hash_id, task_id
        else:
            log(f"GEMINI HATASI: {json.dumps(res_data, indent=2)[:500]}", "ERROR")
            return False, None, None
    except Exception as e:
        log(f"SİSTEM HATASI: {e}", "ERROR")
        traceback.print_exc()
        return False, None, None

def operasyon_baslat():
    log("=" * 70)
    log("CREATOR BOT V48 - META LOG'LU, GÖRSEL BOYUT LOG'LU")
    log("1. Gemini'den makale üret")
    log("2. Hash oluştur")
    log("3. Görsel üret (boyutlar log'da)")
    log("4. Makaleleri kaydet (META yorum satırı olarak)")
    log("5. Tüm veriler log'da göster")
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
    log(f"CREATOR V48 TAMAMLANDI!")
    log(f"Hash: {hash_id}")
    log(f"Task ID: {task_id}")
    log("=" * 70)

if __name__ == "__main__":
    operasyon_baslat()
