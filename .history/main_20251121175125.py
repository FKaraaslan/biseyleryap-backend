import os
import json
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from google import genai # ⬅️ Yeni: Gemini kütüphanesi
from dotenv import load_dotenv
import random # Rastgele seçim için ekleyin

# .env dosyasını yükle (Gemini anahtarını okuyacak)
load_dotenv()

# Gemini istemcisini API anahtarı ile başlat
client = genai.Client(
    api_key=os.environ.get("OPENAI_API_KEY") 
)

app = FastAPI()

# Gelen/Giden Veri Yapıları aynı kalıyor
class IngredientRequest(BaseModel):
    ingredients: list[str]
    kategori: str # ⬅️ Yeni: Kategori alanı eklendi

class Recipe(BaseModel):
    yemekAdi: str
    aciklama: str
    sure: str
    kalori: str
    malzemeler: list[str]
    tarif: list[str]

# Şefin Tavsiyesi için basit bir rastgele tarife dönen endpoint
@app.post("/api/chef-recommendation")
async def get_chef_recommendation():
    # 🚨 Adım 1: Gemini'ye rastgele bir tarif sorduracak prompt'u hazırlayın
    # Veya daha basit bir test için: Direkt JSON döndürün.
    
    # 💡 Gerçekçi bir Gemini çağrısı (Siz bunu uygulayacaksınız)
    menu_prompt = (
        "Şu anki mevsime uygun, popüler ve birbirini tamamlayan, üç aşamalı bir akşam yemeği menüsü oluştur. "
        "Menü: 1) Çorba, 2) Ana Yemek, 3) Tatlı. "
        "Her bir yemek için gerekli tüm tarif bilgilerini (yemekAdi, aciklama, süre, kalori, malzemeler, tarif) "
        "kullanarak TEK bir JSON objesi döndür. JSON objesi, 'menu' adında ana bir liste içermelidir. "
        "Bu liste içinde sırasıyla Çorba, Ana Yemek ve Tatlı tarifleri yer almalıdır."
        
        # 💡 İstenen JSON Yapısı:
        # {
        #   "menu": [
        #     { "yemekAdi": "Mercimek Çorbası", ... }, // Çorba
        #     { "yemekAdi": "Hünkar Beğendi", ... }, // Ana Yemek
        #     { "yemekAdi": "Sütlaç", ... } // Tatlı
        #   ]
        # }
    )

    try:
        # Gerçek uygulamada buraya Gemini API çağrısı gelecek:
        # gemini_response = gemini_client.generate_content(recommendation_prompt)
        # recipe_json = json.loads(gemini_response.text.strip())
        
        # 🧪 Şimdilik hızlı test için örnek bir JSON döndürelim:
        dummy_menu = {
            "menu": [
                {
                    "yemekAdi": "Domates Çorbası",
                    "aciklama": "Bol vitaminli ve kremalı domates çorbası.",
                    "sure": "20 Dakika",
                    "kalori": "180 kcal",
                    "malzemeler": ["Domates Salçası", "Un", "Süt", "Tereyağı"],
                    "tarif": ["Tereyağı ve unu kavur.", "Salçayı ekle ve karıştır.", "Su ve sütü ekleyip kaynat.", "Tuz ve baharat ekleyip servis et."]
                },
                {
                    "yemekAdi": "Fırında Sebzeli Tavuk",
                    "aciklama": "Bütün tavuk ve mevsim sebzeleri ile hazırlanan doyurucu ana yemek.",
                    "sure": "60 Dakika",
                    "kalori": "450 kcal",
                    "malzemeler": ["Bütün Tavuk", "Patates", "Havuç", "Biber", "Kekik"],
                    "tarif": ["Sebzeleri doğra, tavuğu marine et.", "Hepsini fırın tepsisine diz.", "180°C fırında 60 dakika pişir."]
                },
                {
                    "yemekAdi": "Supangle",
                    "aciklama": "Çikolatalı ve soğuk, hafif bir tatlı alternatifi.",
                    "sure": "45 Dakika",
                    "kalori": "300 kcal",
                    "malzemeler": ["Süt", "Şeker", "Kakao", "Un", "Yumurta Sarısı"],
                    "tarif": ["Tüm malzemeleri karıştırıp ocakta pişir.", "Kaselere paylaştır ve soğut.", "Üzerini çikolata sosuyla süsle."]
                }
            ]
        }
        
        return dummy_menu # Artık Menüyü döndürüyoruz

    except Exception as e:
        # Hata durumunda 500 status kodu döndürün
        raise HTTPException(status_code=500, detail=f"Menü üretilirken hata oluştu: {str(e)}")

# ... (diğer endpointleriniz, örneğin /generate-recipe/ burada olmalı)
# 👩‍🍳 Ana API Endpoint'i: Tarif Üretme
@app.post("/generate-recipe/", response_model=Recipe)
def generate_recipe(request: IngredientRequest):
    malzeme_listesi = ", ".join(request.ingredients)
    
    # Sisteme vereceğimiz talimat (Prompt)
    system_prompt = (
        f"Sen, profesyonel, yaratıcı ve detaycı bir şefsin. Senden istenen tarifin türü: '{request.kategori}'. " # ⬅️ Kategori Prompt'a Eklendi
        "Verilen malzemelerin ve temel mutfak gereçlerinin (tuz, yağ, karabiber vb.) ötesine geçme. "
        "Tarif adımlarını **kısa, net ve numaralandırılmış** adımlar halinde listele. "
        "Yemek adını (yemekAdi) her zaman büyük harflerle başlat. "
        "Cevabını sadece Türkçe JSON formatında ve tam olarak şu şemaya uygun ver: "
        "{'yemekAdi': '...', 'aciklama': '...', 'sure': '...', 'kalori': '...', 'malzemeler': ['...'], 'tarif': ['...']}"
    )

    try:
        # ⬅️ YENİ: Gemini API Çağrısı
        response = client.models.generate_content(
            model='gemini-2.5-flash', # Hızlı ve uygun maliyetli model
            contents=[
                {"role": "user", "parts": [
                    {"text": system_prompt + f" Elindeki malzemeler şunlar: {malzeme_listesi}. Sadece JSON dön."}
                ]}
            ]
        )
        
        # Gemini'dan gelen cevabın etrafındaki markdown kodlarını temizle
        raw_json_text = response.text.strip().replace('```json', '').replace('```', '')
        recipe_data = json.loads(raw_json_text)
        
        # Gelen veride en azından ana alanların varlığını kontrol et
        if 'yemekAdi' not in recipe_data or 'tarif' not in recipe_data:
             raise ValueError("Gemini'dan beklenen formatta JSON alınamadı.")

        return recipe_data
        
    except (json.JSONDecodeError, ValueError, Exception) as e:
        # Hata yakalama ve güvenli cevap gönderme bloğu
        print(f"HATA: Gemini cevabının işlenmesi başarısız oldu: {e}")
        
        return {
            "yemekAdi": "Tarif Oluşturulamadı",
            "aciklama": "AI şef şu anda meşgul. Lütfen daha belirgin malzemeler girin.",
            "sure": "0 Dakika",
            "kalori": "0 kcal",
            "malzemeler": ["Hata: Eksik format"],
            "tarif": ["Yapay zeka, çıktıyı doğru formatta vermedi veya bağlantı kesildi."]
        }