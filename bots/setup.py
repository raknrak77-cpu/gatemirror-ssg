import os

def kategori_index_olustur(dil, kategori, kategori_adi):
    """Belirtilen dil ve kategori için index.html oluşturur."""
    hedef_klasor = os.path.join("content", dil, kategori)
    os.makedirs(hedef_klasor, exist_ok=True)
    
    index_dosyasi = os.path.join(hedef_klasor, "index.html")
    
    html_icerik = f"""<!DOCTYPE html>
<html lang="{dil}">
<head>
    <meta charset="UTF-8">
    <title>{kategori_adi} | Gatemirror</title>
</head>
<body>
    <h1>{kategori_adi}</h1>
    <p>Bu kategoride yakında makaleler yayınlanacak.</p>
    <a href="/">Ana Sayfaya Dön</a>
</body>
</html>"""
    
    with open(index_dosyasi, "w", encoding="utf-8") as f:
        f.write(html_icerik)
    print(f"✅ {index_dosyasi} oluşturuldu.")

def dizinleri_olustur():
    """Tüm diller ve kategoriler için gerekli dizinleri oluşturur."""
    
    diller = ["en", "es", "de", "fr"]
    kategoriler = {
        "wellness": "WELLNESS",
        "tech": "TECH & AI",
        "future-economy": "FUTURE ECONOMY",
        "eco": "ECO & SUSTAINABLE",
        "elearning": "E-LEARNING"
    }
    
    for dil in diller:
        for kategori, kategori_adi in kategoriler.items():
            kategori_index_olustur(dil, kategori, kategori_adi)
    
    # Ana dizin için index.html
    ana_index = "public/index.html"
    os.makedirs("public", exist_ok=True)
    with open(ana_index, "w", encoding="utf-8") as f:
        f.write("""<!DOCTYPE html>
<html>
<head><title>Gatemirror SSG</title></head>
<body>
    <h1>Gatemirror SSG</h1>
    <p>Yapım aşamasında. Yakında içerikler gelecek.</p>
</body>
</html>""")
    print(f"✅ {ana_index} oluşturuldu.")

if __name__ == "__main__":
    dizinleri_olustur()
    print("\n🏁 Tüm dizinler ve index dosyaları oluşturuldu.")
