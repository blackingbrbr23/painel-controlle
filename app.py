from flask import Flask, request, jsonify, render_template, redirect
import sqlite3, json, os
from datetime import datetime

app = Flask(__name__)
DB_FILE = os.path.join(app.root_path, "clients.db")
JSON_FILE = os.path.join(app.root_path, "clients.json")

# Banco de dados inicial
def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS clients (
            mac TEXT PRIMARY KEY,
            nome TEXT,
            ip TEXT,
            ativo INTEGER,
            last_seen TEXT
        )''')

# Exporta dados para JSON
def export_to_json():
    with sqlite3.connect(DB_FILE) as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM clients")
        rows = cur.fetchall()
        data = {
            mac: {
                "nome": nome,
                "ip": ip,
                "ativo": bool(ativo),
                "last_seen": last_seen
            }
            for mac, nome, ip, ativo, last_seen in rows
        }
    with open(JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# Normaliza MAC
def normalize_mac(mac):
    return mac.strip().lower()

# Rota principal
@app.route("/")
def index():
    with sqlite3.connect(DB_FILE) as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM clients")
        rows = cur.fetchall()
        clients = {
            mac: {
                "nome": nome,
                "ip": ip,
                "ativo": bool(ativo),
                "last_seen": last_seen
            }
            for mac, nome, ip, ativo, last_seen in rows
        }
    return render_template("index.html", clients=clients)

# Rota de comando do cliente
@app.route("/command")
def command():
    mac_raw = request.args.get("mac")
    ip = request.args.get("public_ip")
    if not mac_raw:
        return jsonify({"error": "MAC não fornecido"}), 400

    mac = normalize_mac(mac_raw)
    now = datetime.utcnow().isoformat()

    with sqlite3.connect(DB_FILE) as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM clients WHERE mac = ?", (mac,))
        row = cur.fetchone()
        if row:
            cur.execute("UPDATE clients SET ip = ?, last_seen = ? WHERE mac = ?", (ip, now, mac))
        else:
            cur.execute("INSERT INTO clients (mac, nome, ip, ativo, last_seen) VALUES (?, ?, ?, ?, ?)",
                        (mac, "Sem nome", ip, 0, now))
        conn.commit()
    export_to_json()
    with sqlite3.connect(DB_FILE) as conn:
        cur = conn.cursor()
        cur.execute("SELECT ativo FROM clients WHERE mac = ?", (mac,))
        ativo = cur.fetchone()[0]
    return jsonify({"ativo": bool(ativo)})

# Renomear cliente
@app.route("/rename", methods=["POST"])
def rename():
    mac = normalize_mac(request.form.get("mac"))
    nome = request.form.get("nome")
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("UPDATE clients SET nome = ? WHERE mac = ?", (nome, mac))
        conn.commit()
    export_to_json()
    return redirect("/")

# Alterar status
@app.route("/set", methods=["POST"])
def set_status():
    mac = normalize_mac(request.form.get("mac"))
    status = request.form.get("status")
    ativo = 1 if status == "ACTIVE" else 0
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("UPDATE clients SET ativo = ? WHERE mac = ?", (ativo, mac))
        conn.commit()
    export_to_json()
    return redirect("/")

# Excluir cliente
@app.route("/delete", methods=["POST"])
def delete():
    mac = normalize_mac(request.form.get("mac"))
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("DELETE FROM clients WHERE mac = ?", (mac,))
        conn.commit()
    export_to_json()
    return redirect("/")

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=10000)
