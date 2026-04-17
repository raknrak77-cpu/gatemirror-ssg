import os
import boto3
from botocore.client import Config

# R2 Secrets
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

def upload_file_to_r2(local_path, r2_key, content_type=None):
    if os.path.exists(local_path):
        print(f"🚀 Yükleniyor: {local_path} -> {r2_key}")
        extra_args = {}
        if content_type:
            extra_args['ContentType'] = content_type
        s3.upload_file(local_path, R2_BUCKET, r2_key, ExtraArgs=extra_args)
        print(f"✅ Yüklendi: {r2_key}")
        return True
    return False

def upload_templates():
    """templates/ klasöründeki dosyaları R2'ye yedekler"""
    templates_dir = "templates"
    if not os.path.exists(templates_dir):
        print(f"⚠️ {templates_dir} klasörü yok, atlanıyor.")
        return
    
    for file in os.listdir(templates_dir):
        local_path = os.path.join(templates_dir, file)
        if os.path.isfile(local_path):
            r2_key = f"templates/{file}"
            upload_file_to_r2(local_path, r2_key)

def upload_css_to_assets():
    """templates/css/style.css dosyasını R2'de assets/css/style.css olarak yükler"""
    local_path = "templates/css/style.css"
    r2_key = "assets/css/style.css"
    
    if os.path.exists(local_path):
        print(f"\n🎨 CSS dosyası assets'e yükleniyor...")
        return upload_file_to_r2(local_path, r2_key, content_type='text/css')
    else:
        print(f"\n⚠️ templates/css/style.css dosyası bulunamadı, atlanıyor.")
        return False

def upload_hero_json():
    """Github templates/ klasöründen hero.json'u alıp R2 templates/ klasörüne yükler"""
    local_path = "templates/hero.json"
    r2_key = "templates/hero.json"
    
    if os.path.exists(local_path):
        print(f"\n🎨 Hero JSON yükleniyor...")
        return upload_file_to_r2(local_path, r2_key, content_type='application/json')
    else:
        print(f"\n⚠️ templates/hero.json dosyası bulunamadı, atlanıyor.")
        return False

def upload_svg_patterns():
    """SADECE 2 SVG pattern'ini R2'ye assets/ klasörüne yükler (isim değiştirerek)"""
    print("\n🎨 ÖZEL SVG PATTERN YÜKLEME (SADECE 2 DOSYA)")
    print("-" * 40)
    
    svg_files = [
        ("assets/all-patterns/spiral_out/spiral_circular_basic_12.svg", "assets/svg1.svg"),
        ("assets/all-patterns/spiral_out/spiral_circular_basic_04.svg", "assets/svg2.svg"),
    ]
    
    for local_path, r2_key in svg_files:
        if os.path.exists(local_path):
            upload_file_to_r2(local_path, r2_key, content_type='image/svg+xml')
        else:
            print(f"⚠️ Dosya bulunamadı: {local_path}")

def uploader():
    """content/ altındaki HTML'leri R2'ye (raw-articles/) yükler"""
    
    # 1. Template'leri yedekle
    print("\n📁 TEMPLATE YEDEKLEME")
    print("-" * 40)
    upload_templates()
    
    # 2. CSS dosyasını assets/ altına yükle
    upload_css_to_assets()
    
    # 3. Hero JSON'u yedekle
    upload_hero_json()
    
    # 4. SADECE 2 ÖZEL SVG PATTERN YÜKLE (assets/ klasörünü tarama YOK!)
    upload_svg_patterns()
    
    # 5. content/ altındaki ham HTML'leri raw-articles/ altına yükle
    content_base = "content"
    if not os.path.exists(content_base):
        print(f"❌ {content_base} klasörü yok!")
        return
    
    print("\n📁 İÇERİK YÜKLEME")
    print("-" * 40)
    
    uploaded_files = []
    
    for root, dirs, files in os.walk(content_base):
        for file in files:
            if not file.endswith('.html'):
                continue
            
            local_path = os.path.join(root, file)
            r2_key = local_path.replace("content/", "raw-articles/")
            if upload_file_to_r2(local_path, r2_key):
                uploaded_files.append(local_path)
    
    # 6. Local dosyaları temizle
    print("\n🗑️ LOCAL TEMİZLİK")
    print("-" * 40)
    for file_path in uploaded_files:
        try:
            os.remove(file_path)
            print(f"   🗑️ Silindi: {file_path}")
        except Exception as e:
            print(f"   ⚠️ Silinemedi: {file_path} - {e}")
    
    # 7. Boş klasörleri temizle
    for root, dirs, files in os.walk(content_base, topdown=False):
        for dir_name in dirs:
            dir_path = os.path.join(root, dir_name)
            try:
                if not os.listdir(dir_path):
                    os.rmdir(dir_path)
                    print(f"   🗑️ Boş klasör silindi: {dir_path}")
            except:
                pass
    
    print("\n" + "=" * 60)
    print("🏁 UPLOADER TAMAMLANDI!")
    print("   ✅ Template'ler → R2/templates/")
    print("   ✅ style.css → R2/assets/css/style.css")
    print("   ✅ hero.json → R2/templates/hero.json")
    print("   ✅ svg1.svg → R2/assets/svg1.svg")
    print("   ✅ svg2.svg → R2/assets/svg2.svg")
    print("   ✅ content/ → R2/raw-articles/")
    print("=" * 60)

if __name__ == "__main__":
    uploader()
