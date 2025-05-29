from flask import Flask, request, jsonify, render_template, redirect
import psycopg2
from datetime import datetime
import os

# ---- CONFIG ----
DATABASE_URL = os.getenv("DATABASE_URL") or "sua_string_postgres_aqui"
# ----------------

app = Flask(__name__)

def connect_db():
    return psycopg2.connect(DATABASE_URL)

def init_db():
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS clients (
        mac TEXT PRIMARY KEY,
        nome TEXT,
        ip TEXT,
        ativo BOOLEAN,
        last_seen TEXT
    )
    """)
    conn.commit()
    conn.close()

def get_clients():
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("SELECT mac, nome, ip, ativo, last_seen FROM clients")
    rows = cur.fetchall()
    conn.close()
    return {mac: {"nome": nome, "ip": ip, "ativo": ativo, "last_seen": last_seen} for mac, nome, ip, ativo, last_seen in rows}

def save_client(mac, nome, ip, ativo, last_seen):
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("""
    INSERT INTO clients (mac, nome, ip, ativo, last_seen)
    VALUES (%s, %s, %s, %s, %s)
    ON CONFLICT (mac) DO UPDATE SET
        nome = EXCLUDED.nome,
        ip = EXCLUDED.ip,
        ativo = EXCLUDED.ativo,
        last_seen = EXCLUDED.last_seen
    """, (mac, nome, ip, ativo, last_seen))
    conn.commit()
    conn.close()

def delete_client(mac):
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM clients WHERE mac = %s", (mac,))
    conn.commit()
    conn.close()

@app.route("/command")
def command():
    mac = request.args.get("mac")
    ip = request.args.get("public_ip")
    if not mac:
        return jsonify({"error": "MAC não fornecido"}), 400

    now_iso = datetime.utcnow().isoformat()
    clients = get_clients()

    if mac not in clients:
        save_client(mac, "Sem nome", ip, False, now_iso)
    else:
        client = clients[mac]
        save_client(mac, client["nome"], ip, client["ativo"], now_iso)

    return jsonify({"ativo": get_clients()[mac]["ativo"]})

@app.route("/")
def index():
    return render_template("index.html", clients=get_clients())

@app.route("/set/<mac>/<status>", methods=["POST"])
def set_status(mac, status):
    clients = get_clients()
    if mac in clients:
        c = clients[mac]
        save_client(mac, c["nome"], c["ip"], status == "ACTIVE", c["last_seen"])
    return redirect("/")

@app.route("/rename/<mac>", methods=["POST"])
def rename(mac):
    new_name = request.form.get("nome")
    clients = get_clients()
    if mac in clients and new_name:
        c = clients[mac]
        save_client(mac, new_name, c["ip"], c["ativo"], c["last_seen"])
    return redirect("/")

@app.route("/delete/<mac>", methods=["POST"])
def delete(mac):
    delete_client(mac)
    return redirect("/")

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=10000)
