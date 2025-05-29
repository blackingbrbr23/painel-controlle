from flask import Flask, request, jsonify, render_template, redirect
import sqlite3
from datetime import datetime

app = Flask(__name__)
DATABASE = "clientes.db"

def init_db():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS clients (
        mac TEXT PRIMARY KEY,
        nome TEXT,
        ip TEXT,
        ativo INTEGER,
        last_seen TEXT,
        cadastrado INTEGER DEFAULT 0
    )''')
    conn.commit()
    conn.close()

def get_all_clients():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM clients")
    clients = cursor.fetchall()
    conn.close()
    return clients

def get_cadastrados():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM clients WHERE cadastrado = 1")
    clients = cursor.fetchall()
    conn.close()
    return clients

@app.route("/command")
def command():
    mac = request.args.get("mac")
    ip = request.args.get("public_ip")
    if not mac:
        return jsonify({"error": "MAC não fornecido"}), 400

    now = datetime.utcnow().isoformat()
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM clients WHERE mac = ?", (mac,))
    result = cursor.fetchone()

    if result:
        cursor.execute("UPDATE clients SET ip = ?, last_seen = ? WHERE mac = ?", (ip, now, mac))
    else:
        cursor.execute("INSERT INTO clients (mac, nome, ip, ativo, last_seen, cadastrado) VALUES (?, ?, ?, ?, ?, 0)", (mac, "Sem nome", ip, 0, now))

    conn.commit()
    cursor.execute("SELECT ativo FROM clients WHERE mac = ?", (mac,))
    ativo = cursor.fetchone()[0]
    conn.close()
    return jsonify({"ativo": bool(ativo)})

@app.route("/")
def index():
    clients = get_all_clients()
    return render_template("index.html", clients=clients)

@app.route("/ver_clientes")
def ver_clientes():
    clients = get_cadastrados()
    return render_template("clientes.html", clients=clients)

@app.route("/rename/<mac>", methods=["POST"])
def rename(mac):
    nome = request.form.get("nome")
    if nome:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute("UPDATE clients SET nome = ?, cadastrado = 1 WHERE mac = ?", (nome, mac))
        conn.commit()
        conn.close()
    return redirect("/")

@app.route("/set/<mac>/<status>", methods=["POST"])
def set_status(mac, status):
    ativo = 1 if status == "ACTIVE" else 0
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("UPDATE clients SET ativo = ? WHERE mac = ?", (ativo, mac))
    conn.commit()
    conn.close()
    return redirect("/")

@app.route("/delete/<mac>", methods=["POST"])
def delete(mac):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM clients WHERE mac = ?", (mac,))
    conn.commit()
    conn.close()
    return redirect("/")

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=10000)
