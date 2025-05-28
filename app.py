from flask import Flask, request, jsonify, render_template, redirect
import sqlite3
from datetime import datetime
import os

app = Flask(__name__)
DB_FILE = os.path.join(app.root_path, "clients.db")

def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS clients (
                mac TEXT PRIMARY KEY,
                nome TEXT,
                ip TEXT,
                ativo INTEGER,
                last_seen TEXT
            )
        """)

def get_all_clients():
    with sqlite3.connect(DB_FILE) as conn:
        conn.row_factory = sqlite3.Row
        return conn.execute("SELECT * FROM clients").fetchall()

def save_client(mac, ip):
    now = datetime.utcnow().isoformat()
    with sqlite3.connect(DB_FILE) as conn:
        cur = conn.cursor()
        exists = cur.execute("SELECT * FROM clients WHERE mac = ?", (mac,)).fetchone()
        if exists:
            cur.execute("UPDATE clients SET ip=?, last_seen=? WHERE mac=?",
                        (ip, now, mac))
        else:
            cur.execute("INSERT INTO clients (mac, nome, ip, ativo, last_seen) VALUES (?, ?, ?, ?, ?)",
                        (mac, "Sem nome", ip, 0, now))
        conn.commit()

@app.route("/command")
def command():
    raw_mac = request.args.get("mac")
    ip = request.args.get("public_ip")
    if not raw_mac:
        return jsonify({"error": "MAC não fornecido"}), 400

    mac = raw_mac.strip().lower()
    save_client(mac, ip)

    with sqlite3.connect(DB_FILE) as conn:
        ativo = conn.execute("SELECT ativo FROM clients WHERE mac=?", (mac,)).fetchone()[0]
    return jsonify({"ativo": bool(ativo)})

@app.route("/")
def index():
    clients = get_all_clients()
    return render_template("index.html", clients=clients)

@app.route("/set", methods=["POST"])
def set_status():
    mac = request.form.get("mac")
    status = request.form.get("status")
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("UPDATE clients SET ativo=? WHERE mac=?", (1 if status == "ACTIVE" else 0, mac))
        conn.commit()
    return redirect("/")

@app.route("/rename", methods=["POST"])
def rename():
    mac = request.form.get("mac")
    new_name = request.form.get("nome")
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("UPDATE clients SET nome=? WHERE mac=?", (new_name, mac))
        conn.commit()
    return redirect("/")

@app.route("/delete", methods=["POST"])
def delete():
    mac = request.form.get("mac")
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("DELETE FROM clients WHERE mac=?", (mac,))
        conn.commit()
    return redirect("/")

# ✅ Nova rota que exibe tudo do banco como JSON
@app.route("/dados")
def dados():
    rows = get_all_clients()
    return jsonify([dict(row) for row in rows])

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=10000)
