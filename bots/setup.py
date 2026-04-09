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
        
        # Her klasöre .gitkeep dosyası ekle (Git'in görmesi için)
        gitkeep_path = os.path.join(folder, ".gitkeep")
        with open(gitkeep_path, "w") as f:
            f.write("# Bu klasörün Git tarafından takip edilmesi için eklendi.")
        print(f"      📄 {folder}/.gitkeep")
    
    print("\n✅ Tüm klasörler ve .gitkeep dosyaları oluşturuldu.")

if __name__ == "__main__":
    create_folders()
