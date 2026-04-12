import json
import pandas as pd
import os

def export_clusters_to_excel():
    """clusters.json dosyasını Excel'e dönüştürür"""
    
    json_path = "bots/clusters.json"
    excel_path = "clusters_export.xlsx"
    
    if not os.path.exists(json_path):
        print(f"❌ {json_path} bulunamadı!")
        return
    
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    rows = []
    
    for category, cat_data in data['categories'].items():
        for cluster_name, cluster in cat_data['clusters'].items():
            # Affiliate isimlerini al
            affiliate_list = []
            for aff_id in cluster.get('affiliate_ids', []):
                aff_info = data['affiliates'].get(aff_id, {})
                if aff_info:
                    affiliate_list.append(f"{aff_info.get('name', aff_id)} ({aff_info.get('commission', 'N/A')})")
                else:
                    affiliate_list.append(f"{aff_id} (Bilgi yok)")
            
            # Zorunlu bölümleri ve yasakları birleştir
            required = "\n".join(cluster.get('required_sections', [])) if cluster.get('required_sections') else "Yok"
            forbidden = "\n".join(cluster.get('forbidden', [])) if cluster.get('forbidden') else "Yok"
            keywords = ", ".join(cluster.get('keywords', [])) if cluster.get('keywords') else "Yok"
            affiliates_str = "\n".join(affiliate_list) if affiliate_list else "Yok"
            affiliate_ids_str = ", ".join(cluster.get('affiliate_ids', [])) if cluster.get('affiliate_ids') else "Yok"
            style_boost = cluster.get('style_boost', 'Yok')
            
            rows.append({
                'Kategori': category.upper(),
                'Cluster Adı': cluster_name,
                'Cluster ID': cluster.get('cluster_id', 'Yok'),
                'Intent': cluster.get('intent', 'Yok'),
                'CPC Min ($)': cluster.get('cpc_min', 'Yok'),
                'CPC Max ($)': cluster.get('cpc_max', 'Yok'),
                'Monetizasyon': cluster.get('monetization', 'Yok'),
                'Affiliate Programları': affiliates_str,
                'Affiliate ID\'leri': affiliate_ids_str,
                'Zorunlu Bölümler': required,
                'Yasaklar': forbidden,
                'Stil Boost': style_boost,
                'Anahtar Kelimeler': keywords
            })
    
    df = pd.DataFrame(rows)
    df.to_excel(excel_path, index=False, engine='openpyxl')
    
    print(f"✅ Excel dosyası oluşturuldu: {excel_path}")
    print(f"📊 Toplam {len(rows)} cluster tabloya eklendi.")
    return excel_path

if __name__ == "__main__":
    export_clusters_to_excel()
