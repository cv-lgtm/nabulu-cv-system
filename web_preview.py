import os
import mimetypes
from pathlib import Path
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
import urllib.parse
from database import get_cv_by_token
from config import WEB_PREVIEW_HOST, WEB_PREVIEW_PORT

class CVPreviewHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Sadeleştirilmiş konsol logları
        pass

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.strip("/")
        parts = path.split("/")

        if len(parts) >= 2 and parts[0] == "preview":
            token = parts[1]
            self.handle_preview(token)
        elif len(parts) >= 2 and parts[0] == "raw":
            token = parts[1]
            self.handle_raw_file(token)
        elif path == "health":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"OK")
        elif path == "preview-report":
            from report_generator import build_report_html
            from database import get_unreported_cvs, get_connection
            from datetime import datetime
            cvs = get_unreported_cvs()
            if not cvs:
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM cv_records ORDER BY id DESC LIMIT 10")
                cvs = [dict(row) for row in cursor.fetchall()]
                conn.close()
            html = build_report_html(cvs, datetime.now().strftime("%d.%m.%Y") + " Haftası")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(html.encode("utf-8"))
        else:
            self.send_response(404)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write("<h3>404 - Sayfa Bulunamadı</h3>".encode("utf-8"))

    def handle_preview(self, token: str):
        cv = get_cv_by_token(token)
        if not cv:
            self.send_response(404)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write("<h2>CV Önizleme Bulunamadı</h2><p>İstenen CV kaydı mevcut değil veya silinmiş olabilir.</p>".encode("utf-8"))
            return

        name = cv.get("candidate_name", "Aday")
        category = cv.get("category", "Genel Başvuru")
        seniority = cv.get("seniority", "Belirtilmemiş")
        experience = cv.get("experience_years", "-")
        skills = cv.get("key_skills", "")
        summary = cv.get("summary", "")
        pros = cv.get("pros", "")
        cons = cv.get("cons", "")
        cover_letter = cv.get("cover_letter", "")
        email = cv.get("candidate_email", "")
        phone = cv.get("candidate_phone", "")
        city = cv.get("candidate_city", "")
        portfolio = cv.get("portfolio_links", "")
        file_name = cv.get("file_name", "cv.pdf")

        pros_html = ""
        if pros:
            p_items = "".join([f'<li>{p.strip().lstrip("•").strip()}</li>' for p in pros.split("\n") if p.strip()])
            pros_html = f"""
            <div style="background: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.3); border-radius: 8px; padding: 12px; font-size: 13px; color: #6ee7b7;">
                <strong style="color: #34d399;">🟢 Artıları (Güçlü Yönler):</strong>
                <ul style="margin: 6px 0 0 16px; padding: 0;">{p_items}</ul>
            </div>
            """

        cons_html = ""
        if cons:
            c_items = "".join([f'<li>{c.strip().lstrip("•").strip()}</li>' for c in cons.split("\n") if c.strip()])
            cons_html = f"""
            <div style="background: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.3); border-radius: 8px; padding: 12px; font-size: 13px; color: #fca5a5;">
                <strong style="color: #f87171;">🔴 Soru İşaretleri & Eksileri:</strong>
                <ul style="margin: 6px 0 0 16px; padding: 0;">{c_items}</ul>
            </div>
            """

        skills_html = "".join([f'<span class="badge skill">{s.strip()}</span>' for s in skills.split(",") if s.strip()])
        portfolio_html = ""
        if portfolio:
            links = [l.strip() for l in portfolio.split(",") if l.strip()]
            for l in links:
                portfolio_html += f'<a href="{l}" target="_blank" class="btn btn-outline">🔗 Portfolyo / Link</a> '

        formatted_letter = cover_letter.replace("\r\n", "<br>").replace("\n", "<br>")
        html = f"""<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{name} - CV Önizleme | Nabulu - İK</title>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: 'Plus Jakarta Sans', -apple-system, sans-serif;
            background: #0f172a;
            color: #f8fafc;
            height: 100vh;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }}
        .header {{
            background: #1e293b;
            border-bottom: 1px solid #334155;
            padding: 16px 24px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 12px;
            z-index: 10;
        }}
        .brand {{
            display: flex;
            align-items: center;
            gap: 12px;
        }}
        .brand-logo {{
            background: linear-gradient(135deg, #FF5E14, #FF8A00);
            color: white;
            font-weight: 800;
            padding: 6px 14px;
            border-radius: 8px;
            font-size: 13px;
            letter-spacing: 1px;
        }}
        .candidate-title h1 {{
            font-size: 18px;
            font-weight: 700;
            color: #ffffff;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .candidate-meta {{
            font-size: 13px;
            color: #94a3b8;
            margin-top: 4px;
            display: flex;
            gap: 12px;
            flex-wrap: wrap;
        }}
        .badge {{
            display: inline-block;
            padding: 3px 8px;
            border-radius: 6px;
            font-size: 11px;
            font-weight: 600;
        }}
        .badge.cat {{ background: #431407; color: #fdba74; border: 1px solid #9a3412; }}
        .badge.sen {{ background: #064e3b; color: #6ee7b7; border: 1px solid #047857; }}
        .badge.skill {{ background: #1e293b; color: #cbd5e1; border: 1px solid #475569; }}
        
        .actions {{
            display: flex;
            gap: 8px;
            align-items: center;
        }}
        .btn {{
            padding: 8px 14px;
            border-radius: 8px;
            font-size: 13px;
            font-weight: 600;
            text-decoration: none;
            transition: all 0.2s;
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }}
        .btn-primary {{
            background: #FF5E14;
            color: white;
        }}
        .btn-primary:hover {{ background: #E04D0C; }}
        .btn-outline {{
            background: #334155;
            color: #e2e8f0;
        }}
        .btn-outline:hover {{ background: #475569; }}

        .main-container {{
            display: flex;
            flex: 1;
            overflow: hidden;
        }}
        .sidebar {{
            width: 440px;
            min-width: 440px;
            background: #1e293b;
            border-right: 1px solid #334155;
            padding: 24px;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 20px;
            height: calc(100vh - 73px);
        }}
        .section-title {{
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: #64748b;
            font-weight: 700;
            margin-bottom: 8px;
        }}
        .summary-box {{
            background: #0f172a;
            border: 1px solid #334155;
            border-radius: 10px;
            padding: 14px;
            font-size: 13.5px;
            line-height: 1.6;
            color: #e2e8f0;
        }}
        .info-list {{
            display: flex;
            flex-direction: column;
            gap: 8px;
            font-size: 13px;
        }}
        .info-row {{
            display: flex;
            justify-content: space-between;
            border-bottom: 1px solid #2d3748;
            padding-bottom: 6px;
        }}
        .info-label {{ color: #94a3b8; }}
        .info-value {{ color: #f1f5f9; font-weight: 500; text-align: right; }}
        .skills-wrap {{
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
        }}

        .viewer {{
            flex: 1;
            background: #334155;
            position: relative;
        }}
        .viewer iframe {{
            width: 100%;
            height: 100%;
            border: none;
        }}
        .modal-overlay {{
            display: none;
            position: fixed;
            top: 0; left: 0; width: 100%; height: 100%;
            background: rgba(0, 0, 0, 0.7);
            z-index: 100;
            justify-content: center;
            align-items: center;
        }}
        .modal-content {{
            background: #1e293b;
            border: 1px solid #475569;
            border-radius: 12px;
            width: 90%;
            max-width: 650px;
            max-height: 80vh;
            display: flex;
            flex-direction: column;
            box-shadow: 0 20px 25px -5px rgba(0,0,0,0.5);
        }}
        .modal-header {{
            padding: 16px 20px;
            border-bottom: 1px solid #334155;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .modal-body {{
            padding: 20px;
            overflow-y: auto;
            line-height: 1.7;
            font-size: 14px;
            color: #e2e8f0;
        }}
        .btn-close {{
            background: none;
            border: none;
            color: #94a3b8;
            font-size: 20px;
            cursor: pointer;
        }}
        .btn-close:hover {{ color: white; }}
        @media(max-width: 768px) {{
            .main-container {{ flex-direction: column; }}
            .sidebar {{ width: 100%; min-width: 100%; height: auto; max-height: 45vh; }}
        }}
    </style>
</head>
<body>
    <div class="header">
        <div class="brand">
            <div class="brand-logo">NABULU - IK</div>
            <div class="candidate-title">
                <h1>{name}</h1>
                <div class="candidate-meta">
                    <span class="badge cat">{category}</span>
                    <span class="badge sen">{seniority}</span>
                    <span>📍 {city or 'Konum Belirtilmemiş'}</span>
                    <span>⏳ Deneyim: {experience}</span>
                </div>
            </div>
        </div>
        <div class="actions">
            {f'<button onclick="openLetterModal()" class="btn btn-outline">✉️ Ön Yazıyı Oku</button>' if cover_letter else ''}
            {portfolio_html}
            {f'<a href="mailto:{email}" class="btn btn-outline">✉️ E-posta</a>' if email else ''}
            {f'<a href="tel:{phone}" class="btn btn-outline">📞 Ara</a>' if phone else ''}
            <a href="/raw/{token}" download="{file_name}" class="btn btn-primary">⬇️ Dosyayı İndir</a>
        </div>
    </div>
    
    <div class="main-container">
        <div class="sidebar">
            <div>
                <div class="section-title">✨ AI Değerlendirme & Yönetici Özeti</div>
                <div class="summary-box">
                    {summary or 'Bu aday için özet oluşturulamadı.'}
                </div>
            </div>

            {pros_html}

            {cons_html}

            {f'''<div>
                <div class="section-title">✉️ Adayın E-posta Ön Yazısı & Notu</div>
                <div class="summary-box" style="font-style: italic; color: #cbd5e1; border-color: #475569; max-height: 180px; overflow-y: auto;">
                    "{cover_letter}"
                </div>
            </div>''' if cover_letter else ''}

            <div>
                <div class="section-title">🛠️ Öne Çıkan Yetenekler</div>
                <div class="skills-wrap">
                    {skills_html if skills_html else '<span style="color:#64748b; font-size:12px;">Yetenek bilgisi bulunamadı.</span>'}
                </div>
            </div>

            <div>
                <div class="section-title">📋 İletişim & Detaylar</div>
                <div class="info-list">
                    <div class="info-row">
                        <span class="info-label">E-posta:</span>
                        <span class="info-value">{email or '-'}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">Telefon:</span>
                        <span class="info-value">{phone or '-'}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">Şehir:</span>
                        <span class="info-value">{city or '-'}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">Orijinal Dosya:</span>
                        <span class="info-value">{file_name}</span>
                    </div>
                </div>
            </div>
        </div>

        <div class="viewer">
            <iframe src="/raw/{token}#toolbar=1" type="application/pdf"></iframe>
        </div>
    </div>

    <!-- Ön Yazı Modal -->
    <div id="letterModal" class="modal-overlay" onclick="if(event.target === this) closeLetterModal()">
        <div class="modal-content">
            <div class="modal-header">
                <h3 style="font-size: 15px; font-weight: 700; color: #f8fafc; display: flex; align-items: center; gap: 8px;">
                    ✉️ {name} - E-posta Ön Yazısı & Notları
                </h3>
                <button class="btn-close" onclick="closeLetterModal()">&times;</button>
            </div>
            <div class="modal-body">
                {formatted_letter}
            </div>
        </div>
    </div>

    <script>
        function openLetterModal() {{
            document.getElementById('letterModal').style.display = 'flex';
        }}
        function closeLetterModal() {{
            document.getElementById('letterModal').style.display = 'none';
        }}
        document.addEventListener('keydown', function(e) {{
            if (e.key === 'Escape') closeLetterModal();
        }});
    </script>
</body>
</html>"""

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))

    def handle_raw_file(self, token: str):
        cv = get_cv_by_token(token)
        if not cv:
            self.send_response(404)
            self.end_headers()
            return

        file_path = Path(cv.get("file_path", ""))
        if not file_path.exists():
            self.send_response(404)
            self.end_headers()
            return

        mime_type, _ = mimetypes.guess_type(str(file_path))
        if not mime_type:
            mime_type = "application/pdf"

        file_size = file_path.stat().st_size
        self.send_response(200)
        self.send_header("Content-Type", mime_type)
        self.send_header("Content-Length", str(file_size))
        self.send_header("Content-Disposition", f'inline; filename="{file_path.name}"')
        self.end_headers()

        with open(file_path, "rb") as f:
            while chunk := f.read(65536):
                self.wfile.write(chunk)

def run_preview_server(host=WEB_PREVIEW_HOST, port=WEB_PREVIEW_PORT):
    server = ThreadingHTTPServer((host, port), CVPreviewHandler)
    print(f"[+] CV Önizleme Web Sunucusu aktif: http://{host}:{port}")
    server.serve_forever()

if __name__ == "__main__":
    run_preview_server()
