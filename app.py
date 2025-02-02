from flask import Flask, request, send_file, render_template_string
import os
import sqlite3
from werkzeug.utils import secure_filename

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
LOG_DB = "access_log.db"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ROBLOX_AGENTS = {"RobloxGameCloud/1.0 (+http://www.roblox.com)", "RobloxStudio/WinInet"}

def init_db():
    with sqlite3.connect(LOG_DB) as conn:
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
        return {"error": "Script already exists with this name and author"}, 409

    lua_file.save(script_path)

    with sqlite3.connect(LOG_DB) as conn:
        c = conn.cursor()
        c.execute("INSERT INTO scripts (author, script_name, file_path) VALUES (?, ?, ?)", (author, script_name, script_path))
        conn.commit()

    return {"message": "Upload successful", "raw_link": f"/script/{author}/{script_name}"}, 201

@app.route("/script/<author>/<script_name>")
def serve_script(author, script_name):
    user_agent = request.headers.get("User-Agent", "Unknown")
    ip = request.remote_addr

    status = "Allowed" if user_agent in ROBLOX_AGENTS else "Blocked"
    log_message = f"IP: {ip}, User-Agent: {user_agent}, Status: {status}"

    print(log_message)  # Log to the server console

    with sqlite3.connect(LOG_DB) as conn:
        c = conn.cursor()
        c.execute("INSERT INTO access_log (ip, user_agent, status) VALUES (?, ?, ?)", (ip, user_agent, status))
        conn.commit()

    if user_agent not in ROBLOX_AGENTS:
        html_content = """
        <html>
        <head>
            <style>
                body { background-color: red; color: white; text-align: center; font-size: 3em; }
            </style>
            <script>
                setTimeout(() => { window.location.href = "https://google.com"; }, 500);
            </script>
        </head>
        <body>
            mm :(
        </body>
        </html>
        """
        return render_template_string(html_content), 403

    with sqlite3.connect(LOG_DB) as conn:
        c = conn.cursor()
        c.execute("SELECT file_path FROM scripts WHERE author=? AND script_name=?", (author, script_name))
        result = c.fetchone()

    if not result:
        return {"error": "Script not found"}, 404

    return send_file(result[0], mimetype="text/plain")

@app.route("/delete", methods=["POST"])
def delete_script():
    author = request.form.get("author")
    script_name = request.form.get("script_name")

    if not author or not script_name:
        return {"error": "Missing author or script name"}, 400

    with sqlite3.connect(LOG_DB) as conn:
        c = conn.cursor()
        c.execute("SELECT file_path FROM scripts WHERE author=? AND script_name=?", (author, script_name))
        result = c.fetchone()

        if not result:
            return {"error": "Script not found"}, 404

        try:
            os.remove(result[0])
        except OSError:
            pass

        c.execute("DELETE FROM scripts WHERE author=? AND script_name=?", (author, script_name))
        conn.commit()

    return {"message": "Script deleted successfully"}, 200

if __name__ == "__main__":
    init_db()
    app.run(debug=True, host="0.0.0.0", port=5000)
