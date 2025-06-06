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
                    last_seen TEXT,
                    expiration_timestamp TIMESTAMP
                );
            """)
            conn.commit()

# Armazena clientes temporários (pingaram mas ainda não foram salvos no banco)
temp_clients = {}

@app.route("/command")
def command():
    """
    1) Recebe os parâmetros mac e public_ip.
    2) Busca no banco: SELECT ativo, expiration_timestamp.
       - Se não existir, grava em temp_clients e retorna {"ativo": False}.
       - Se existir:
         a) Se expiration_timestamp <= agora UTC, força ativo = FALSE no banco.
         b) Se ainda não expirou, retorna o valor atual de ativo.
       Em qualquer caso em que o cliente exista no banco, atualiza ip e last_seen.
    """
    mac = request.args.get("mac")
    ip = request.args.get("public_ip")
    if not mac:
        return jsonify({"error": "MAC não fornecido"}), 400

    now_utc = datetime.utcnow()

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # 1) Busca ativo e expiration_timestamp no banco
                cur.execute("SELECT ativo, expiration_timestamp FROM clients WHERE mac = %s", (mac,))
                row = cur.fetchone()

                if row:
                    ativo_db, expiration_ts = row

                    # 2) Verifica se já expirou
                    if expiration_ts is not None and expiration_ts <= now_utc:
                        # Marca como bloqueado no banco se ainda estivesse ativo
                        if ativo_db:
                            cur.execute(
                                "UPDATE clients SET ativo = FALSE WHERE mac = %s",
                                (mac,)
                            )
                            conn.commit()
                        ativo = False
                    else:
                        ativo = ativo_db

                    # 3) Atualiza IP e last_seen independentemente
                    cur.execute(
                        "UPDATE clients SET ip = %s, last_seen = %s WHERE mac = %s",
                        (ip, now_utc.isoformat(), mac)
                    )
                    conn.commit()

                else:
                    # Cliente não existe ainda no banco → armazena em temporários e retorna ativo = False
                    temp_clients[mac] = {
                        "nome": "Sem nome",
                        "ip": ip,
                        "ativo": False,
                        "last_seen": now_utc.isoformat()
                    }
                    ativo = False

        return jsonify({"ativo": ativo})

    except Exception as e:
        # Em caso de qualquer erro de BD, retorna bloqueado para não permitir acesso indevido
        print(f"Erro no /command: {e}")
        return jsonify({"ativo": False})

@app.route("/")
def index():
    """
    Renderiza a página principal, listando:
     - Todos os clientes cadastrados no banco (com expiration, se houver)
     - Todos os temp_clients que ainda não foram salvos
    """
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
                    # Gera ISO para o JS e human-readable para exibição
                    expiration_iso = expiration_ts.strftime("%Y-%m-%dT%H:%M:%SZ")
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
    """
    Marca como ACTIVE ou BLOCKED, limpando expiration_timestamp se for ACTIVE.
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            if status == "ACTIVE":
                # Ao ativar manualmente, limpa expiração
                cur.execute(
                    "UPDATE clients SET ativo = TRUE, expiration_timestamp = NULL WHERE mac = %s",
                    (mac,)
                )
            else:
                # Se for BLOCKED, apenas bloqueia sem mexer na expiração
                cur.execute(
                    "UPDATE clients SET ativo = FALSE WHERE mac = %s",
                    (mac,)
                )
            conn.commit()
    return ("", 204)

@app.route("/rename/<mac>", methods=["POST"])
def rename(mac):
    """
    Atualiza nome e expiration_timestamp (via data/hora ou via segundos contados a partir do momento).
    Se cliente não existir ainda no banco, insere novo registro com 'ativo = False'.
    """
    new_name = request.form.get("nome")
    expiration_date = request.form.get("expiration_date")      # ex.: "2025-06-10T15:30"
    expiration_seconds = request.form.get("expiration_seconds") # ex.: "3600"

    expiration_ts = None
    if expiration_date:
        try:
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
                # Atualiza nome e expiração
                cur.execute("""
                    UPDATE clients
                    SET nome = %s,
                        expiration_timestamp = %s
                    WHERE mac = %s
                """, (new_name, expiration_ts, mac))
            else:
                # Insere novo cliente com ativo = False
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
    """
    Exclui o cliente do banco e, se estiver em temp_clients, também remove.
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM clients WHERE mac = %s", (mac,))
            conn.commit()
    if mac in temp_clients:
        del temp_clients[mac]
    return redirect("/")

def expiration_worker():
    """
    Thread de background que roda a cada 60 segundos e bloqueia todos os clientes
    cuja expiration_timestamp já tenha passado, definindo ativo = FALSE.
    """
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
            # Ignora erros temporários de conexão
            pass
        time.sleep(60)

if __name__ == "__main__":
    init_db()
    # Inicia a thread de expiração em background (daemon para não bloquear o shutdown)
    t = threading.Thread(target=expiration_worker, daemon=True)
    t.start()
    app.run(host="0.0.0.0", port=10000)
