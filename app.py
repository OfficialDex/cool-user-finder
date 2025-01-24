from flask import Flask, request, jsonify, abort
from flask_sqlalchemy import SQLAlchemy
import uuid

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///scripts.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

REQUIRED_HEADER = "carl"
REQUIRED_TOKEN = "cj is my homie"

class Script(db.Model):
    id = db.Column(db.String(36), primary_key=True, nullable=False)
    script_name = db.Column(db.String(100), nullable=False, unique=True)
    owner_name = db.Column(db.String(100), nullable=False)
    script_content = db.Column(db.Text, nullable=False)

    def __repr__(self):
        return f'<Script {self.script_name}>'

with app.app_context():
    db.create_all()

@app.before_request
def require_token():
    header = request.headers.get("Header")
    token = request.headers.get("Token")
    if header != REQUIRED_HEADER or token != REQUIRED_TOKEN:
        abort(403)

@app.route('/')
def homepage():
    return "there is nothing to see here:>"

@app.route('/publish', methods=['POST'])
def publish_script():
    if not request.is_json:
        return jsonify({"error": "Invalid JSON format"}), 400
    
    data = request.get_json()
    script_content = data.get('script')
    script_name = data.get('script_name')
    owner_name = data.get('owner_name')

    if not script_content or not script_name or not owner_name:
        return jsonify({"error": "Script content, script name, and owner name are required"}), 400
    
    existing_script = Script.query.filter_by(script_name=script_name).first()
    if existing_script:
        return jsonify({"error": "Script name already exists, please choose a different name."}), 400
    
    script_id = str(uuid.uuid4())
    new_script = Script(id=script_id, script_name=script_name, owner_name=owner_name, script_content=script_content)
    db.session.add(new_script)
    db.session.commit()

    raw_link = f"/raw/{script_id}"
    return jsonify({
        "message": "Script uploaded successfully",
        "raw_link": raw_link,
        "script_name": script_name,
        "owner_name": owner_name
    }), 201

@app.route('/raw/<path:script_id>', methods=['GET'])
def raw_script(script_id):
    header = request.headers.get("Header")
    token = request.headers.get("Token")
    
    if header != REQUIRED_HEADER or token != REQUIRED_TOKEN:
        return jsonify({"error": "Forbidden"}), 403
    
    script = Script.query.get(script_id)
    
    if not script:
        return jsonify({"error": "Script not found"}), 404

    return script.script_content, 200

@app.route('/update/<path:script_id>', methods=['PUT'])
def update_script(script_id):
    if not request.is_json:
        return jsonify({"error": "Invalid JSON format"}), 400
    
    data = request.get_json()
    new_script_name = data.get('script_name')
    new_script_content = data.get('script')
    owner_name = data.get('owner_name')

    if not new_script_name or not new_script_content or not owner_name:
        return jsonify({"error": "Script name, content, and owner name are required for update"}), 400

    script = Script.query.get(script_id)
    if not script:
        return jsonify({"error": "Script not found"}), 404

    if script.owner_name != owner_name:
        return jsonify({"error": "You are not the owner of this script, so you cannot modify it."}), 403

    if new_script_name != script.script_name:
        existing_script = Script.query.filter_by(script_name=new_script_name).first()
        if existing_script:
            return jsonify({"error": "Script name already exists, please choose a different name."}), 400

    script.script_name = new_script_name
    script.script_content = new_script_content
    db.session.commit()

    return jsonify({
        "message": "Script updated successfully",
        "raw_link": f"/raw/{script.id}",
        "script_name": new_script_name,
        "owner_name": owner_name
    })

@app.route('/delete/<path:script_id>', methods=['DELETE'])
def delete_script(script_id):
    data = request.get_json()
    owner_name = data.get('owner_name')

    if not owner_name:
        return jsonify({"error": "Owner name is required to delete the script"}), 400

    script = Script.query.get(script_id)
    if not script:
        return jsonify({"error": "Script not found"}), 404

    if script.owner_name != owner_name:
        return jsonify({"error": "You are not the owner of this script, so you cannot delete it."}), 403

    db.session.delete(script)
    db.session.commit()

    return jsonify({"message": "Script deleted successfully"}), 200

@app.route('/scripts', methods=['GET'])
def list_scripts():
    scripts = Script.query.all()
    if not scripts:
        return jsonify({"error": "No scripts found"}), 404

    script_list = []
    for script in scripts:
        script_list.append({
            "script_name": script.script_name,
            "owner_name": script.owner_name,
            "script_content": script.script_content,
            "raw_link": f"/raw/{script.id}"
        })

    return jsonify({"scripts": script_list}), 200

if __name__ == '__main__':
    app.run(port=5000, debug=True)
