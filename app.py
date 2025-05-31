import os
from flask import Flask, request, jsonify, render_template, redirect
import psycopg2
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()  # carrega as variáveis definidas em .env

app = Flask(__name__)

# ----------------------------------------------------------
# 1) CARREGA A STRING DE CONEXÃO DO SUPABASE
# ----------------------------------------------------------
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("A variável DATABASE_URL não foi encontrada. Verifique seu .env")

def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

# ----------------------------------------------------------
# 2) FUNÇÃO PARA CRIAR A TABELA AUTOMATICAMENTE
# ----------------------------------------------------------
def init_db():
    """
    Cria a tabela 'clients' caso ela ainda não exista.
    Estrutura:
      - mac       : TEXT (PRIMARY KEY)
      - nome      : TEXT
      - ip        : TEXT
      - ativo     : BOOLEAN DEFAULT FALSE
      - last_seen : TIMESTAMP WITH TIME ZONE
    """
    conn = get_db_connection()
    with conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS clients (
                    mac TEXT PRIMARY KEY,
                    nome TEXT,
                    ip TEXT,
                    ativo BOOLEAN DEFAULT FALSE,
                    last_seen TIMESTAMP WITH TIME ZONE
                );
                """
            )
    conn.close()

# Antes da primeira requisição, garantimos que a tabela exista
@app.before_first_request
def create_tables_if_not_exist():
    init_db()

# ----------------------------------------------------------
# 3) DICIONÁRIO TEMPORÁRIO (clientes vistos mas ainda não salvos)
# ----------------------------------------------------------
temp_clients = {}

# ----------------------------------------------------------
# 4) ROTA /command: cliente envia MAC e IP, marcamos ativo ou não
# ----------------------------------------------------------
@app.route("/command")
def command():
    mac = request.args.get("mac")
    ip = request.args.get("public_ip")
    if not mac:
        return jsonify({"error": "MAC não fornecido"}), 400

    now_iso = datetime.utcnow().isoformat()

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # Verifica se já existe no banco
            cur.execute("SELECT ativo FROM clients WHERE mac = %s", (mac,))
            row = cur.fetchone()

            if row:
                # Se já existe, só atualiza IP e last_seen
                cur.execute(
                    "UPDATE clients SET ip = %s, last_seen = %s WHERE mac = %s",
                    (ip, now_iso, mac)
                )
                conn.commit()
                ativo = row[0]
            else:
                # Se não existe, armazena temporariamente em memória
                temp_clients[mac] = {
                    "nome": "Sem nome",
                    "ip": ip,
                    "ativo": False,
                    "last_seen": now_iso
                }
                ativo = False

    return jsonify({"ativo": ativo})

# ----------------------------------------------------------
# 5) ROTA /: exibe lista de clientes (do banco + temporários)
# ----------------------------------------------------------
@app.route("/")
def index():
    clients = {}

    # Busca todos os clientes persistidos no banco
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

    # Adiciona ao dicionário aqueles que estão em temp_clients mas não estão no banco
    for mac, data in temp_clients.items():
        if mac not in clients:
            clients[mac] = data

    return render_template("index.html", clients=clients, temp_clients=set(temp_clients.keys()))

# ----------------------------------------------------------
# 6) ROTA /set/<mac>/<status>: altera status de ativo/bloqueado
# ----------------------------------------------------------
@app.route("/set/<mac>/<status>", methods=["POST"])
def set_status(mac, status):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # status == "ACTIVE" => ativo = True; caso contrário, False
            cur.execute(
                "UPDATE clients SET ativo = %s WHERE mac = %s",
                (status == "ACTIVE", mac)
            )
            conn.commit()
    return redirect("/")

# ----------------------------------------------------------
# 7) ROTA /rename/<mac>: atualiza ou insere (se for temporário) com novo nome
# ----------------------------------------------------------
@app.route("/rename/<mac>", methods=["POST"])
def rename(mac):
    new_name = request.form.get("nome")
    if not new_name:
        return redirect("/")

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # Verifica se já existe um registro com essa MAC
            cur.execute("SELECT 1 FROM clients WHERE mac = %s", (mac,))
            exists = cur.fetchone()

            if exists:
                # Atualiza o nome no banco
                cur.execute(
                    "UPDATE clients SET nome = %s WHERE mac = %s",
                    (new_name, mac)
                )
            else:
                # Insere um novo registro usando dados de temp_clients (se existirem)
                temp_data = temp_clients.get(mac)
                ip = temp_data["ip"] if temp_data else request.remote_addr
                last_seen = temp_data["last_seen"] if temp_data else datetime.utcnow().isoformat()

                cur.execute(
                    """
                    INSERT INTO clients (mac, nome, ip, ativo, last_seen)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (mac, new_name, ip, False, last_seen)
                )
                # Remove o cliente temporário da memória em RAM
                if mac in temp_clients:
                    del temp_clients[mac]

            conn.commit()

    return redirect("/")

# ----------------------------------------------------------
# 8) ROTA /delete/<mac>: deleta cliente (banco + temp, se existir)
# ----------------------------------------------------------
@app.route("/delete/<mac>", methods=["POST"])
def delete(mac):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM clients WHERE mac = %s", (mac,))
            conn.commit()

    # Também remove do temp_clients se estiver lá
    if mac in temp_clients:
        del temp_clients[mac]

    return redirect("/")

# ----------------------------------------------------------
# 9) RODA O APP
# ----------------------------------------------------------
if __name__ == "__main__":
    # Antes de iniciar, o @app.before_first_request já terá criado a tabela
    app.run(host="0.0.0.0", port=10000)
