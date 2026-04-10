import os
import re
import boto3
from datetime import datetime
from botocore.client import Config
from jinja2 import Template

# R2
R2_ID = os.getenv('R2_ACCOUNT_ID')
R2_ACCESS_KEY = os.getenv('R2_ACCESS_KEY_ID')
R2_SECRET_KEY = os.getenv('R2_SECRET_ACCESS_KEY')
R2_BUCKET = os.getenv('R2_BUCKET_NAME')
R2_PUBLIC_URL = os.getenv('R2_PUBLIC_URL').rstrip('/')

s3 = boto3.client(
    's3',
    endpoint_url=f'https://{R2_ID}.r2.cloudflarestorage.com',
    aws_access_key_id=R2_ACCESS_KEY,
    aws_secret_access_key=R2_SECRET_KEY,
    config=Config(signature_version='s3v4'),
    region_name='auto'
)

def get_template_from_r2(template_name):
    """R2'den template dosyasını çeker"""
    import requests
    url = f"{R2_PUBLIC_URL}/templates/{template_name}"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.text
    except:
        pass
    return None

def get_all_articles():
    """R2'deki tüm makaleleri listeler"""
    articles = []
    prefix = "articles/en/"
    
    response = s3.list_objects_v2(Bucket=R2_BUCKET, Prefix=prefix)
    if 'Contents' not in response:
        return articles
    
    for obj in response['Contents']:
        key = obj['Key']
        if not key.endswith('.html') or key.endswith('/index.html'):
            continue
        
        file_obj = s3.get_object(Bucket=R2_BUCKET, Key=key)
        content = file_obj['Body'].read().decode('utf-8')
        
        title_match = re.search(r'<h1>(.*?)</h1>', content)
        title = title_match.group(1) if title_match else ""
        
        parts = key.replace(prefix, '').split('/')
        if len(parts) >= 2:
            category = parts[0]
            hash_id = parts[1].replace('.html', '')
        else:
            category = 'general'
            hash_id = 'unknown'
        
        articles.append({
            'title': title,
            'url': f"/articles/en/{category}/{hash_id}.html",
            'image': f"{R2_PUBLIC_URL}/images/{category}/{hash_id}_kapak.webp",
            'excerpt': title[:100],
            'date': obj['LastModified'].strftime("%Y-%m-%d"),
            'category': category,
            'hash': hash_id
        })
    
    return articles

def get_menu_texts(lang):
    texts = {
        'en': {'home': 'HOME', 'wellness': 'WELLNESS', 'tech': 'TECH & AI', 
               'future-economy': 'FUTURE ECONOMY', 'eco': 'ECO & SUSTAINABLE', 'elearning': 'E-LEARNING'}
    }
    return texts.get(lang, texts['en'])

def publisher():
    print("🚀 Publisher bot başlatılıyor...")
    
    # Template'leri al
    home_template_str = get_template_from_r2("home.html")
    list_template_str = get_template_from_r2("list.html")
    
    if not home_template_str or not list_template_str:
        print("❌ Template'ler alınamadı!")
        return
    
    home_template = Template(home_template_str)
    list_template = Template(list_template_str)
    
    # Makaleleri al
    articles = get_all_articles()
    print(f"📋 {len(articles)} makale bulundu.")
    
    if not articles:
        return
    
    # Tarihe göre sırala
    articles.sort(key=lambda x: x['date'], reverse=True)
    latest_articles = articles[:12]
    menu_texts = get_menu_texts('en')
    
    # Ana sayfayı oluştur (home.html)
    home_output = home_template.render(lang='en', menu=menu_texts, articles=latest_articles)
    s3.put_object(Bucket=R2_BUCKET, Key='articles/en/index.html', Body=home_output.encode('utf-8'), ContentType='text/html')
    print("✅ Ana sayfa: articles/en/index.html")
    
    # Kategori arşivlerini oluştur (list.html)
    categories = ['wellness', 'tech', 'future-economy', 'eco', 'elearning']
    for category in categories:
        cat_articles = [a for a in articles if a['category'] == category]
        if not cat_articles:
            continue
        cat_articles.sort(key=lambda x: x['date'], reverse=True)
        list_output = list_template.render(
            lang='en', menu=menu_texts,
            category_name=category.upper(),
            category_description="",
            articles=cat_articles
        )
        s3.put_object(Bucket=R2_BUCKET, Key=f'articles/en/{category}/index.html', Body=list_output.encode('utf-8'), ContentType='text/html')
        print(f"✅ Kategori arşivi: articles/en/{category}/index.html")
    
    print("\n🏁 Publisher tamamlandı.")

if __name__ == "__main__":
    publisher()
