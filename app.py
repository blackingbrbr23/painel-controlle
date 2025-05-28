from flask import Flask, request, render_template, redirect, url_for
import sqlite3
from datetime import datetime
import os

app = Flask(__name__)
DB_FILE = "clientes.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS clientes (
            mac TEXT PRIMARY KEY,
            nome TEXT,
            ip TEXT,
            ativo INTEGER,
            last_seen TEXT
        )
    ''')
    conn.commit()
    conn.close()

def salvar_cliente(mac, ip):
    now = datetime.utcnow().isoformat()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT mac FROM clientes WHERE mac = ?", (mac,))
    if cursor.fetchone():
        cursor.execute("UPDATE clientes SET ip=?, last_seen=? WHERE mac=?", (ip, now, mac))
    else:
        cursor.execute("INSERT INTO clientes (mac, nome, ip, ativo, last_seen) VALUES (?, ?, ?, 0, ?)", (mac, "Sem nome", ip, now))
    conn.commit()
    conn.close()

def listar_clientes():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT mac, nome, ip, ativo, last_seen FROM clientes")
    rows = cursor.fetchall()
    conn.close()
    return rows

def atualizar_status(mac, status):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("UPDATE clientes SET ativo=? WHERE mac=?", (1 if status == "ACTIVE" else 0, mac))
    conn.commit()
    conn.close()

def renomear_cliente(mac, nome):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("UPDATE clientes SET nome=? WHERE mac=?", (nome, mac))
    conn.commit()
    conn.close()

def excluir_cliente(mac):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM clientes WHERE mac=?", (mac,))
    conn.commit()
    conn.close()

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/command")
def command():
    mac = request.args.get("mac", "").strip().lower()
    ip = request.args.get("public_ip", "")
    if mac:
        salvar_cliente(mac, ip)
    return "OK"

@app.route("/set", methods=["POST"])
def set_status():
    atualizar_status(request.form["mac"], request.form["status"])
    return redirect("/clientes")

@app.route("/rename", methods=["POST"])
def rename():
    renomear_cliente(request.form["mac"], request.form["nome"])
    return redirect("/clientes")

@app.route("/delete", methods=["POST"])
def delete():
    excluir_cliente(request.form["mac"])
    return redirect("/clientes")

@app.route("/clientes")
def clientes():
    clientes = listar_clientes()
    return render_template("clientes.html", clientes=clientes)

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=10000)
