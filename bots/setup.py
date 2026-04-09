import os

# Oluşturulacak klasörler (dizinler ve alt dizinler)
folders = [
    "content/en/wellness",
    "content/en/tech",
    "content/en/future-economy",
    "content/en/eco",
    "content/en/elearning",
    "content/es/wellness",
    "content/es/tech",
    "content/es/future-economy",
    "content/es/eco",
    "content/es/elearning",
    "content/de/wellness",
    "content/de/tech",
    "content/de/future-economy",
    "content/de/eco",
    "content/de/elearning",
    "content/fr/wellness",
    "content/fr/tech",
    "content/fr/future-economy",
    "content/fr/eco",
    "content/fr/elearning",
    "templates",
    "public",
    "bots",
    ".github/workflows"
]

def create_folders():
    print("📁 Klasör yapısı oluşturuluyor...")
    for folder in folders:
        os.makedirs(folder, exist_ok=True)
        print(f"   ✅ {folder}/")
        
        # Her klasöre info.txt dosyası ekle (Git'in görmesi için)
        info_path = os.path.join(folder, "info.txt")
        with open(info_path, "w") as f:
            f.write(f"Bu klasör: {folder}\nOluşturulma tarihi: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"      📄 {folder}/info.txt")
    
    print("\n✅ Tüm klasörler ve info.txt dosyaları oluşturuldu.")

if __name__ == "__main__":
    import time
    create_folders()
