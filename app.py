from flask import Flask, request, send_file, render_template_string
import os
import sqlite3
import shutil
import requests
import json
from werkzeug.utils import secure_filename
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from google.oauth2.service_account import Credentials

app = Flask(__name__)

BASE_STORAGE = "/var/lib/flask_api"
UPLOAD_FOLDER = os.path.join(BASE_STORAGE, "uploads")
DB_PATH = os.path.join(BASE_STORAGE, "access_log.db")
BACKUP_DB_PATH = os.path.join(BASE_STORAGE, "backup_access_log.db")

ROBLOX_AGENTS = {"RobloxGameCloud/1.0 (+http://www.roblox.com)", "RobloxStudio/WinInet"}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

SERVICE_ACCOUNT_FILE = "credentials.json"
SCOPES = ["https://www.googleapis.com/auth/drive"]
FOLDER_ID = "1e4xOJCwGCpCQa6c5CSOuRAq5yiQyYZpm"

def get_drive_service():
    creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    return build("drive", "v3", credentials=creds)

def upload_to_drive():
    service = get_drive_service()
    file_metadata = {"name": "access_log.db", "parents": [FOLDER_ID]}
    media = MediaFileUpload(DB_PATH, mimetype="application/x-sqlite3", resumable=True)
    file_list = service.files().list(q="name='access_log.db' and trashed=false").execute()
    
    if file_list.get("files"):
        file_id = file_list["files"][0]["id"]
        service.files().update(fileId=file_id, media_body=media).execute()
    else:
        service.files().create(body=file_metadata, media_body=media, fields="id").execute()

def download_from_drive():
    service = get_drive_service()
    file_list = service.files().list(q="name='access_log.db' and trashed=false").execute()
    
    if not file_list.get("files"):
        return
    
    file_id = file_list["files"][0]["id"]
    request = service.files().get_media(fileId=file_id)
    
    with open(DB_PATH, "wb") as f:
        downloader = MediaIoBaseDownload(f, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()

def init_db():
    download_from_drive()
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute(
            """CREATE TABLE IF NOT EXISTS access_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ip TEXT,
                user_agent TEXT,
                status TEXT
            )"""
        )
        c.execute(
            """CREATE TABLE IF NOT EXISTS scripts (
                author TEXT,
                script_name TEXT,
                file_path TEXT,
                UNIQUE(author, script_name)
            )"""
        )
        conn.commit()

@app.route("/")
def homepage():
    html_content = """
    <html>
    <head>
        <title>Nothing Here</title>
        <script>
            setTimeout(() => { window.location.href = "https://google.com"; }, 4000);
        </script>
        <style>
            body { text-align: center; font-size: 2em; margin-top: 20%; }
        </style>
    </head>
    <body>
        There is nothing to see :)
    </body>
    </html>
    """
    return render_template_string(html_content)

@app.route("/upload", methods=["POST"])
def upload():
    if "lua_file" not in request.files or not request.form.get("author") or not request.form.get("script_name"):
        return {"error": "Missing file, author, or script name"}, 400

    author = secure_filename(request.form["author"])
    script_name = secure_filename(request.form["script_name"])
    lua_file = request.files["lua_file"]

    script_path = os.path.join(UPLOAD_FOLDER, f"{author}_{script_name}.lua")

    if os.path.exists(script_path):
        return {"error": "Script already exists"}, 409

    lua_file.save(script_path)

    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("INSERT INTO scripts (author, script_name, file_path) VALUES (?, ?, ?)", (author, script_name, script_path))
        conn.commit()

    upload_to_drive()
    return {"message": "Upload successful", "raw_link": f"/script/{author}/{script_name}"}, 201

@app.route("/script/<author>/<script_name>")
def serve_script(author, script_name):
    user_agent = request.headers.get("User-Agent", "Unknown")
    ip = request.remote_addr

    status = "Allowed" if user_agent in ROBLOX_AGENTS else "Blocked"
    log_message = f"IP: {ip}, User-Agent: {user_agent}, Status: {status}"
    print(log_message)

    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("INSERT INTO access_log (ip, user_agent, status) VALUES (?, ?, ?)", (ip, user_agent, status))
        conn.commit()

    upload_to_drive()

    if user_agent not in ROBLOX_AGENTS:
        html_content = """<html><head><script>setTimeout(() => { window.location.href = "https://google.com"; }, 500);</script></head><body>mm :(</body></html>"""
        return render_template_string(html_content), 403

    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT file_path FROM scripts WHERE author=? AND script_name=?", (author, script_name))
        result = c.fetchone()

    if not result:
        return {"error": "Script not found"}, 404

    return send_file(result[0], mimetype="text/plain")

@app.route("/edit", methods=["POST"])
def edit_script():
    if "lua_file" not in request.files or not request.form.get("author") or not request.form.get("script_name"):
        return {"error": "Missing file, author, or script name"}, 400

    author = secure_filename(request.form["author"])
    script_name = secure_filename(request.form["script_name"])
    lua_file = request.files["lua_file"]

    script_path = os.path.join(UPLOAD_FOLDER, f"{author}_{script_name}.lua")

    if not os.path.exists(script_path):
        return {"error": "Script not found"}, 404

    lua_file.save(script_path)

    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("UPDATE scripts SET file_path=? WHERE author=? AND script_name=?", (script_path, author, script_name))
        conn.commit()

    upload_to_drive()
    return {"message": "Script edited", "raw_link": f"/script/{author}/{script_name}"}, 200

if __name__ == "__main__":
    init_db()
    app.run(debug=True, host="0.0.0.0", port=5000)
