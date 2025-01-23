from flask import Flask, request

app = Flask(__name__)

@app.route('/log', methods=['GET', 'POST'])
def log_request():
    client_ip = request.remote_addr
    user_agent = request.headers.get("User-Agent")
    print(f"Request received from IP: {client_ip}, User-Agent: {user_agent}")
    return {
        "message": "Logged the request details",
        "ip": client_ip,
        "user_agent": user_agent
    }, 200

if __name__ == '__main__':
    app.run(port=5000, debug=True)
