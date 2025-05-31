from flask import Flask, request, jsonify, render_template, redirect
import psycopg2
from datetime import datetime

app = Flask(__name__)

# ------------------------------------------------------------
# 1) STRING DE CONEXÃO COM O SUPABASE (com password URL-encoded)
# ------------------------------------------------------------
DATABASE_URL = "postgresql://postgres:%40%40W365888aw@db.olmnsorpzkxojrgljyy.supabase.co:5432/postgres"

def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

# ------------------------------------------------------------
# 2) CRIAÇÃO AUTOMÁTICA DA TABELA 'clients'
# ------------------------------------------------------------
def init_db():
    conn = get_db_connection()
    with conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS clients (
                    mac TEXT PRIMARY KEY,
                    nome TEXT,
                    ip TEXT,
                    ativo BOOLEAN DEFAULT FALSE,
                    last_seen TIMESTAMPTZ
                );
            """)
    conn.close()

# Garante que a tabela exista ao iniciar o script
init_db()

# ------------------------------------------------------------
# 3) DICIONÁRIO TEMPORÁRIO (clientes “pingados”, mas não salvos)
# ------------------------------------------------------------
temp_clients = {}

# ------------------------------------------------------------
# 4) ROTA /command: cliente envia MAC e IP; marca ativo ou armazena em RAM
# ------------------------------------------------------------
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
                # Cliente já existe no banco: atualiza IP e last_seen
                cur.execute(
                    "UPDATE clients SET ip = %s, last_seen = %s WHERE mac = %s",
                    (ip, now_iso, mac)
                )
                conn.commit()
                ativo = row[0]
            else:
                # Cliente não existe: guarda em RAM como temporário
                temp_clients[mac] = {
                    "nome": "Sem nome",
                    "ip": ip,
                    "ativo": False,
                    "last_seen": now_iso
                }
                ativo = False

    return jsonify({"ativo": ativo})

# ------------------------------------------------------------
# 5) ROTA /: exibe lista de clientes (persistidos + temporários)
# ------------------------------------------------------------
@app.route("/")
def index():
    clients = {}

    # 1) Busca todos os clientes persistidos no Supabase
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

    # 2) Junta com os temporários que ainda não foram salvos
    for mac, data in temp_clients.items():
        if mac not in clients:
            clients[mac] = data

    return render_template("index.html", clients=clients, temp_clients=set(temp_clients.keys()))

# ------------------------------------------------------------
# 6) ROTA /set/<mac>/<status>: altera status ativo/bloqueado
# ------------------------------------------------------------
@app.route("/set/<mac>/<status>", methods=["POST"])
def set_status(mac, status):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE clients SET ativo = %s WHERE mac = %s",
                (status == "ACTIVE", mac)
            )
            conn.commit()
    return redirect("/")

# ------------------------------------------------------------
# 7) ROTA /rename/<mac>: insere ou atualiza nome do cliente
# ------------------------------------------------------------
@app.route("/rename/<mac>", methods=["POST"])
def rename(mac):
    new_name = request.form.get("nome")
    if not new_name:
        return redirect("/")

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # Verifica se já existe no banco
            cur.execute("SELECT 1 FROM clients WHERE mac = %s", (mac,))
            exists = cur.fetchone()

            if exists:
                # Atualiza o nome
                cur.execute(
                    "UPDATE clients SET nome = %s WHERE mac = %s",
                    (new_name, mac)
                )
            else:
                # Insere um novo registro, puxando dados de temp_clients (se houver)
                temp_data = temp_clients.get(mac)
                ip = temp_data["ip"] if temp_data else request.remote_addr
                last_seen = temp_data["last_seen"] if temp_data else datetime.utcnow().isoformat()

                cur.execute("""
                    INSERT INTO clients (mac, nome, ip, ativo, last_seen)
                    VALUES (%s, %s, %s, %s, %s)
                """, (mac, new_name, ip, False, last_seen))

                # Remove da memória temporária
                if mac in temp_clients:
                    del temp_clients[mac]

            conn.commit()

    return redirect("/")

# ------------------------------------------------------------
# 8) ROTA /delete/<mac>: exclui cliente do Supabase + RAM
# ------------------------------------------------------------
@app.route("/delete/<mac>", methods=["POST"])
def delete(mac):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM clients WHERE mac = %s", (mac,))
            conn.commit()

    if mac in temp_clients:
        del temp_clients[mac]

    return redirect("/")

# ------------------------------------------------------------
# 9) RODA O APP
# ------------------------------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
