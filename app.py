from flask import Flask, request, jsonify, render_template, redirect
import sqlite3, os
from datetime import datetime

app = Flask(__name__)
DB_FILE = "clients.db"

def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS clients (
                mac TEXT PRIMARY KEY,
                nome TEXT,
                ip TEXT,
                ativo INTEGER,
                last_seen TEXT
            )
        """)
        conn.commit()

def get_all_clients():
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute("SELECT mac, nome, ip, ativo, last_seen FROM clients")
        rows = c.fetchall()
        return {
            mac: {
                "nome": nome,
                "ip": ip,
                "ativo": bool(ativo),
                "last_seen": last_seen
            }
            for mac, nome, ip, ativo, last_seen in rows
        }

@app.route("/")
def index():
    clients = get_all_clients()
    return render_template("index.html", clients=clients)

@app.route("/command")
def command():
    mac = request.args.get("mac")
    ip = request.args.get("public_ip")
    if not mac:
        return jsonify({"error": "MAC não fornecido"}), 400

    now_iso = datetime.utcnow().isoformat()

    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM clients WHERE mac = ?", (mac,))
        result = c.fetchone()

        if result:
            # já cadastrado, só atualiza IP e last_seen
            c.execute("UPDATE clients SET ip = ?, last_seen = ? WHERE mac = ?", (ip, now_iso, mac))
            ativo = result[3]
        else:
            # ainda não cadastrado, adiciona com nome vazio, mas não marca como CLIENTE JÁ CADASTRADO
            c.execute("INSERT INTO clients (mac, nome, ip, ativo, last_seen) VALUES (?, ?, ?, ?, ?)", (mac, "Sem nome", ip, 0, now_iso))
            ativo = 0

        conn.commit()

    return jsonify({"ativo": bool(ativo)})

@app.route("/rename/<mac>", methods=["POST"])
def rename(mac):
    nome = request.form.get("nome")
    if nome:
        with sqlite3.connect(DB_FILE) as conn:
            c = conn.cursor()
            c.execute("UPDATE clients SET nome = ? WHERE mac = ?", (nome.strip(), mac))
            conn.commit()
    return redirect("/")

@app.route("/set/<mac>/<status>", methods=["POST"])
def set_status(mac, status):
    ativo = 1 if status == "ACTIVE" else 0
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute("UPDATE clients SET ativo = ? WHERE mac = ?", (ativo, mac))
        conn.commit()
    return redirect("/")

@app.route("/delete/<mac>", methods=["POST"])
def delete(mac):
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM clients WHERE mac = ?", (mac,))
        conn.commit()
    return redirect("/")

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=10000)
