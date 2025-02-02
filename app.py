from flask import Flask, request, send_file, render_template_string
import os
import firebase_admin
from firebase_admin import credentials, firestore
from werkzeug.utils import secure_filename

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

cred = credentials.Certificate("firebase_credentials.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

ROBLOX_AGENTS = {"RobloxGameCloud/1.0 (+http://www.roblox.com)", "RobloxStudio/WinInet"}

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

    if db.collection("scripts").document(f"{author}_{script_name}").get().exists:
        return {"error": "Script already exists with this name and author"}, 409

    lua_file.save(script_path)

    db.collection("scripts").document(f"{author}_{script_name}").set({
        "author": author,
        "script_name": script_name,
        "file_path": script_path
    })

    return {"message": "Upload successful", "raw_link": f"/script/{author}/{script_name}"}, 201

@app.route("/script/<author>/<script_name>")
def serve_script(author, script_name):
    user_agent = request.headers.get("User-Agent", "Unknown")
    ip = request.remote_addr

    status = "Allowed" if user_agent in ROBLOX_AGENTS else "Blocked"
    log_message = f"IP: {ip}, User-Agent: {user_agent}, Status: {status}"

    print(log_message)

    db.collection("access_log").add({"ip": ip, "user_agent": user_agent, "status": status})

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

    script_ref = db.collection("scripts").document(f"{author}_{script_name}").get()

    if not script_ref.exists:
        return {"error": "Script not found"}, 404

    script_path = script_ref.to_dict().get("file_path")

    return send_file(script_path, mimetype="text/plain")

@app.route("/edit", methods=["POST"])
def edit_script():
    if "lua_file" not in request.files or not request.form.get("author") or not request.form.get("script_name"):
        return {"error": "Missing file, author, or script name"}, 400

    author = secure_filename(request.form["author"])
    script_name = secure_filename(request.form["script_name"])
    lua_file = request.files["lua_file"]

    script_ref = db.collection("scripts").document(f"{author}_{script_name}").get()

    if not script_ref.exists:
        return {"error": "Script not found to edit"}, 404

    script_path = os.path.join(UPLOAD_FOLDER, f"{author}_{script_name}.lua")

    lua_file.save(script_path)

    db.collection("scripts").document(f"{author}_{script_name}").update({"file_path": script_path})

    return {"message": "Script edited successfully", "raw_link": f"/script/{author}/{script_name}"}, 200

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
