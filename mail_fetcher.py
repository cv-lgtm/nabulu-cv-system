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
import zipfile
import io
from PIL import Image
from pathlib import Path
from datetime import datetime
from typing import List, Tuple, Optional

def handle_attachment_conversion(filename: str, file_bytes: bytes) -> Tuple[str, bytes]:
    """
    Apple Pages (.pages) veya gorsel dosyalarini PDF'e cevirir.
    """
    suffix = Path(filename).suffix.lower()
    if suffix == ".pages":
        try:
            z = zipfile.ZipFile(io.BytesIO(file_bytes))
            for candidate in ["preview.jpg", "preview-web.jpg", "QuickLook/Preview.pdf"]:
                if candidate in z.namelist():
                    extracted_bytes = z.read(candidate)
                    if candidate.endswith(".pdf"):
                        return (Path(filename).stem + ".pdf", extracted_bytes)
                    img = Image.open(io.BytesIO(extracted_bytes)).convert("RGB")
                    pdf_buf = io.BytesIO()
                    img.save(pdf_buf, format="PDF")
                    return (Path(filename).stem + ".pdf", pdf_buf.getvalue())
        except Exception as e:
            print(f"[-] .pages donusturme uyarisi: {e}")
    return (filename, file_bytes)

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
    
    # Okunmamış veya son 50 e-postayı tara (zaten işlenmiş olanları atlayacak)
    status_unseen, unseen_msgs = mail.search(None, 'UNSEEN')
    status_all, all_msgs = mail.search(None, 'ALL')
    
    id_set = set()
    if status_unseen == 'OK' and unseen_msgs[0]:
        id_set.update(unseen_msgs[0].split())
    if status_all == 'OK' and all_msgs[0]:
        id_set.update(all_msgs[0].split()[-50:])
    
    msg_ids = sorted(list(id_set), key=lambda x: int(x) if x.isdigit() else 0)

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

            # CV eklerini filtrele (.pdf, .docx, .doc, .pages)
            valid_attachments = [
                (fn, content) for fn, content in attachments
                if Path(fn).suffix.lower() in [".pdf", ".docx", ".doc", ".pages"]
            ]

            if not valid_attachments:
                continue

            for original_filename, file_bytes in valid_attachments:
                if is_message_processed(message_id, original_filename):
                    continue

                # Apple .pages gibi ozel formatlari PDF'e donustur
                conv_filename, conv_bytes = handle_attachment_conversion(original_filename, file_bytes)

                safe_name = sanitize_filename(conv_filename)
                unique_name = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}_{safe_name}"
                saved_path = STORAGE_DIR / unique_name

                with open(saved_path, "wb") as f:
                    f.write(conv_bytes)

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

def download_attachment_on_demand(message_id: str, original_filename: str) -> Optional[Path]:
    """
    Eğer sunucu diskinde PDF dosyası bulunamazsa, Gmail'den e-postayı bulup eki anında indirir ve kaydeder.
    """
    if not GMAIL_APP_PASSWORD or not message_id:
        return None
    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
        mail.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        mail.select("INBOX")
        
        # message_id bazen '_stem' içerir
        raw_msg_id = message_id.split('_')[0] if '_' in message_id else message_id
        
        status, messages = mail.search(None, 'ALL')
        msg_ids = messages[0].split()[-50:] if (status == 'OK' and messages[0]) else []

        for m_id in reversed(msg_ids):
            st, data = mail.fetch(m_id, '(RFC822)')
            if st != 'OK':
                continue
            raw_msg = email.message_from_bytes(data[0][1])
            curr_msg_id = clean_header_str(raw_msg.get("Message-ID", ""))
            
            # E-posta eşleşmesi kontrolü (message_id veya attachment filename eşleşmesi)
            id_matches = raw_msg_id and (raw_msg_id in curr_msg_id or curr_msg_id in raw_msg_id)

            for part in raw_msg.walk():
                fn = clean_header_str(part.get_filename() or "")
                if fn and (fn == original_filename or (id_matches and (original_filename in fn or fn in original_filename))):
                    payload = part.get_payload(decode=True)
                    if payload:
                        conv_fn, conv_bytes = handle_attachment_conversion(fn, payload)
                        safe_name = sanitize_filename(conv_fn)
                        STORAGE_DIR.mkdir(parents=True, exist_ok=True)
                        save_p = STORAGE_DIR / safe_name
                        with open(save_p, "wb") as f:
                            f.write(conv_bytes)
                        try:
                            mail.close()
                            mail.logout()
                        except Exception:
                            pass
                        return save_p
        try:
            mail.close()
            mail.logout()
        except Exception:
            pass
    except Exception as e:
        print(f"[-] Gmail on-demand download hatası: {e}")
    return None

if __name__ == "__main__":
    fetch_and_process_emails()
