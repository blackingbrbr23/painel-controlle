from flask import Flask, request, jsonify, redirect, render_template
import json
import os

app = Flask(__name__)

CLIENTES_FILE = "clients.json"

def carregar_clientes():
    if not os.path.exists(CLIENTES_FILE):
        return {}
    with open(CLIENTES_FILE, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}

def salvar_clientes(clientes):
    with open(CLIENTES_FILE, "w") as f:
        json.dump(clientes, f, indent=2)

@app.route("/")
def index():
    clientes = carregar_clientes()
    return render_template("index.html", clientes=clientes)

@app.route("/set/<id>/<status>", methods=["POST"])
def set_status(id, status):
    clientes = carregar_clientes()
    if id in clientes:
        clientes[id]["ativo"] = status.upper() == "ACTIVE"
        salvar_clientes(clientes)
    return redirect("/")

@app.route("/setname/<id>", methods=["POST"])
def set_name(id):
    nome = request.form.get("nome")
    clientes = carregar_clientes()
    if id in clientes:
        clientes[id]["nome"] = nome
        salvar_clientes(clientes)
    return redirect("/")

@app.route("/command")
def command():
    id = request.args.get("id")
    ip = request.args.get("public_ip")
    if not id or not ip:
        return jsonify({"error": "Missing id or public_ip"}), 400

    clientes = carregar_clientes()

    # Se o cliente ainda não existe, adiciona com status bloqueado por padrão
    if id not in clientes:
        clientes[id] = {"nome": "Sem nome", "ip": ip, "ativo": False}
        salvar_clientes(clientes)

    if not clientes[id].get("ativo"):
        return jsonify({"status": "BLOCKED"})

    return jsonify({"status": "ACTIVE"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)

