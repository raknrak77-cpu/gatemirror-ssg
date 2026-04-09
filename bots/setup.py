import os
import subprocess
import time

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
        
        # Her klasöre info.txt dosyası ekle
        info_path = os.path.join(folder, "info.txt")
        with open(info_path, "w") as f:
            f.write(f"Klasör: {folder}\nOluşturulma: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Değişiklikleri Git'e ekle ve commit yap
    print("\n📤 Değişiklikler Git'e ekleniyor...")
    subprocess.run(["git", "config", "--local", "user.email", "action@github.com"])
    subprocess.run(["git", "config", "--local", "user.name", "GitHub Action"])
    subprocess.run(["git", "add", "."])
    subprocess.run(["git", "commit", "-m", "📁 Klasör yapısı oluşturuldu", "--allow-empty"])
    subprocess.run(["git", "push"])
    
    print("\n✅ Tüm klasörler oluşturuldu ve GitHub'a kaydedildi.")

if __name__ == "__main__":
    create_folders()
