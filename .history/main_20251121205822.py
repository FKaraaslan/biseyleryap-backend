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
# Not: Flutter tarafında karışıklık olmasın diye .env içinde "OPENAI_API_KEY" adını kullanmıştık.
# Aslında bu değişken senin GEMINI anahtarını tutuyor.
api_key = os.environ.get("OPENAI_API_KEY")

if not api_key:
    raise ValueError("API Anahtarı bulunamadı! Lütfen .env dosyasını kontrol edin.")

# 3. Gemini İstemcisini Başlat
client = genai.Client(api_key=api_key)

app = FastAPI()

# ---------------------------------------------------------
# VERİ MODELLERİ (Pydantic)
# ---------------------------------------------------------

# Flutter'dan gelen malzeme isteği modeli
class IngredientRequest(BaseModel):
    ingredients: list[str]
    kategori: str

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

# 1. ŞEFİN TAVSİYESİ (MENÜ) ENDPOINT'İ
@app.post("/api/chef-recommendation")
async def get_chef_recommendation():
    # Prompt: 3 Aşamalı Menü İsteği
    menu_prompt = (
        "Şu anki mevsime uygun, Türk mutfağından popüler ve birbirini tamamlayan "
        "3 aşamalı bir akşam yemeği menüsü oluştur: 1) Çorba, 2) Ana Yemek, 3) Tatlı. "
        
        "Cevabı SADECE aşağıdaki JSON formatında döndür. Başka hiçbir metin ekleme."
        "JSON Şeması:"
        "{"
        "  'menu': ["
        "    { 'yemekAdi': '...', 'aciklama': '...', 'sure': '...', 'kalori': '...', 'malzemeler': ['...'], 'tarif': ['...'] },"
        "    { 'yemekAdi': '...', 'aciklama': '...', 'sure': '...', 'kalori': '...', 'malzemeler': ['...'], 'tarif': ['...'] },"
        "    { 'yemekAdi': '...', 'aciklama': '...', 'sure': '...', 'kalori': '...', 'malzemeler': ['...'], 'tarif': ['...'] }"
        "  ]"
        "}"
    )

    try:
        response = client.models.generate_content(
            model='gemini-2.0-flash', # Hızlı ve güncel model
            contents=menu_prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json" # Cevabın JSON olmasını zorlar
            )
        )
        
        # Cevabı temizle ve JSON'a çevir
        cleaned_json = clean_json_response(response.text)
        menu_data = json.loads(cleaned_json)
        
        return menu_data

    except Exception as e:
        print(f"HATA (Menu): {e}")
        raise HTTPException(status_code=500, detail=f"Menü oluşturulamadı: {str(e)}")


# 2. TARİF ÜRETME (MALZEMEYE GÖRE) ENDPOINT'İ
@app.post("/generate-recipe/")
async def generate_recipe(request: IngredientRequest):
    malzeme_listesi = ", ".join(request.ingredients)
    kategori = request.kategori
    
    # Prompt: Tekil Tarif İsteği
    recipe_prompt = (
        f"Sen profesyonel bir şefsin. Elimdeki malzemeler: {malzeme_listesi}. "
        f"İstediğim kategori: {kategori}. "
        "Bu malzemelerle yapılabilecek en iyi ve yaratıcı Türk mutfağı tarifini oluştur. "
        
        "Cevabı SADECE aşağıdaki JSON formatında döndür:"
        "{"
        "  'yemekAdi': 'Yemeğin Adı',"
        "  'aciklama': 'Kısa, iştah açıcı bir açıklama',"
        "  'sure': 'Hazırlama süresi (örn: 45 dk)',"
        "  'kalori': 'Tahmini kalori (örn: 350 kcal)',"
        "  'malzemeler': ['malzeme1', 'malzeme2', '...'],"
        "  'tarif': ['Adım 1: ...', 'Adım 2: ...', '...']"
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

# Sunucuyu doğrudan bu dosyadan başlatmak istersen:
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)