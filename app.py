from flask import Flask, request, jsonify, render_template, redirect
import sqlite3, os
from datetime import datetime

app = Flask(__name__)

# Path para o banco SQLite (criado automaticamente se não existir)
DB_PATH = os.path.join(app.root_path, "clients.db")

def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

# Inicializa conexão e garante tabela
conn = get_conn()
conn.execute("""
CREATE TABLE IF NOT EXISTS clients (
  mac TEXT PRIMARY KEY,
  nome TEXT NOT NULL,
  ip TEXT,
  ativo INTEGER NOT NULL DEFAULT 0,
  last_seen TEXT
)
""")
conn.commit()

def normalize_mac(mac: str) -> str:
    return mac.strip().lower()

@app.route("/command")
def command():
    raw_mac = request.args.get("mac")
    ip = request.args.get("public_ip")
    if not raw_mac:
        return jsonify({"error": "MAC não fornecido"}), 400

    mac = normalize_mac(raw_mac)
    now_iso = datetime.utcnow().isoformat()

    cur = conn.execute("SELECT * FROM clients WHERE mac = ?", (mac,))
    row = cur.fetchone()
    if row is None:
        conn.execute(
            "INSERT INTO clients(mac, nome, ip, ativo, last_seen) VALUES (?, ?, ?, ?, ?)",
            (mac, "Sem nome", ip, 0, now_iso)
        )
    else:
        conn.execute(
            "UPDATE clients SET ip = ?, last_seen = ? WHERE mac = ?",
            (ip, now_iso, mac)
        )
    conn.commit()

    cur = conn.execute("SELECT ativo FROM clients WHERE mac = ?", (mac,))
    ativo = bool(cur.fetchone()["ativo"])
    return jsonify({"ativo": ativo})

@app.route("/")
def index():
    cur = conn.execute("SELECT mac, nome, ip, ativo, last_seen FROM clients")
    clients = [dict(r) for r in cur.fetchall()]
    return render_template("index.html", clients=clients)

@app.route("/set", methods=["POST"])
def set_status():
    mac = normalize_mac(request.form.get("mac"))
    status = request.form.get("status")
    ativo = 1 if status == "ACTIVE" else 0
    conn.execute("UPDATE clients SET ativo = ? WHERE mac = ?", (ativo, mac))
    conn.commit()
    return redirect("/")

@app.route("/rename", methods=["POST"])
def rename():
    mac = normalize_mac(request.form.get("mac"))
    new_name = request.form.get("nome")
    if new_name:
        conn.execute("UPDATE clients SET nome = ? WHERE mac = ?", (new_name, mac))
        conn.commit()
    return redirect("/")

@app.route("/delete", methods=["POST"])
def delete():
    mac = normalize_mac(request.form.get("mac"))
    conn.execute("DELETE FROM clients WHERE mac = ?", (mac,))
    conn.commit()
    return redirect("/")

# Exporta todos os clientes como JSON
@app.route("/export_json")
def export_json():
    cur = conn.execute("SELECT mac, nome, ip, ativo, last_seen FROM clients")
    clients = [
        {
            "mac": row["mac"],
            "nome": row["nome"],
            "ip": row["ip"],
            "ativo": bool(row["ativo"]),
            "last_seen": row["last_seen"],
        }
        for row in cur.fetchall()
    ]
    return jsonify(clients)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
