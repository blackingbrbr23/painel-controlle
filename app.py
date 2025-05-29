from flask import Flask, request, jsonify, render_template, redirect, g
import sqlite3
from datetime import datetime

app = Flask(__name__)
DATABASE = 'clients.db'

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

def init_db():
    with app.app_context():
        db = get_db()
        db.execute('''
            CREATE TABLE IF NOT EXISTS clients (
                mac TEXT PRIMARY KEY,
                nome TEXT,
                ip TEXT,
                ativo INTEGER,
                last_seen TEXT,
                cadastrado INTEGER
            )
        ''')
        db.commit()

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

@app.route("/command")
def command():
    mac = request.args.get("mac")
    ip = request.args.get("public_ip")
    if not mac:
        return jsonify({"error": "MAC não fornecido"}), 400

    db = get_db()
    cur = db.execute("SELECT * FROM clients WHERE mac = ?", (mac,))
    client = cur.fetchone()
    now = datetime.utcnow().isoformat()

    if client is None:
        db.execute("INSERT INTO clients (mac, nome, ip, ativo, last_seen, cadastrado) VALUES (?, ?, ?, ?, ?, ?)",
                   (mac, 'Sem nome', ip, 0, now, 0))
    else:
        db.execute("UPDATE clients SET ip = ?, last_seen = ? WHERE mac = ?", (ip, now, mac))
    db.commit()

    cur = db.execute("SELECT ativo FROM clients WHERE mac = ?", (mac,))
    ativo = cur.fetchone()["ativo"]
    return jsonify({"ativo": bool(ativo)})

@app.route("/")
def index():
    db = get_db()
    cur = db.execute("SELECT * FROM clients")
    clients = cur.fetchall()
    return render_template("index.html", clients=clients)

@app.route("/set/<mac>/<status>", methods=["POST"])
def set_status(mac, status):
    db = get_db()
    ativo = 1 if status == "ACTIVE" else 0
    db.execute("UPDATE clients SET ativo = ? WHERE mac = ?", (ativo, mac))
    db.commit()
    return redirect("/")

@app.route("/rename/<mac>", methods=["POST"])
def rename(mac):
    new_name = request.form.get("nome")
    if new_name:
        db = get_db()
        db.execute("UPDATE clients SET nome = ?, cadastrado = 1 WHERE mac = ?", (new_name, mac))
        db.commit()
    return redirect("/")

@app.route("/delete/<mac>", methods=["POST"])
def delete(mac):
    db = get_db()
    db.execute("DELETE FROM clients WHERE mac = ?", (mac,))
    db.commit()
    return redirect("/")

@app.route("/ver_clientes")
def ver_clientes():
    db = get_db()
    cur = db.execute("SELECT * FROM clients WHERE cadastrado = 1")
    clients = cur.fetchall()
    return render_template("clientes.html", clients=clients)

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=10000)

