from flask import Flask, request, jsonify, render_template, redirect
import psycopg2
import os
from datetime import datetime

app = Flask(__name__)
DATABASE_URL = os.getenv("DATABASE_URL")

def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

def init_db():
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS clients (
                    mac TEXT PRIMARY KEY,
                    nome TEXT,
                    ip TEXT,
                    ativo BOOLEAN,
                    last_seen TEXT
                );
            """)
            conn.commit()

@app.route("/command")
def command():
    mac = request.args.get("mac")
    ip = request.args.get("public_ip")
    if not mac:
        return jsonify({"error": "MAC não fornecido"}), 400

    now_iso = datetime.utcnow().isoformat()

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT ativo FROM clients WHERE mac = %s", (mac,))
            row = cur.fetchone()

            if row:
                cur.execute("UPDATE clients SET ip = %s, last_seen = %s WHERE mac = %s",
                            (ip, now_iso, mac))
                conn.commit()
                ativo = row[0]
            else:
                ativo = False  # cliente novo, mas não será salvo
    return jsonify({"ativo": ativo})

@app.route("/")
def index():
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT mac, nome, ip, ativo, last_seen FROM clients")
            rows = cur.fetchall()
            clients = {
                mac: {
                    "nome": nome,
                    "ip": ip,
                    "ativo": ativo,
                    "last_seen": last_seen
                } for mac, nome, ip, ativo, last_seen in rows
            }
    return render_template("index.html", clients=clients)

@app.route("/rename/<mac>", methods=["POST"])
def rename(mac):
    new_name = request.form.get("nome")
    if not new_name:
        return redirect("/")

    now_iso = datetime.utcnow().isoformat()
    ip = request.remote_addr

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM clients WHERE mac = %s", (mac,))
            exists = cur.fetchone()
            if exists:
                cur.execute("UPDATE clients SET nome = %s WHERE mac = %s", (new_name, mac))
            else:
                cur.execute("INSERT INTO clients (mac, nome, ip, ativo, last_seen) VALUES (%s, %s, %s, %s, %s)",
                            (mac, new_name, ip, False, now_iso))
            conn.commit()
    return redirect("/")

@app.route("/set/<mac>/<status>", methods=["POST"])
def set_status(mac, status):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE clients SET ativo = %s WHERE mac = %s", (status == "ACTIVE", mac))
            conn.commit()
    return redirect("/")

@app.route("/delete/<mac>", methods=["POST"])
def delete(mac):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM clients WHERE mac = %s", (mac,))
            conn.commit()
    return redirect("/")

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=10000)
