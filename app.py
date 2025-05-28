from flask import Flask, request, jsonify, render_template, redirect
import json, os
from datetime import datetime

app = Flask(__name__)
# Use an absolute path to ensure clients.json is always referenced correctly
CLIENTS_FILE = os.path.join(app.root_path, "clients.json")


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


def normalize_mac(mac: str) -> str:
    return mac.strip().lower()


@app.route("/command")
def command():
    raw_mac = request.args.get("mac")
    ip = request.args.get("public_ip")
    if not raw_mac:
        return jsonify({"error": "MAC não fornecido"}), 400

    mac = normalize_mac(raw_mac)
    clients = load_clients()
    now_iso = datetime.utcnow().isoformat()

    if mac not in clients:
        # cliente novo: inicializa com nome padrão
        clients[mac] = {
            "nome": "Sem nome",
            "ip": ip,
            "ativo": False,
            "last_seen": now_iso
        }
    else:
        # apenas atualiza IP e timestamp, mantém nome e status
        clients[mac]["ip"] = ip
        clients[mac]["last_seen"] = now_iso

    save_clients(clients)
    return jsonify({"ativo": clients[mac]["ativo"]})


@app.route("/")
def index():
    clients = load_clients()
    return render_template("index.html", clients=clients)


@app.route("/set/<raw_mac>/<status>", methods=["POST"])
def set_status(raw_mac, status):
    mac = normalize_mac(raw_mac)
    clients = load_clients()
    if mac in clients:
        clients[mac]["ativo"] = (status == "ACTIVE")
        save_clients(clients)
    return redirect("/")


@app.route("/rename/<raw_mac>", methods=["POST"])
def rename(raw_mac):
    new_name = request.form.get("nome")
    mac = normalize_mac(raw_mac)
    clients = load_clients()
    if mac in clients and new_name:
        clients[mac]["nome"] = new_name
        save_clients(clients)
    return redirect("/")


@app.route("/delete/<raw_mac>", methods=["POST"])
def delete(raw_mac):
    mac = normalize_mac(raw_mac)
    clients = load_clients()
    if mac in clients:
        del clients[mac]
        save_clients(clients)
    return redirect("/")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
