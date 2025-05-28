from flask import Flask, request, jsonify, render_template, redirect
import sqlite3
from datetime import datetime
import os

app = Flask(__name__)
DB_FILE = "clients.db"

# Garante que o banco e a tabela existem
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS clients (
            mac TEXT PRIMARY KEY,
            nome TEXT,
            ip TEXT,
            ativo INTEGER,
            last_seen TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# Retorna todos os clientes
def get_all_clients():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM clients")
    rows = cursor.fetchall()
    conn.close()
    return rows

# Salva/atualiza cliente que acessa /command
@app.route("/command")
def command():
    mac = request.args.get("mac")
    ip = request.args.get("public_ip")
    if not mac:
        return jsonify({"error": "MAC não fornecido"}), 400

    now = datetime.utcnow().isoformat()

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM clients WHERE mac = ?", (mac,))
    client = cursor.fetchone()

    if client is None:
        # Novo cliente
        cursor.execute(
            "INSERT INTO clients (mac, nome, ip, ativo, last_seen) VALUES (?, ?, ?, ?, ?)",
            (mac, "Sem nome", ip, 0, now)
        )
    else:
        # Atualiza IP e timestamp
        cursor.execute(
            "UPDATE clients SET ip = ?, last_seen = ? WHERE mac = ?",
            (ip, now, mac)
        )

    conn.commit()
    cursor.execute("SELECT ativo FROM clients WHERE mac = ?", (mac,))
    ativo = cursor.fetchone()[0]
    conn.close()

    return jsonify({"ativo": bool(ativo)})

# Página principal
@app.route("/")
def index():
    clients = get_all_clients()
    return render_template("index.html", clients=clients)

# Ativar/bloquear cliente
@app.route("/set/<mac>/<status>", methods=["POST"])
def set_status(mac, status):
    ativo = 1 if status == "ACTIVE" else 0
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("UPDATE clients SET ativo = ? WHERE mac = ?", (ativo, mac))
    conn.commit()
    conn.close()
    return redirect("/")

# Renomear cliente
@app.route("/rename/<mac>", methods=["POST"])
def rename(mac):
    new_name = request.form.get("nome")
    if new_name:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("UPDATE clients SET nome = ? WHERE mac = ?", (new_name, mac))
        conn.commit()
        conn.close()
    return redirect("/")

# Excluir cliente
@app.route("/delete/<mac>", methods=["POST"])
def delete(mac):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM clients WHERE mac = ?", (mac,))
    conn.commit()
    conn.close()
    return redirect("/")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
