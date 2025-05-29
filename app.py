from flask import Flask, request, jsonify, render_template, redirect
import psycopg2
import os
from datetime import datetime

app = Flask(__name__)

# Conexão com o banco
DATABASE_URL = "postgresql://postgres:ZoEOavewaBNFBVCfnRMOlNOQDWMRsZQJ@metro.proxy.rlwy.net:46435/railway"

def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

# Armazena clientes temporários (que deram ping mas ainda não foram salvos no banco)
temp_clients = {}

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
                # já salvo no banco
                cur.execute("UPDATE clients SET ip = %s, last_seen = %s WHERE mac = %s",
                            (ip, now_iso, mac))
                conn.commit()
                ativo = row[0]
            else:
                # ainda não salvo: armazenar temporariamente
                temp_clients[mac] = {
                    "nome": "Sem nome",
                    "ip": ip,
                    "ativo": False,
                    "last_seen": now_iso
                }
                ativo = False
    return jsonify({"ativo": ativo})


@app.route("/")
def index():
    clients = {}

    # Dados salvos no banco
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT mac, nome, ip, ativo, last_seen FROM clients")
            rows = cur.fetchall()
            for mac, nome, ip, ativo, last_seen in rows:
                clients[mac] = {
                    "nome": nome,
                    "ip": ip,
                    "ativo": ativo,
                    "last_seen": last_seen
                }

    # Adiciona temporários que ainda não estão salvos
    for mac, data in temp_clients.items():
        if mac not in clients:
            clients[mac] = data

    return render_template("index.html", clients=clients)


@app.route("/set/<mac>/<status>", methods=["POST"])
def set_status(mac, status):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE clients SET ativo = %s WHERE mac = %s", (status == "ACTIVE", mac))
            conn.commit()
    return redirect("/")


@app.route("/rename/<mac>", methods=["POST"])
def rename(mac):
    new_name = request.form.get("nome")
    if not new_name:
        return redirect("/")

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM clients WHERE mac = %s", (mac,))
            exists = cur.fetchone()
            if exists:
                # Já salvo, só atualizar o nome
                cur.execute("UPDATE clients SET nome = %s WHERE mac = %s", (new_name, mac))
            else:
                # Primeiro salvamento
                temp_data = temp_clients.get(mac)
                ip = temp_data["ip"] if temp_data else request.remote_addr
                last_seen = temp_data["last_seen"] if temp_data else datetime.utcnow().isoformat()
                cur.execute("INSERT INTO clients (mac, nome, ip, ativo, last_seen) VALUES (%s, %s, %s, %s, %s)",
                            (mac, new_name, ip, False, last_seen))
                # remove da lista temporária
                if mac in temp_clients:
                    del temp_clients[mac]
            conn.commit()
    return redirect("/")


@app.route("/delete/<mac>", methods=["POST"])
def delete(mac):
    # Remove do banco
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM clients WHERE mac = %s", (mac,))
            conn.commit()
    # Remove da memória também
    if mac in temp_clients:
        del temp_clients[mac]
    return redirect("/")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
