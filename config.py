import os
from pathlib import Path
from dotenv import load_dotenv

# Proje ana dizini
BASE_DIR = Path(__file__).resolve().parent

# .env dosyasını yükle
load_dotenv(BASE_DIR / ".env")

# Gmail Yapılandırması
GMAIL_USER = os.getenv("GMAIL_USER", "cv@nabulu.com.tr")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "").strip()
IMAP_SERVER = "imap.gmail.com"
IMAP_PORT = 993
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

# AI Yapılandırması
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = "gemini-3.1-flash-lite"

# Rapor Alıcıları
REPORT_RECIPIENTS = [email.strip() for email in os.getenv("REPORT_RECIPIENTS", "").split(",") if email.strip()]

# Web Önizleme Sunucusu
WEB_PREVIEW_HOST = os.getenv("WEB_PREVIEW_HOST", "0.0.0.0")
WEB_PREVIEW_PORT = int(os.getenv("PORT", os.getenv("WEB_PREVIEW_PORT", "8088")))
# Render canlı sunucu URL'si (Asla e-postada localhost gitmemesi için varsayılan)
DEFAULT_PUBLIC_URL = "https://nabulu-cv.onrender.com"
CLOUD_URL = os.getenv("RENDER_EXTERNAL_URL") or os.getenv("RAILWAY_STATIC_URL") or DEFAULT_PUBLIC_URL
PREVIEW_BASE_URL = os.getenv("PREVIEW_BASE_URL", CLOUD_URL).rstrip("/")
if "localhost" in PREVIEW_BASE_URL or "127.0.0.1" in PREVIEW_BASE_URL:
    PREVIEW_BASE_URL = DEFAULT_PUBLIC_URL

# Zamanlama
CHECK_INTERVAL_MINUTES = int(os.getenv("CHECK_INTERVAL_MINUTES", "15"))
REPORT_DAY_OF_WEEK = os.getenv("REPORT_DAY_OF_WEEK", "mon")
REPORT_HOUR = int(os.getenv("REPORT_HOUR", "10"))
REPORT_MINUTE = int(os.getenv("REPORT_MINUTE", "0"))
TIMEZONE = os.getenv("TIMEZONE", "Europe/Istanbul")

# Dizin Yolları
STORAGE_DIR = BASE_DIR / "storage" / "cvs"
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "cv_database.db"
TEMPLATES_DIR = BASE_DIR / "templates"

# Dizinlerin varlığını garanti altına al
STORAGE_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)
TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
