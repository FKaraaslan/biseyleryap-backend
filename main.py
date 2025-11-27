import os
import json
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from google import genai
from google.genai import types
from dotenv import load_dotenv

# 1. Ortam değişkenlerini yükle (.env dosyasından)
load_dotenv()

# 2. API Anahtarını Al
api_key = os.environ.get("OPENAI_API_KEY")

if not api_key:
    raise ValueError("API Anahtarı bulunamadı! Lütfen .env dosyasını kontrol edin.")

# 3. Gemini İstemcisini Başlat
client = genai.Client(api_key=api_key)

app = FastAPI()

# ---------------------------------------------------------
# VERİ MODELLERİ (Pydantic) - GÜNCELLENDİ ✅
# ---------------------------------------------------------

class IngredientRequest(BaseModel):
    ingredients: list[str]
    kategori: str
    diet_info: str = "" # YENİ: Diyet bilgisi (Boş olabilir)

class DishRequest(BaseModel):
    dish_name: str
    diet_info: str = "" # YENİ: Diyet bilgisi (Boş olabilir)

# ---------------------------------------------------------
# YARDIMCI FONKSİYONLAR
# ---------------------------------------------------------

def clean_json_response(text: str):
    """
    Gemini bazen cevabı ```json ... ``` blokları arasına alır.
    Bu fonksiyon o blokları temizleyip saf JSON string'i döndürür.
    """
    cleaned_text = text.strip()
    if cleaned_text.startswith("```json"):
        cleaned_text = cleaned_text[7:]
    elif cleaned_text.startswith("```"):
        cleaned_text = cleaned_text[3:]
    
    if cleaned_text.endswith("```"):
        cleaned_text = cleaned_text[:-3]
        
    return cleaned_text.strip()

# ---------------------------------------------------------
# API ENDPOINTLERİ
# ---------------------------------------------------------

# 1. ŞEFİN TAVSİYESİ (MENÜ)
@app.post("/api/chef-recommendation")
async def get_chef_recommendation():
    menu_prompt = (
        "Şu anki mevsime uygun, Türk mutfağından popüler ve birbirini tamamlayan "
        "3 aşamalı bir akşam yemeği menüsü oluştur: 1) Çorba, 2) Ana Yemek, 3) Tatlı. "
        
        "Cevabı SADECE aşağıdaki JSON formatında döndür. Başka hiçbir metin ekleme."
        "JSON Şeması:"
        "{"
        "  'menu': ["
        "    { "
        "      'yemekAdi': '...', "
        "      'aciklama': '...', "
        "      'sure': '...', "
        "      'kalori': '...', "
        "      'malzemeler': ['...'], "
        "      'tarif': ['...'],"
        "      'image_prompt': '[Yemeğin Adı] sunumu yemek fotoğrafı'"
        "    },"
        "    { "
        "      'yemekAdi': '...', "
        "      'aciklama': '...', "
        "      'sure': '...', "
        "      'kalori': '...', "
        "      'malzemeler': ['...'], "
        "      'tarif': ['...'],"
        "      'image_prompt': '[Yemeğin Adı] sunumu yemek fotoğrafı'"
        "    },"
        "    { "
        "      'yemekAdi': '...', "
        "      'aciklama': '...', "
        "      'sure': '...', "
        "      'kalori': '...', "
        "      'malzemeler': ['...'], "
        "      'tarif': ['...'],"
        "      'image_prompt': '[Yemeğin Adı] sunumu yemek fotoğrafı'"
        "    }"
        "  ]"
        "}"
    )

    try:
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=menu_prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )
        
        cleaned_json = clean_json_response(response.text)
        menu_data = json.loads(cleaned_json)
        
        return menu_data

    except Exception as e:
        print(f"HATA (Menu): {e}")
        raise HTTPException(status_code=500, detail=f"Menü oluşturulamadı: {str(e)}")


# 2. TARİF ÜRETME (MALZEMEYE GÖRE) - GÜNCELLENDİ ✅
@app.post("/generate-recipe/")
async def generate_recipe(request: IngredientRequest):
    malzeme_listesi = ", ".join(request.ingredients)
    kategori = request.kategori
    diyet_notu = request.diet_info # Frontend'den gelen diyet bilgisi
    
    recipe_prompt = (
        f"Sen profesyonel bir şefsin. Elimdeki malzemeler: {malzeme_listesi}. "
        f"İstediğim kategori: {kategori}. "
        f"⚠️ DİKKAT EDİLMESİ GEREKEN KISITLAMALAR: {diyet_notu} "
        "Bu malzemelerle (ve varsa kısıtlamalara uyarak) yapılabilecek en iyi ve yaratıcı Türk mutfağı tarifini oluştur. "
        "Eğer kısıtlamalar yüzünden bu malzemeler kullanılamıyorsa, uygun alternatifler önererek tarifi oluştur."
        
        "Cevabı SADECE aşağıdaki JSON formatında döndür:"
        "{"
        "  'yemekAdi': 'Yemeğin Adı',"
        "  'aciklama': 'Kısa, iştah açıcı bir açıklama',"
        "  'sure': 'Hazırlama süresi (örn: 45 dk)',"
        "  'kalori': 'Tahmini kalori (örn: 350 kcal)',"
        "  'malzemeler': ['malzeme1', 'malzeme2', '...'],"
        "  'tarif': ['Adım 1: ...', 'Adım 2: ...', '...'],"
        "  'image_prompt': '[Yemeğin Tam Türkçe Adı] nefis yemek sunumu'"
        "}"
    )

    try:
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=recipe_prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )
        
        cleaned_json = clean_json_response(response.text)
        recipe_data = json.loads(cleaned_json)
        
        return recipe_data

    except Exception as e:
        print(f"HATA (Tarif): {e}")
        raise HTTPException(status_code=500, detail=f"Tarif oluşturulamadı: {str(e)}")


# 3. YEMEK İSMİNDEN TARİF - GÜNCELLENDİ ✅
@app.post("/generate-recipe-by-name/")
async def generate_recipe_by_name(request: DishRequest):
    yemek_ismi = request.dish_name
    diyet_notu = request.diet_info # Frontend'den gelen diyet bilgisi
    
    recipe_prompt = (
        f"Sen profesyonel bir şefsin. Kullanıcı '{yemek_ismi}' yapmak istiyor. "
        f"⚠️ DİKKAT EDİLMESİ GEREKEN KISITLAMALAR: {diyet_notu} "
        "Bu yemek için (varsa kısıtlamalara uyarak) en orijinal ve lezzetli tarifi oluştur. "
        "Örneğin kullanıcı 'Lahmacun' istediyse ama kısıtlamada 'Vegan' varsa, 'Vegan Lahmacun (Mercimekli)' tarifi ver. "
        "Kısıtlama yoksa orijinal tarifi ver."
        
        "Cevabı SADECE aşağıdaki JSON formatında döndür:"
        "{"
        "  'yemekAdi': 'Yemeğin Adı (Gerekirse Vegan/Glutensiz ibaresi ekle)',"
        "  'aciklama': 'Kısa, iştah açıcı bir açıklama',"
        "  'sure': 'Hazırlama süresi (örn: 45 dk)',"
        "  'kalori': 'Tahmini kalori (örn: 350 kcal)',"
        "  'malzemeler': ['malzeme1', 'malzeme2', '...'],"
        "  'tarif': ['Adım 1: ...', 'Adım 2: ...', '...'],"
        "  'image_prompt': '[Yemeğin Tam Türkçe Adı] nefis yemek sunumu'"
        "}"
    )

    try:
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=recipe_prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )
        cleaned_json = clean_json_response(response.text)
        return json.loads(cleaned_json)

    except Exception as e:
        print(f"HATA (İsimden Tarif): {e}")
        raise HTTPException(status_code=500, detail=f"Tarif oluşturulamadı: {str(e)}")

# Dosya doğrudan çalıştırılırsa sunucuyu başlat
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)