# app.py

from flask import Flask, request, jsonify, render_template, redirect
import psycopg2
from datetime import datetime, timedelta
import threading
import time

app = Flask(__name__)

# Supabase Pooler IPv4 (senha corretamente codificada: @@W365888aw → %40%40W365888aw)
DATABASE_URL = "postgresql://postgres.olmnsorpzkxqojrgljyy:%40%40W365888aw@aws-0-sa-east-1.pooler.supabase.com:6543/postgres"

def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

def init_db():
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # Cria a tabela se não existir
            cur.execute("""
                CREATE TABLE IF NOT EXISTS clients (
                    mac TEXT PRIMARY KEY,
                    nome TEXT NOT NULL,
                    ip TEXT,
                    ativo BOOLEAN DEFAULT FALSE,
                    last_seen TEXT
                );
            """)
            # Adiciona a coluna de expiração, se ainda não exista
            cur.execute("""
                ALTER TABLE clients
                    ADD COLUMN IF NOT EXISTS expiration_timestamp TIMESTAMP;
            """)
            conn.commit()

# Armazena clientes temporários (pingaram mas ainda não foram salvos no banco)
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
                # Cliente já salvo: atualiza IP e last_seen
                cur.execute(
                    "UPDATE clients SET ip = %s, last_seen = %s WHERE mac = %s",
                    (ip, now_iso, mac)
                )
                conn.commit()
                ativo = row[0]
            else:
                # Cliente temporário (não salvo ainda)
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
    # Busca todos os clientes cadastrados no banco, incluindo o timestamp de expiração
    clients = {}
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT mac, nome, ip, ativo, last_seen, expiration_timestamp
                FROM clients;
            """)
            rows = cur.fetchall()
            for mac, nome, ip, ativo, last_seen, expiration_ts in rows:
                expiration_iso = None
                expiration_human = None
                if expiration_ts:
                    # string ISO (para o JavaScript interpretar como UTC)
                    expiration_iso = expiration_ts.strftime("%Y-%m-%dT%H:%M:%SZ")
                    # formato legível para exibir “Bloqueia em: …”
                    expiration_human = expiration_ts.strftime("%Y-%m-%d %H:%M UTC")
                clients[mac] = {
                    "nome": nome,
                    "ip": ip,
                    "ativo": ativo,
                    "last_seen": last_seen,
                    "expiration": expiration_iso,
                    "expiration_human": expiration_human
                }

    # Junta com os temporários que ainda não foram salvos no banco
    for mac, data in temp_clients.items():
        if mac not in clients:
            clients[mac] = {
                "nome": data["nome"],
                "ip": data["ip"],
                "ativo": data["ativo"],
                "last_seen": data["last_seen"],
                "expiration": None,
                "expiration_human": None
            }

    return render_template("index.html", clients=clients, temp_clients=set(temp_clients.keys()))

@app.route("/set/<mac>/<status>", methods=["POST"])
def set_status(mac, status):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            if status == "ACTIVE":
                # Ao ativar manualmente, limpamos também a expiração
                cur.execute(
                    "UPDATE clients SET ativo = TRUE, expiration_timestamp = NULL WHERE mac = %s",
                    (mac,)
                )
            else:
                # Se for BLOCKED, apenas bloqueia
                cur.execute(
                    "UPDATE clients SET ativo = FALSE WHERE mac = %s",
                    (mac,)
                )
            conn.commit()
    return ("", 204)

@app.route("/rename/<mac>", methods=["POST"])
def rename(mac):
    new_name = request.form.get("nome")
    # Captura os campos de expiração vindos do formulário
    expiration_date = request.form.get("expiration_date")      # ex.: "2025-06-10T15:30"
    expiration_seconds = request.form.get("expiration_seconds") # ex.: "3600" (em segundos)

    # Calcula o timestamp de expiração, se houver
    expiration_ts = None
    if expiration_date:
        try:
            # datetime.fromisoformat aceita algo como "2025-06-10T15:30"
            expiration_ts = datetime.fromisoformat(expiration_date)
        except ValueError:
            expiration_ts = None
    elif expiration_seconds:
        try:
            secs = int(expiration_seconds)
            expiration_ts = datetime.utcnow() + timedelta(seconds=secs)
        except ValueError:
            expiration_ts = None

    if not new_name:
        return redirect("/")

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # Verifica se já existe no banco
            cur.execute("SELECT 1 FROM clients WHERE mac = %s", (mac,))
            exists = cur.fetchone()
            if exists:
                # Atualiza nome e expiração, se já existe
                cur.execute("""
                    UPDATE clients
                    SET nome = %s,
                        expiration_timestamp = %s
                    WHERE mac = %s
                """, (new_name, expiration_ts, mac))
            else:
                # Insere novo cliente no banco
                temp_data = temp_clients.get(mac)
                ip = temp_data["ip"] if temp_data else request.remote_addr
                last_seen = temp_data["last_seen"] if temp_data else datetime.utcnow().isoformat()
                cur.execute("""
                    INSERT INTO clients (mac, nome, ip, ativo, last_seen, expiration_timestamp)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (mac, new_name, ip, False, last_seen, expiration_ts))
                # Remove dos temporários
                if mac in temp_clients:
                    del temp_clients[mac]
            conn.commit()
    return redirect("/")

@app.route("/delete/<mac>", methods=["POST"])
def delete(mac):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM clients WHERE mac = %s", (mac,))
            conn.commit()
    if mac in temp_clients:
        del temp_clients[mac]
    return redirect("/")


# Background thread que roda a cada 60 segundos e bloqueia todos os clientes expirados no banco,
# sem depender de alguém acessar a rota "/".
def expiration_worker():
    while True:
        now = datetime.utcnow()
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        UPDATE clients
                        SET ativo = FALSE
                        WHERE expiration_timestamp IS NOT NULL
                          AND expiration_timestamp <= %s
                          AND ativo = TRUE;
                    """, (now,))
                    conn.commit()
        except Exception:
            # Ignora erros de conexão momentânea; tenta novamente
            pass
        time.sleep(60)  # espera 60 segundos antes de checar de novo

if __name__ == "__main__":
    init_db()
    # Inicia a thread de expiração em background, como daemon para não bloquear o shutdown
    t = threading.Thread(target=expiration_worker, daemon=True)
    t.start()
    app.run(host="0.0.0.0", port=10000)
