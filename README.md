# 🚀 Nabulu Talent - Akıllı CV Analiz ve Raporlama Sistemi

Bu sistem, **`cv@nabulu.com.tr`** e-posta adresine gelen CV başvurularını otomatik olarak yakalar, **Gemini Flash Yapay Zekası** ile kreatif ajans dinamiklerine göre anlamlandırıp kategorize eder ve her **Pazartesi saat 10:00'da (TSİ)** ilgililere görsel bir e-posta bülteni olarak raporlar.

---

## 🌟 Temel Yetenekler

1. **Dinamik Ajans Kategorizasyonu (AI):**
   - Sabit kalıplar yerine, Gemini Flash CV'yi ve ön yazıyı okuyarak adayı en uygun ajans disiplinine atar (*Art Director, Video/Motion, Sosyal Medya, Metin Yazarlığı, Medya Planlama, Yazılım, Stajyer vb.*).
2. **Yönetici Özeti & Yetenek Matrisi:**
   - Her aday için 15 saniyede karar vermeyi sağlayan 2-3 cümlelik vurucu Türkçe yönetici özeti, seniority seviyesi (Junior/Mid/Senior) ve öne çıkan araçlar listelenir.
3. **Web Tabanlı CV Önizleme (Preview):**
   - Rapor içerisindeki **"👁️ CV'yi Önizle"** butonuna tıklandığında, tarayıcıda sol panelinde AI özeti ve iletişim butonları, sağ panelinde ise PDF'in kendisi bulunan modern bir önizleme ekranı açılır.
4. **Pazartesi 10:00 Otomasyonu:**
   - `Europe/Istanbul` saat diliminde haftalık bülten otomatik gönderilir ve raporlanan adaylar işaretlenir.

---

## ⚙️ Kurulum ve Ayarlar

Sistemin ayarları `E:\cv-system\.env` dosyasında yer alır:

### ⚠️ Önemli: Google Uygulama Şifresi (App Password)
Google Workspace ve Gmail güvenlik kuralları gereği, IMAP ve SMTP bağlantılarında doğrudan hesap şifresi yerine 16 haneli bir **Uygulama Şifresi** kullanılması zorunludur:

1. `cv@nabulu.com.tr` hesabıyla [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords) adresine gidin.
   *(Eğer 2 Adımlı Doğrulama kapalıysa önce açmanız gerekir).*
2. Uygulama Adı olarak `CV Sistemi` yazıp **Oluştur** butonuna tıklayın.
3. Verilen 16 haneli kodu kopyalayın (örnek: `abcd efgh ijkl mnop`).
4. `E:\cv-system\.env` dosyasındaki `GMAIL_APP_PASSWORD` satırına bu şifreyi yapıştırın.

### .env Dosyası Parametreleri:
```env
GMAIL_USER=cv@nabulu.com.tr
GMAIL_APP_PASSWORD=buraya_16_haneli_uygulama_sifresi
GEMINI_API_KEY=buraya_gemini_api_anahtari
REPORT_RECIPIENTS=ik@nabulu.com.tr,patron@nabulu.com.tr
PREVIEW_BASE_URL=http://localhost:8088
```

> **Not:** Rapor içindeki "CV'yi Önizle" linklerinin ofis dışından veya farklı cihazlardan açılabilmesi için `PREVIEW_BASE_URL` değerine sunucunun yerel IP'si (ör. `http://192.168.1.50:8088`), alan adı veya Cloudflare Tunnel URL'si yazılabilir.

---

## ▶️ Çalıştırma

### 1. Servisi Başlatma (7/24 Arka Plan Modu)
`BASLAT.bat` dosyasına çift tıklayabilir veya PowerShell üzerinden çalıştırabilirsiniz:
```powershell
cd E:\cv-system
py main.py
```

### 2. Hızlı Komutlar (Manuel Testler)
- **Hemen Mailleri Tara:** `py main.py --fetch`
- **Hemen Test Raporu Gönder:** `py main.py --report`
- **Veritabanı İstatistiklerini Gör:** `py main.py --stats`
