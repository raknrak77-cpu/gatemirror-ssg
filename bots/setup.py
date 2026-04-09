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
    
    # .gitkeep dosyaları oluştur (boş klasörlerin git'e eklenmesi için)
    with open("content/.gitkeep", "w") as f:
        f.write("# Boş klasör")
    with open("templates/.gitkeep", "w") as f:
        f.write("# Boş klasör")
    with open("public/.gitkeep", "w") as f:
        f.write("# Boş klasör")
    with open("bots/.gitkeep", "w") as f:
        f.write("# Boş klasör")
    
    print("\n✅ Tüm klasörler oluşturuldu.")

if __name__ == "__main__":
    create_folders()
