import sqlite3
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from config import DB_PATH, DATA_DIR

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cv_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id TEXT UNIQUE,
            sender_email TEXT,
            sender_name TEXT,
            subject TEXT,
            received_date TEXT,
            candidate_name TEXT,
            candidate_email TEXT,
            candidate_phone TEXT,
            candidate_city TEXT,
            category TEXT,
            seniority TEXT,
            experience_years TEXT,
            key_skills TEXT,
            summary TEXT,
            portfolio_links TEXT,
            file_name TEXT,
            file_path TEXT,
            preview_token TEXT UNIQUE,
            pros TEXT,
            cons TEXT,
            cover_letter TEXT,
            status TEXT DEFAULT 'processed',
            reported INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Mevcut veritabanlarına yeni sütunları güvenle ekle
    try:
        cursor.execute("ALTER TABLE cv_records ADD COLUMN pros TEXT")
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE cv_records ADD COLUMN cons TEXT")
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE cv_records ADD COLUMN cover_letter TEXT")
    except Exception:
        pass

    # Eğer veritabanı boşsa ve seed_data.sql varsa, verileri yükle
    try:
        cursor.execute("SELECT COUNT(*) FROM cv_records")
        count = cursor.fetchone()[0]
        seed_file = DATA_DIR / "seed_data.sql"
        if count == 0 and seed_file.exists():
            conn.executescript(seed_file.read_text(encoding="utf-8"))
            print(f"[+] seed_data.sql basariyla yuklendi.")
    except Exception as e:
        print(f"[-] Seed veri yukleme hatasi: {e}")

    conn.commit()
    conn.close()

def is_message_processed(message_id: str, file_name: str = "") -> bool:
    if not message_id:
        return False
    conn = get_connection()
    cursor = conn.cursor()
    if file_name:
        cursor.execute(
            "SELECT 1 FROM cv_records WHERE message_id LIKE ? AND file_name = ?", 
            (f"{message_id}%", file_name)
        )
    else:
        cursor.execute(
            "SELECT 1 FROM cv_records WHERE message_id LIKE ?", 
            (f"{message_id}%",)
        )
    row = cursor.fetchone()
    conn.close()
    return row is not None

def save_cv_record(record: Dict[str, Any]) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    preview_token = record.get("preview_token")
    if not preview_token:
        msg_id = record.get("message_id", "")
        f_name = record.get("file_name", "")
        if msg_id and f_name:
            import hashlib
            preview_token = hashlib.sha256(f"{msg_id}_{f_name}".encode("utf-8")).hexdigest()[:32]
        else:
            preview_token = str(uuid.uuid4()).replace("-", "")
    
    cursor.execute("""
        INSERT INTO cv_records (
            message_id, sender_email, sender_name, subject, received_date,
            candidate_name, candidate_email, candidate_phone, candidate_city,
            category, seniority, experience_years, key_skills, summary,
            portfolio_links, file_name, file_path, preview_token, pros, cons, cover_letter, status, reported
        ) VALUES (
            :message_id, :sender_email, :sender_name, :subject, :received_date,
            :candidate_name, :candidate_email, :candidate_phone, :candidate_city,
            :category, :seniority, :experience_years, :key_skills, :summary,
            :portfolio_links, :file_name, :file_path, :preview_token, :pros, :cons, :cover_letter, :status, 0
        )
    """, {
        "message_id": record.get("message_id"),
        "sender_email": record.get("sender_email"),
        "sender_name": record.get("sender_name"),
        "subject": record.get("subject"),
        "received_date": record.get("received_date") or datetime.now().isoformat(),
        "candidate_name": record.get("candidate_name") or "Belirtilmemiş",
        "candidate_email": record.get("candidate_email") or "",
        "candidate_phone": record.get("candidate_phone") or "",
        "candidate_city": record.get("candidate_city") or "",
        "category": record.get("category") or "Genel Başvuru",
        "seniority": record.get("seniority") or "Belirtilmemiş",
        "experience_years": str(record.get("experience_years") or "Belirtilmemiş"),
        "key_skills": record.get("key_skills") or "",
        "summary": record.get("summary") or "",
        "portfolio_links": record.get("portfolio_links") or "",
        "file_name": record.get("file_name"),
        "file_path": record.get("file_path"),
        "preview_token": preview_token,
        "pros": record.get("pros") or "",
        "cons": record.get("cons") or "",
        "cover_letter": record.get("cover_letter") or "",
        "status": record.get("status", "processed")
    })
    rec_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return rec_id

def get_unreported_cvs() -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM cv_records 
        WHERE reported = 0 
        ORDER BY category ASC, created_at DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def mark_cvs_as_reported(cv_ids: List[int]):
    if not cv_ids:
        return
    conn = get_connection()
    cursor = conn.cursor()
    placeholders = ",".join("?" * len(cv_ids))
    cursor.execute(f"UPDATE cv_records SET reported = 1 WHERE id IN ({placeholders})", cv_ids)
    conn.commit()
    conn.close()

def get_cv_by_token(token: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM cv_records WHERE preview_token = ?", (token,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_stats() -> Dict[str, Any]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM cv_records")
    total = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM cv_records WHERE reported = 0")
    pending = cursor.fetchone()[0]
    cursor.execute("SELECT category, COUNT(*) as count FROM cv_records GROUP BY category ORDER BY count DESC")
    categories = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return {"total": total, "pending": pending, "categories": categories}

# Veritabanını başlat
init_db()
