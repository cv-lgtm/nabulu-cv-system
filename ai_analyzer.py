import json
import base64
import requests
from pathlib import Path
from typing import Dict, Any
from pypdf import PdfReader
from docx import Document
from config import GEMINI_API_KEY, GEMINI_MODEL

def extract_text_from_file(file_path: Path) -> str:
    suffix = file_path.suffix.lower()
    text = ""
    try:
        if suffix == ".pdf":
            reader = PdfReader(str(file_path))
            for page in reader.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n"
        elif suffix in [".docx", ".doc"]:
            doc = Document(str(file_path))
            for p in doc.paragraphs:
                text += p.text + "\n"
        elif suffix in [".txt"]:
            text = file_path.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        print(f"[-] Metin çıkarma uyarısı ({file_path.name}): {e}")
    return text.strip()

def analyze_cv(file_path: Path, email_subject: str = "", email_body: str = "") -> Dict[str, Any]:
    """
    CV dosyasını ve varsa mail içeriğini Gemini Flash ile analiz eder.
    Dinamik ajans kategorizasyonu ve özet çıkarır.
    """
    file_path = Path(file_path)
    extracted_text = extract_text_from_file(file_path)
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
    headers = {"Content-Type": "application/json"}
    
    prompt = f"""
Sen bir kreatif reklam ve dijital pazarlama ajansının son derece deneyimli, eleştirel ve tarafsız İnsan Kaynakları & Yetenek Direktörüsün.
Sana gelen iş başvurusunu (CV ve/veya mail metni) detaylıca inceleyeceksin.

ÖNEMLİ DEĞERLENDİRME VE ÜSLUP KURALLARI:
1. Adayı sadece övme ve sadece olumlu yönlerine odaklanma! Ajans yöneticilerinin doğru karar verebilmesi ve zaman kaybetmemesi için adayın hem GÜÇLÜ YÖNLERİNİ (Pros) hem de EKSİKLERİNİ / ŞÜPHE UYANDIRAN NOKTALARINI (Cons) objektif ve net bir dille ortaya koy.
2. BAŞKA AJANSLARI ASLA ÖVME VE YÜCELTME! "Köklü", "ileri gelen", "sektörün önde gelen", "prestijli", "büyük ölçekli" gibi övgü dolu sıfatları kesinlikle KULLANMA. Diğer ajanslardan bahsederken yalnızca yalın ve nesnel ifadeler kullan (Örn: "önceki ajans geçmişinde", "2 yıllık ajans tecrübesi").
3. Adayın çalıştığı yerlerin isimlerine/etiketlerine değil; bizzat kendi ürettiği işe, sorumluluklarına, teknik/yaratıcı çıktılarına ve Nabulu Ajans standartlarına uygunluğuna odaklan.

GELEN BİLGİLER:
E-posta Konusu: {email_subject}
E-posta Ön Yazısı: {email_body[:1000]}
CV Metni (varsa):
{extracted_text[:12000]}

GÖREVLERİN:
1. Adayın iletişim bilgilerini çıkar (Ad-Soyad, e-posta, telefon, şehir).
2. Adayın uzmanlığına göre dinamik AJANS KATEGORİSİ belirle.
3. Seniority (Kıdem): "Stajyer", "Junior", "Mid-Level", "Senior", "Lead / Direktör".
4. Toplam tahmini deneyim yılı (Örn: "3 Yıl", "6 Ay", "Yeni Mezun").
5. En belirgin 4-6 yetenek/araç (Örn: Figma, After Effects, Meta Ads, Premiere, SEO vb.).
6. Portfolyo linkleri (Behance, Dribbble, GitHub, Vimeo, Kişisel Site, LinkedIn vb.).
7. GÜÇLÜ YÖNLER / ARTILARI (pros): Adayın belirgin 2-3 güçlü yönü (ajans geçmişi, somut yetkinlikleri, araç hakimiyeti vb. Başka ajansları övücü sıfatlar kullanmadan yalın şekilde ifade et).
8. DİKKAT EDİLMESİ GEREKENLER / EKSİLERİ (cons): Adayın 1-3 belirgin eksiği veya soru işareti (Örn: sık iş değiştirme, portfolyo sunulmaması, ajans tecrübesi eksikliği, araçların yüzeysel kalması, rol için fazla/az deneyim vb.).
9. ADAYIN ÖN YAZI / MAİL NOTLARI (candidate_notes): E-posta gövdesinde adayın belirttiği özel detaylar varsa (Örn: Maaş beklentisi, ne zaman başlayabileceği/ihbar süresi, motivasyonu, çalışma modeli tercihi vb.). Yoksa boş bırak.
10. YÖNETİCİ ÖZETİ (summary): Başka ajanslara paye vermeden, adayın somut yeteneklerini ve risklerini tartan, Nabulu için uygunluğunu net bir dille özetleyen 2-3 cümlelik tarafsız yönetici değerlendirmesi.

YANIT FORMATI:
Aşağıdaki JSON şemasına kesinlikle sadık kal. Sadece saf JSON döndür, markdown formatında tırnak işareti (```json) kullanma.

{{
  "candidate_name": "Ad Soyad",
  "candidate_email": "aday@email.com",
  "candidate_phone": "05xx xxx xx xx",
  "candidate_city": "İstanbul",
  "category": "Kategori Adı",
  "seniority": "Junior / Mid-Level / Senior / Stajyer",
  "experience_years": "X Yıl",
  "key_skills": ["Yetenek 1", "Yetenek 2"],
  "pros": ["Artı yön 1", "Artı yön 2"],
  "cons": ["Eksi/risk yön 1", "Eksi/risk yön 2"],
  "candidate_notes": "Adayın mailinde belirttiği başlangıç tarihi, motivasyon, maaş beklentisi vb. notlar.",
  "summary": "Hem artıları hem eksileri içeren 2-3 cümlelik dengeli yönetici özeti.",
  "portfolio_links": ["https://..."]
}}
"""

    parts = [{"text": prompt}]
    
    # Eğer metin çıkarılamadıysa (taranmış görsel PDF ise), dosyayı multimodal olarak gönder
    if len(extracted_text) < 50 and file_path.suffix.lower() == ".pdf":
        try:
            with open(file_path, "rb") as f:
                pdf_bytes = f.read()
                base64_data = base64.b64encode(pdf_bytes).decode("utf-8")
                parts.append({
                    "inlineData": {
                        "mimeType": "application/pdf",
                        "data": base64_data
                    }
                })
        except Exception as e:
            print(f"[-] PDF base64 okuma hatası: {e}")

    payload = {
        "contents": [{"parts": parts}],
        "generationConfig": {
            "temperature": 0.2,
            "responseMimeType": "application/json"
        }
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()
        raw_text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
        
        # Temizleme
        if raw_text.startswith("```json"):
            raw_text = raw_text[7:]
        if raw_text.endswith("```"):
            raw_text = raw_text[:-3]
        parsed = json.loads(raw_text.strip())
        
        # Formatlama
        if isinstance(parsed.get("key_skills"), list):
            parsed["key_skills"] = ", ".join(parsed["key_skills"])
        if isinstance(parsed.get("pros"), list):
            parsed["pros"] = " • " + "\n • ".join(parsed["pros"])
        if isinstance(parsed.get("cons"), list):
            parsed["cons"] = " • " + "\n • ".join(parsed["cons"])
        if isinstance(parsed.get("portfolio_links"), list):
            parsed["portfolio_links"] = ", ".join(parsed["portfolio_links"])
            
        return parsed
    except Exception as e:
        print(f"[-] Gemini AI Analiz Hatası: {e}")
        return {
            "candidate_name": file_path.stem.replace("_", " ").title(),
            "candidate_email": "",
            "candidate_phone": "",
            "candidate_city": "",
            "category": "Genel Başvuru",
            "seniority": "Belirtilmemiş",
            "experience_years": "Belirtilmemiş",
            "key_skills": "Otomatik analiz edilemedi",
            "pros": "",
            "cons": "",
            "summary": "CV içeriği otomatik olarak okunamadı, ekteki orijinal dosyayı inceleyiniz.",
            "portfolio_links": ""
        }
