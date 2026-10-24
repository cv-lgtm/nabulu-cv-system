import sys
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from collections import defaultdict
from typing import List, Dict, Any

from config import (
    GMAIL_USER, GMAIL_APP_PASSWORD, SMTP_SERVER, SMTP_PORT,
    REPORT_RECIPIENTS, PREVIEW_BASE_URL
)
from database import get_unreported_cvs, mark_cvs_as_reported

def build_report_html(cv_list: List[Dict[str, Any]], period_title: str) -> str:
    # Aday bazlı tekilleştirme (aynı aday birden fazla mail atmışsa son kaydı al)
    unique_cvs = {}
    for cv in cv_list:
        dedup_key = (cv.get("candidate_email") or "").lower().strip() or (cv.get("candidate_name") or "").lower().strip()
        if dedup_key:
            unique_cvs[dedup_key] = cv
        else:
            unique_cvs[cv.get("id")] = cv

    cv_list = list(unique_cvs.values())
    total_count = len(cv_list)
    
    # Kategorilere göre grupla
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for cv in cv_list:
        cat = cv.get("category") or "Genel Başvuru"
        grouped[cat].append(cv)

    # İstatistik kartları
    cat_badges = ""
    for cat, items in grouped.items():
        cat_badges += f"""
        <div style="background: #ffffff; border: 1px solid #fed7aa; padding: 10px 14px; border-radius: 8px; margin: 4px; display: inline-block;">
            <strong style="color: #431407; font-size: 13px;">{cat}:</strong> 
            <span style="color: #FF5E14; font-weight: bold; font-size: 14px;">{len(items)}</span>
        </div>
        """

    # Kategori bölümleri ve aday kartları
    categories_html = ""
    for cat, items in grouped.items():
        cards_html = ""
        for cv in items:
            name = cv.get("candidate_name") or "İsimsiz Aday"
            seniority = cv.get("seniority") or "Belirtilmemiş"
            experience = cv.get("experience_years") or "-"
            city = cv.get("candidate_city") or "Şehir Belirtilmemiş"
            skills = cv.get("key_skills") or ""
            pros = cv.get("pros") or ""
            cons = cv.get("cons") or ""
            cover_letter = (cv.get("cover_letter") or "").strip()
            summary = cv.get("summary") or "Özet bulunamadı."
            email = cv.get("candidate_email") or ""
            phone = cv.get("candidate_phone") or ""
            portfolio = cv.get("portfolio_links") or ""
            token = cv.get("preview_token")
            preview_url = f"{PREVIEW_BASE_URL}/preview/{token}"

            cover_letter_html = ""
            if cover_letter:
                clean_letter = cover_letter.replace("\n", " ").strip()
                if len(clean_letter) > 350:
                    clean_letter = clean_letter[:350] + "..."
                cover_letter_html = f"""
                <div style="background: #f8fafc; border-left: 3px solid #94a3b8; border-radius: 4px; padding: 8px 12px; margin-top: 8px; font-size: 12.5px; color: #475569;">
                    <div style="font-weight: bold; color: #334155; font-size: 11.5px; text-transform: uppercase; margin-bottom: 2px;">✉️ Adayın E-posta Ön Yazısı & Notu:</div>
                    <span style="font-style: italic;">"{clean_letter}"</span>
                </div>
                """

            pros_html = ""
            if pros:
                pros_items = "".join([f'<li style="margin-bottom: 2px;">{p.strip().lstrip("•").strip()}</li>' for p in pros.split("\n") if p.strip()])
                pros_html = f"""
                <div style="background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 6px; padding: 8px 12px; margin-top: 8px; font-size: 12.5px; color: #166534;">
                    <strong style="color: #15803d;">🟢 Artıları (Güçlü Yönler):</strong>
                    <ul style="margin: 4px 0 0 16px; padding: 0;">{pros_items}</ul>
                </div>
                """

            cons_html = ""
            if cons:
                cons_items = "".join([f'<li style="margin-bottom: 2px;">{c.strip().lstrip("•").strip()}</li>' for c in cons.split("\n") if c.strip()])
                cons_html = f"""
                <div style="background: #fef2f2; border: 1px solid #fecaca; border-radius: 6px; padding: 8px 12px; margin-top: 6px; font-size: 12.5px; color: #991b1b;">
                    <strong style="color: #b91c1c;">🔴 Soru İşaretleri & Eksileri:</strong>
                    <ul style="margin: 4px 0 0 16px; padding: 0;">{cons_items}</ul>
                </div>
                """

            # Yetenek etiketleri
            skill_tags = ""
            if skills:
                for s in skills.split(",")[:6]:
                    if s.strip():
                        skill_tags += f'<span style="background: #e2e8f0; color: #475569; padding: 2px 8px; border-radius: 4px; font-size: 11px; margin-right: 4px; display: inline-block; margin-bottom: 4px;">{s.strip()}</span>'

            # Portfolyo butonu
            portfolio_btn = ""
            if portfolio:
                first_link = portfolio.split(",")[0].strip()
                if first_link:
                    portfolio_btn = f"""
                    <a href="{first_link}" target="_blank" style="background: #ffffff; color: #475569; border: 1px solid #cbd5e1; padding: 7px 12px; border-radius: 6px; text-decoration: none; font-size: 12px; font-weight: 600; margin-left: 6px;">
                        🔗 Portfolyo
                    </a>
                    """

            cards_html += f"""
            <div style="background: #ffffff; border: 1px solid #e2e8f0; border-radius: 10px; padding: 18px; margin-bottom: 14px; box-shadow: 0 1px 3px rgba(0,0,0,0.04);">
                <table style="width: 100%; border-collapse: collapse;">
                    <tr>
                        <td style="vertical-align: top;">
                            <div style="font-size: 16px; font-weight: bold; color: #0f172a;">
                                {name}
                                <span style="background: #fff3ed; color: #ea580c; border: 1px solid #ffedd5; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; margin-left: 6px;">{seniority}</span>
                                <span style="color: #64748b; font-size: 12px; font-weight: normal; margin-left: 6px;">📍 {city} | ⏳ {experience}</span>
                            </div>
                        </td>
                        <td style="text-align: right; vertical-align: top; white-space: nowrap;">
                            <a href="{preview_url}" target="_blank" style="background: #FF5E14; color: #ffffff; padding: 8px 16px; border-radius: 6px; text-decoration: none; font-size: 13px; font-weight: bold; display: inline-block;">
                                👁️ CV'yi Önizle
                            </a>
                            {portfolio_btn}
                        </td>
                    </tr>
                </table>

                <div style="margin-top: 10px; font-size: 13.5px; color: #334155; line-height: 1.5; background: #fffaf7; padding: 10px; border-radius: 6px; border-left: 3px solid #FF5E14;">
                    <strong>AI Yönetici Değerlendirmesi:</strong> {summary}
                </div>
                {cover_letter_html}
                {pros_html}
                {cons_html}

                <div style="margin-top: 10px; display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between;">
                    <div>
                        {skill_tags}
                    </div>
                    <div style="font-size: 12px; color: #64748b; margin-top: 6px;">
                        {f'✉️ {email} ' if email else ''} {f'| 📞 {phone}' if phone else ''}
                    </div>
                </div>
            </div>
            """

        categories_html += f"""
        <div style="margin-top: 24px;">
            <h3 style="color: #1e293b; font-size: 15px; border-bottom: 2px solid #e2e8f0; padding-bottom: 6px; margin-bottom: 12px; text-transform: uppercase; letter-spacing: 0.5px;">
                📁 {cat} <span style="color: #FF5E14; font-size: 13px;">({len(items)} Başvuru)</span>
            </h3>
            {cards_html}
        </div>
        """

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Haftalık CV & Yetenek Bülteni</title>
    </head>
    <body style="font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; background: #f8fafc; margin: 0; padding: 24px; color: #1e293b;">
        <!-- Gmail Preheader & Threading engelleme -->
        <div style="display:none; font-size:1px; color:#f8fafc; line-height:1px; max-height:0px; max-width:0px; opacity:0; overflow:hidden;">
            NABULU - İK Haftalık Yetenek Bülteni: {total_count} yeni başvuru analiz edildi. ({datetime.now().strftime('%H:%M:%S')})
            &nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;
        </div>

        <div style="max-width: 780px; margin: 0 auto; background: #ffffff; border-radius: 12px; overflow: hidden; border: 1px solid #e2e8f0; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);">
            <!-- Header -->
            <div style="background: linear-gradient(135deg, #FF5E14, #FF8A00); padding: 28px 24px; color: white;">
                <div style="font-size: 13px; letter-spacing: 2px; text-transform: uppercase; opacity: 0.95; font-weight: 800;">NABULU - IK</div>
                <h1 style="margin: 6px 0 4px 0; font-size: 24px; font-weight: 800; letter-spacing: -0.5px;">Haftalık CV & Yetenek Bülteni</h1>
                <p style="margin: 0; font-size: 13.5px; opacity: 0.9;">{period_title} dönemi gelen başvuruların AI destekli analizi ve yönetici özeti.</p>
            </div>

            <!-- Dashboard Stats -->
            <div style="padding: 20px 24px; background: #fffaf7; border-bottom: 1px solid #fed7aa;">
                <div style="font-size: 12px; font-weight: bold; color: #9a3412; text-transform: uppercase; margin-bottom: 8px;">
                    📊 Özet Durum (Toplam {total_count} Yeni Aday)
                </div>
                <div>
                    {cat_badges}
                </div>
            </div>

            <!-- Content -->
            <div style="padding: 24px;">
                {categories_html}
            </div>

            <!-- Footer -->
            <div style="padding: 16px 24px; background: #f8fafc; border-top: 1px solid #e2e8f0; font-size: 12px; color: #64748b; text-align: center;">
                Bu rapor <strong>cv@nabulu.com.tr</strong> posta kutusu için çalışan yapay zeka otomasyonu tarafından oluşturulmuştur.<br>
                Her Pazartesi saat 10:00'da otomatik olarak iletilir.
            </div>
        </div>
    </body>
    </html>
    """
    return html

def send_weekly_report(force: bool = False) -> bool:
    """
    Raporlanmamış CV'leri çeker, HTML bülten üretir ve belirtilen alıcılara gönderir.
    """
    unreported = get_unreported_cvs()
    
    if not unreported and not force:
        print("[*] Raporlanacak yeni CV bulunamadı.")
        return False

    if not unreported and force:
        print("[*] Test modu: Kayıtlı CV yok, boş şablon gönderiliyor.")
        unreported = []

    if not REPORT_RECIPIENTS:
        print("[-] Rapor alıcı listesi (REPORT_RECIPIENTS) boş!")
        return False

    now_str = datetime.now().strftime("%d.%m.%Y")
    # Gmail'in aynı gün atılan mailleri gruplayıp "..." içine gizlemesini (threading) önlemek için benzersiz zaman damgası
    time_suffix = datetime.now().strftime("%H:%M")
    subject = f"NABULU - İK | Haftalık CV & Yetenek Bülteni - {now_str} [{time_suffix}] ({len(unreported)} Aday)"
    period_title = f"{now_str} Haftası"
    html_content = build_report_html(unreported, period_title)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"Nabulu Talent <{GMAIL_USER}>"
    msg["To"] = ", ".join(REPORT_RECIPIENTS)

    msg.attach(MIMEText(html_content, "html", "utf-8"))

    if not GMAIL_APP_PASSWORD or GMAIL_APP_PASSWORD == "Qaz*0987":
        print("[-] UYARI: E-posta gönderimi için 16 haneli Google Uygulama Şifresi gereklidir.")
        return False

    try:
        print(f"[*] Rapor gönderiliyor: {REPORT_RECIPIENTS}...")
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        server.sendmail(GMAIL_USER, REPORT_RECIPIENTS, msg.as_string())
        server.quit()
        print(f"[✓] Rapor başarıyla gönderildi!")

        # Raporlandı olarak işaretle
        ids = [cv["id"] for cv in unreported]
        mark_cvs_as_reported(ids)
        return True
    except Exception as e:
        print(f"[-] Rapor gönderme hatası: {e}")
        return False

if __name__ == "__main__":
    send_weekly_report(force=False)
