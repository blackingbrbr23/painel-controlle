from flask import Flask, request, jsonify, render_template, redirect
import json, os
from datetime import datetime

app = Flask(__name__)
CLIENTS_FILE = "clients.json"

def load_clients():
    if not os.path.exists(CLIENTS_FILE):
        return {}
    with open(CLIENTS_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}

def save_clients(clients):
    with open(CLIENTS_FILE, "w", encoding="utf-8") as f:
        json.dump(clients, f, indent=2, ensure_ascii=False)

@app.route("/command")
def command():
    mac = request.args.get("mac")
    ip = request.args.get("public_ip")
    if not mac:
        return jsonify({"error": "MAC não fornecido"}), 400

    clients = load_clients()
    now_iso = datetime.utcnow().isoformat()

    if mac not in clients:
        # cliente novo
        clients[mac] = {
            "nome": "Sem nome",
            "ip": ip,
            "ativo": True,
            "last_seen": now_iso
        }
    else:
        # apenas atualiza IP e timestamp, sem mexer no nome/ativo
        clients[mac]["ip"] = ip
        clients[mac]["last_seen"] = now_iso

    save_clients(clients)
    return jsonify({"ativo": clients[mac]["ativo"]})

@app.route("/")
def index():
    clients = load_clients()
    # opcional: converter last_seen para datetime aqui, se quiser lógica extra
    return render_template("index.html", clients=clients)

@app.route("/set/<mac>/<status>", methods=["POST"])
def set_status(mac, status):
    clients = load_clients()
    if mac in clients:
        clients[mac]["ativo"] = (status == "ACTIVE")
        save_clients(clients)
    return redirect("/")

@app.route("/rename/<mac>", methods=["POST"])
def rename(mac):
    new_name = request.form.get("nome")
    clients = load_clients()
    if mac in clients and new_name:
        clients[mac]["nome"] = new_name
        save_clients(clients)
    return redirect("/")

@app.route("/delete/<mac>", methods=["POST"])
def delete(mac):
    clients = load_clients()
    if mac in clients:
        del clients[mac]
        save_clients(clients)
    return redirect("/")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
