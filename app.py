from flask import Flask, request, jsonify, redirect, url_for, render_template
import json
import os

app = Flask(__name__)

CLIENTS_FILE = "clients.json"

# Garantir que o arquivo exista
if not os.path.exists(CLIENTS_FILE):
    with open(CLIENTS_FILE, "w") as f:
        json.dump({}, f)

def load_clients():
    with open(CLIENTS_FILE, "r") as f:
        return json.load(f)

def save_clients(clients):
    with open(CLIENTS_FILE, "w") as f:
        json.dump(clients, f, indent=2)

@app.route("/")
def index():
    clients = load_clients()
    return render_template("index.html", clients=clients)

@app.route("/command", methods=["GET"])
def command():
    client_id = request.args.get("id")
    ip = request.args.get("public_ip", "")

    clients = load_clients()

    if client_id not in clients:
        clients[client_id] = {"nome": "Sem nome", "ip": ip, "ativo": False}
        save_clients(clients)

    return jsonify(clients[client_id])

@app.route("/set/<client_id>/<status>", methods=["POST"])
def set_status(client_id, status):
    clients = load_clients()
    if client_id in clients:
        clients[client_id]["ativo"] = True if status.upper() == "ACTIVE" else False
        save_clients(clients)
    return redirect(url_for("index"))

@app.route("/rename/<client_id>", methods=["POST"])
def rename_client(client_id):
    new_name = request.form.get("nome", "Sem nome")
    clients = load_clients()
    if client_id in clients:
        clients[client_id]["nome"] = new_name
        save_clients(clients)
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
