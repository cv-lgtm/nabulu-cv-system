import sys
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

import threading
import time
from database import init_db, get_stats
from config import GMAIL_USER, REPORT_RECIPIENTS, WEB_PREVIEW_PORT, PREVIEW_BASE_URL
from mail_fetcher import fetch_and_process_emails
from report_generator import send_weekly_report
from web_preview import run_preview_server
from scheduler import setup_scheduler

def show_banner():
    print("=" * 65)
    print("      NABULU TALENT - AKILLI CV ANALIZ & RAPORLAMA SERVISI    ")
    print("=" * 65)
    print(f"[*] İzlenen Mail   : {GMAIL_USER}")
    print(f"[*] Rapor Alıcıları: {', '.join(REPORT_RECIPIENTS) if REPORT_RECIPIENTS else 'Tanımlanmadı!'}")
    print(f"[*] Önizleme URL   : {PREVIEW_BASE_URL} (Port: {WEB_PREVIEW_PORT})")
    print(f"[*] Zamanlama      : Her Pazartesi Saat 10:00 (Europe/Istanbul)")
    print("=" * 65)

def print_stats():
    stats = get_stats()
    print("\n--- MEVCUT CV HAVUZU İSTATİSTİKLERİ ---")
    print(f"Toplam Kayıtlı CV    : {stats['total']}")
    print(f"Rapor Bekleyen CV    : {stats['pending']}")
    print("\nKategori Dağılımı:")
    if not stats['categories']:
        print("  Henüz kayıtlı kategori bulunmuyor.")
    for cat in stats['categories']:
        print(f"  • {cat['category']}: {cat['count']} aday")
    print("---------------------------------------\n")

def main():
    init_db()

    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()
        if arg in ["--fetch", "-f"]:
            print("[*] Yeni e-postalar tek seferlik taranıyor...")
            count = fetch_and_process_emails()
            print(f"[OK] Tamamlandi. {count} yeni CV islendi.")
            return
        elif arg in ["--report", "-r"]:
            print("[*] Haftalik rapor zorla gonderiliyor...")
            success = send_weekly_report(force=True)
            print("[OK] Rapor islemi bitti." if success else "[-] Rapor gonderilemedi.")
            return
        elif arg in ["--stats", "-s"]:
            print_stats()
            return
        elif arg in ["--help", "-h"]:
            print("Kullanım:")
            print("  py main.py          : Servisi başlatır (Arka plan zamanlayıcı + Web önizleme)")
            print("  py main.py --fetch  : Yeni mailleri hemen tara ve analiz et")
            print("  py main.py --report : Raporu hemen derle ve e-posta ile gönder")
            print("  py main.py --stats  : Veritabanındaki CV istatistiklerini göster")
            return

    show_banner()
    print_stats()

    # 1. Web önizleme sunucusunu arka planda başlat
    preview_thread = threading.Thread(target=run_preview_server, daemon=True)
    preview_thread.start()

    # Eksik PDF dosyalarını arka planda önbelleğe al
    from mail_fetcher import sync_missing_attachments_in_background
    sync_missing_attachments_in_background()

    # 2. Zamanlayıcıyı başlat
    scheduler = setup_scheduler()
    scheduler.start()
    print("[+] Otomasyon zamanlayıcısı başlatıldı.")
    print("[*] Servis 7/24 çalışıyor. Çıkmak için CTRL+C tuşlayınız...\n")

    # İlk başlangıçta hemen bir kontrol yap
    try:
        fetch_and_process_emails()
    except Exception as e:
        print(f"[-] İlk tarama uyarısı: {e}")

    try:
        while True:
            time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        print("\n[*] Servis kapatılıyor...")
        scheduler.shutdown()
        print("[✓] Güvenle kapatıldı.")

if __name__ == "__main__":
    main()
