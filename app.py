from flask import Flask, request, jsonify, render_template, redirect
import json
import os

app = Flask(__name__)

CLIENTS_FILE = "clients.json"

def load_clients():
    if not os.path.exists(CLIENTS_FILE):
        return {}
    with open(CLIENTS_FILE, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}

def save_clients(clients):
    with open(CLIENTS_FILE, "w") as f:
        json.dump(clients, f, indent=2)

@app.route("/command")
def command():
    client_id = request.args.get("id")
    ip = request.args.get("public_ip")
    clients = load_clients()

    if client_id not in clients:
        clients[client_id] = {
            "nome": "Sem nome",
            "ip": ip,
            "ativo": False
        }
        save_clients(clients)

    return jsonify({"ativo": clients[client_id]["ativo"]})

@app.route("/")
def index():
    clients = load_clients()
    return render_template("index.html", clients=clients)

@app.route("/set/<client_id>/<status>", methods=["POST"])
def set_status(client_id, status):
    clients = load_clients()
    if client_id in clients:
        clients[client_id]["ativo"] = (status == "ACTIVE")
        save_clients(clients)
    return redirect("/")

@app.route("/rename/<client_id>", methods=["POST"])
def rename(client_id):
    new_name = request.form.get("nome")
    clients = load_clients()
    if client_id in clients and new_name:
        clients[client_id]["nome"] = new_name
        save_clients(clients)
    return redirect("/")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
