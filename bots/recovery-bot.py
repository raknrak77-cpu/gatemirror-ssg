import os
import shutil
from bs4 import BeautifulSoup

def remove_all_images_from_html(html_content):
    """HTML içindeki tüm <img> etiketlerini siler"""
    soup = BeautifulSoup(html_content, 'html.parser')
    for img in soup.find_all('img'):
        img.decompose()
    return str(soup)

def clean_and_sync():
    """
    1. recovered-articles/ içindeki HTML'lerden img etiketlerini siler
    2. articles/ klasörünü tamamen temizler
    3. Temizlenmiş dosyaları recovered-articles/ -> articles/ kopyalar
    """
    
    source_dir = "recovered-articles"
    target_dir = "articles"
    
    # 1. Kaynak klasör kontrolü
    if not os.path.exists(source_dir):
        print(f"❌ '{source_dir}' klasörü bulunamadı!")
        print(f"💡 Mevcut klasörler: {os.listdir('.')}")
        return
    
    # 2. TÜM img etiketlerini sil (kaynak klasörde)
    print("\n" + "="*60)
    print("📷 AŞAMA 1: recovered-articles içindeki img etiketleri siliniyor...")
    print("="*60)
    
    success_count = 0
    fail_count = 0
    html_files = []
    
    for root, dirs, files in os.walk(source_dir):
        for file in files:
            if not file.endswith('.html'):
                continue
            
            file_path = os.path.join(root, file)
            html_files.append(file_path)
            print(f"📖 İşleniyor: {file_path}")
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    html_content = f.read()
                
                clean_html = remove_all_images_from_html(html_content)
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(clean_html)
                
                print(f"   ✅ img etiketleri silindi")
                success_count += 1
                
            except Exception as e:
                print(f"   ❌ Hata: {e}")
                fail_count += 1
    
    print(f"\n📊 Temizlik: Başarılı {success_count}, Başarısız {fail_count}")
    
    # 3. articles/ klasörünü temizle
    print("\n" + "="*60)
    print("🗑️ AŞAMA 2: articles/ klasörü temizleniyor...")
    print("="*60)
    
    if os.path.exists(target_dir):
        for root, dirs, files in os.walk(target_dir):
            for file in files:
                file_path = os.path.join(root, file)
                os.remove(file_path)
                print(f"   🗑️ Silindi: {file_path}")
            for dir_name in dirs:
                dir_path = os.path.join(root, dir_name)
                try:
                    os.rmdir(dir_path)
                    print(f"   📁 Silindi: {dir_path}")
                except OSError:
                    pass  # Dizin boş değilse geç
        print(f"✅ {target_dir}/ içi temizlendi")
    else:
        os.makedirs(target_dir, exist_ok=True)
        print(f"✅ {target_dir}/ oluşturuldu")
    
    # 4. Temizlenmiş dosyaları kopyala
    print("\n" + "="*60)
    print("📋 AŞAMA 3: recovered-articles/ -> articles/ kopyalanıyor...")
    print("="*60)
    
    copy_success = 0
    for src_path in html_files:
        # recovered-articles/en/.../file.html -> articles/en/.../file.html
        rel_path = os.path.relpath(src_path, source_dir)
        dst_path = os.path.join(target_dir, rel_path)
        dst_dir = os.path.dirname(dst_path)
        
        os.makedirs(dst_dir, exist_ok=True)
        shutil.copy2(src_path, dst_path)
        print(f"   ✅ Kopyalandı: {rel_path}")
        copy_success += 1
    
    print("\n" + "="*60)
    print("🏁 İŞLEM TAMAMLANDI")
    print(f"📷 Silinen img etiketleri: {success_count} dosya")
    print(f"📋 Kopyalanan dosyalar: {copy_success} dosya")
    print(f"📁 Kaynak: {source_dir}/")
    print(f"📁 Hedef: {target_dir}/")
    print("="*60)

if __name__ == "__main__":
    clean_and_sync()
