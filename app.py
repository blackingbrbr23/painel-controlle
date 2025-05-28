import sqlite3
import json
from flask import Flask, request, jsonify, render_template, redirect, send_file
import os
from datetime import datetime
from io import BytesIO

app = Flask(__name__)
DB_FILE = os.path.join(app.root_path, "clients.db")

def export_clients_json():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS clients (mac TEXT PRIMARY KEY, nome TEXT, ip TEXT, ativo INTEGER, last_seen TEXT)")
    c.execute("SELECT mac, nome, ip, ativo, last_seen FROM clients")
    rows = c.fetchall()
    conn.close()

    data = {}
    for mac, nome, ip, ativo, last_seen in rows:
        data[mac] = {
            "nome": nome,
            "ip": ip,
            "ativo": bool(ativo),
            "last_seen": last_seen
        }

    return data

@app.route("/exportar-json")
def exportar_json():
    data = export_clients_json()
    json_data = json.dumps(data, indent=2, ensure_ascii=False)
    return send_file(BytesIO(json_data.encode("utf-8")),
                     mimetype="application/json",
                     as_attachment=True,
                     download_name="clients.json")

