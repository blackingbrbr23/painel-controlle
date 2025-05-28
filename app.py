from flask import Flask, request, jsonify, render_template, redirect
import sqlite3
from datetime import datetime

app = Flask(__name__)
DB_FILE = "clients.db"

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row  # para retornar dicionários
    return conn

def init_db():
    conn = get_db_connection()
    conn.execute('''
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

@app.before_first_request
def initialize():
    init_db()

@app.route("/command")
def command():
    mac = request.args.get("mac")
    ip = request.args.get("public_ip")
    if not mac:
        return jsonify({"error": "MAC não fornecido"}), 400

    now_iso = datetime.utcnow().isoformat()
    conn = get_db_connection()
    cur = conn.execute("SELECT * FROM clients WHERE mac = ?", (mac,))
    client = cur.fetchone()

    if client is None:
        # Insere cliente novo
        conn.execute(
            "INSERT INTO clients (mac, nome, ip, ativo, last_seen) VALUES (?, ?, ?, ?, ?)",
            (mac, "Sem nome", ip, 0, now_iso)
        )
    else:
        # Atualiza IP e last_seen
        conn.execute(
            "UPDATE clients SET ip = ?, last_seen = ? WHERE mac = ?",
            (ip, now_iso, mac)
        )
    conn.commit()

    # Busca ativo atualizado
    cur = conn.execute("SELECT ativo FROM clients WHERE mac = ?", (mac,))
    ativo = cur.fetchone()["ativo"]
    conn.close()

    return jsonify({"ativo": bool(ativo)})

@app.route("/")
def index():
    conn = get_db_connection()
    clients = conn.execute("SELECT * FROM clients").fetchall()
    conn.close()
    return render_template("index.html", clients=clients)

@app.route("/set/<mac>/<status>", methods=["POST"])
def set_status(mac, status):
    ativo = 1 if status == "ACTIVE" else 0
    conn = get_db_connection()
    conn.execute("UPDATE clients SET ativo = ? WHERE mac = ?", (ativo, mac))
    conn.commit()
    conn.close()
    return redirect("/")

@app.route("/rename/<mac>", methods=["POST"])
def rename(mac):
    new_name = request.form.get("nome")
    if new_name:
        conn = get_db_connection()
        conn.execute("UPDATE clients SET nome = ? WHERE mac = ?", (new_name, mac))
        conn.commit()
        conn.close()
    return redirect("/")

@app.route("/delete/<mac>", methods=["POST"])
def delete(mac):
    conn = get_db_connection()
    conn.execute("DELETE FROM clients WHERE mac = ?", (mac,))
    conn.commit()
    conn.close()
    return redirect("/")

# Rota para ver todos os clientes salvos (pode ser a mesma "/", ou uma nova rota)
@app.route("/clientes")
def clientes():
    conn = get_db_connection()
    clients = conn.execute("SELECT * FROM clients").fetchall()
    conn.close()
    return render_template("clientes.html", clients=clients)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
