import sys
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

import imaplib
import email
from email.header import decode_header
import re
import uuid
from pathlib import Path
from datetime import datetime
from typing import List, Tuple

from config import (
    GMAIL_USER, GMAIL_APP_PASSWORD, IMAP_SERVER, IMAP_PORT, STORAGE_DIR
)
from database import is_message_processed, save_cv_record
from ai_analyzer import analyze_cv

def clean_header_str(value: str) -> str:
    if not value:
        return ""
    decoded_list = decode_header(value)
    result = []
    for text, encoding in decoded_list:
        if isinstance(text, bytes):
            result.append(text.decode(encoding or "utf-8", errors="ignore"))
        else:
            result.append(str(text))
    return "".join(result).strip()

def sanitize_filename(filename: str) -> str:
    # Geçersiz karakterleri temizle
    cleaned = re.sub(r'[\\/*?:"<>|]', "", filename)
    return cleaned.replace(" ", "_")

def fetch_and_process_emails() -> int:
    """
    Gmail kutusundan yeni e-postaları çeker, CV eklerini indirir,
    Gemini ile analiz edip veritabanına kaydeder.
    """
    if not GMAIL_APP_PASSWORD or GMAIL_APP_PASSWORD == "Qaz*0987":
        print("[-] UYARI: Google Uygulama Şifresi (16 haneli App Password) henüz girilmedi.")
        return 0

    print(f"[*] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Gmail kontrol ediliyor ({GMAIL_USER})...")
    
    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
        mail.login(GMAIL_USER, GMAIL_APP_PASSWORD)
    except Exception as e:
        print(f"[-] Gmail IMAP Giriş Hatası: {e}")
        return 0

    mail.select("INBOX")
    
    # Okunmamış veya son mailleri tara
    status, messages = mail.search(None, 'UNSEEN')
    if status != 'OK' or not messages[0]:
        # Eğer okunmamış yoksa, son 10 maile bak (zaten işlenmiş olanları atlayacak)
        status, messages = mail.search(None, 'ALL')
        msg_ids = messages[0].split()[-15:] if messages[0] else []
    else:
        msg_ids = messages[0].split()

    if not msg_ids:
        print("[*] İncelenecek yeni e-posta bulunamadı.")
        mail.logout()
        return 0

    processed_count = 0

    for msg_id in msg_ids:
        try:
            status, data = mail.fetch(msg_id, '(RFC822)')
            if status != 'OK':
                continue

            raw_email = data[0][1]
            msg = email.message_from_bytes(raw_email)

            message_id = clean_header_str(msg.get("Message-ID", ""))
            if not message_id:
                message_id = f"gen-{uuid.uuid4()}"

            if is_message_processed(message_id):
                continue

            subject = clean_header_str(msg.get("Subject", "Konusuz Başvuru"))
            sender = clean_header_str(msg.get("From", ""))
            date_str = clean_header_str(msg.get("Date", ""))

            # Gönderen e-posta adresini ayıkla
            sender_email_match = re.search(r'<([^>]+)>', sender)
            sender_email = sender_email_match.group(1) if sender_email_match else sender
            sender_name = re.sub(r'<[^>]+>', '', sender).strip()

            body_text = ""
            attachments: List[Tuple[str, bytes]] = []

            if msg.is_multipart():
                for part in msg.walk():
                    content_type = part.get_content_type()
                    content_disposition = str(part.get("Content-Disposition", ""))

                    if content_type == "text/plain" and "attachment" not in content_disposition:
                        payload = part.get_payload(decode=True)
                        if payload:
                            body_text += payload.decode(part.get_content_charset() or "utf-8", errors="ignore")
                    elif "attachment" in content_disposition or part.get_filename():
                        filename = clean_header_str(part.get_filename() or "")
                        if filename:
                            payload = part.get_payload(decode=True)
                            if payload:
                                attachments.append((filename, payload))
            else:
                payload = msg.get_payload(decode=True)
                if payload:
                    body_text = payload.decode(msg.get_content_charset() or "utf-8", errors="ignore")

            # CV eklerini filtrele (.pdf, .docx, .doc)
            valid_attachments = [
                (fn, content) for fn, content in attachments
                if Path(fn).suffix.lower() in [".pdf", ".docx", ".doc"]
            ]

            if not valid_attachments:
                # CV eki olmayan e-postaları atla
                continue

            for original_filename, file_bytes in valid_attachments:
                if is_message_processed(message_id, original_filename):
                    continue

                safe_name = sanitize_filename(original_filename)
                unique_name = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}_{safe_name}"
                saved_path = STORAGE_DIR / unique_name

                with open(saved_path, "wb") as f:
                    f.write(file_bytes)

                print(f"[+] Yeni CV İndirildi: {original_filename} ({sender_name})")
                print(f"[*] Gemini AI ile analiz ediliyor...")

                # AI Analizi
                analysis = analyze_cv(saved_path, email_subject=subject, email_body=body_text)

                # Veritabanına kaydet
                record = {
                    "message_id": f"{message_id}_{saved_path.stem}",
                    "sender_email": sender_email,
                    "sender_name": sender_name,
                    "subject": subject,
                    "received_date": date_str,
                    "candidate_name": analysis.get("candidate_name", sender_name),
                    "candidate_email": analysis.get("candidate_email") or sender_email,
                    "candidate_phone": analysis.get("candidate_phone", ""),
                    "candidate_city": analysis.get("candidate_city", ""),
                    "category": analysis.get("category", "Genel Başvuru"),
                    "seniority": analysis.get("seniority", "Belirtilmemiş"),
                    "experience_years": analysis.get("experience_years", "Belirtilmemiş"),
                    "key_skills": analysis.get("key_skills", ""),
                    "pros": analysis.get("pros", ""),
                    "cons": analysis.get("cons", ""),
                    "cover_letter": body_text.strip()[:2000],
                    "summary": analysis.get("summary", ""),
                    "portfolio_links": analysis.get("portfolio_links", ""),
                    "file_name": original_filename,
                    "file_path": str(saved_path),
                    "status": "processed"
                }

                save_cv_record(record)
                processed_count += 1
                name_disp = record.get('candidate_name', '')
                cat_disp = record.get('category', '')
                sen_disp = record.get('seniority', '')
                print(f"[OK] Basariyla kaydedildi: {name_disp} -> {cat_disp} ({sen_disp})")

        except Exception as e:
            print(f"[-] E-posta işleme hatası: {e}")

    try:
        mail.close()
        mail.logout()
    except Exception:
        pass

    return processed_count

if __name__ == "__main__":
    fetch_and_process_emails()
