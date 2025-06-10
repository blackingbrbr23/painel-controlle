from flask import Flask, request, jsonify, render_template, redirect, url_for, session, flash
import psycopg2
from datetime import datetime, timedelta
import threading, time
from functools import wraps
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.secret_key = 'SUBSTITUA_POR_UMA_CHAVE_SECRETA_SEGURA'
DATABASE_URL = "postgresql://postgres.olmnsorpzkxqojrgljyy:%40%40W365888aw@aws-0-sa-east-1.pooler.supabase.com:6543/postgres"

# — Usuário único de admin —
ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD_HASH = generate_password_hash('@@@blackingbrbr@@')  # ajuste aqui

def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

def init_db():
    with get_db_connection() as conn:
        with conn.cursor() as cur:
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

# Clientes que pingaram mas ainda não salvaram
temp_clients = {}

# Cache de último estado ativo/block para cada MAC
active_cache = {}

# — Decorator de login para rotas da interface web —
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login', next=request.path))
        return f(*args, **kwargs)
    return decorated

# — Endpoint público para o cliente —
@app.route('/command')
def command():
    """
    Público: cliente chama para saber se está ativo.
    Usa active_cache como fallback se o banco falhar.
    """
    mac = request.args.get("mac")
    ip  = request.args.get("public_ip")
    if not mac:
        return jsonify({"error":"MAC não fornecido"}),400

    now_utc = datetime.utcnow()

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT ativo, expiration_timestamp FROM clients WHERE mac=%s",
                    (mac,)
                )
                row = cur.fetchone()

                if row:
                    ativo_db, _ = row
                    ativo = ativo_db
                    # atualiza IP e last_seen
                    cur.execute(
                        "UPDATE clients SET ip=%s, last_seen=%s WHERE mac=%s",
                        (ip, now_utc.isoformat(), mac)
                    )
                else:
                    ativo = False
                    temp_clients[mac] = {
                        "nome":"Sem nome",
                        "ip":ip,
                        "ativo":False,
                        "last_seen":now_utc.isoformat()
                    }

                conn.commit()

        # atualiza cache sempre que o banco respondeu
        active_cache[mac] = ativo

    except Exception as e:
        print(f"Erro /command (usa cache): {e}")
        # se já tivermos um valor no cache, devolve-o; senão, assume True
        ativo = active_cache.get(mac, True)

    return jsonify({"ativo": ativo})

# — Rotas de login/logout para a interface web —
@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        u = request.form['username']
        p = request.form['password']
        if u == ADMIN_USERNAME and check_password_hash(ADMIN_PASSWORD_HASH, p):
            session['logged_in'] = True
            return redirect(request.args.get('next') or url_for('index'))
        flash('Usuário ou senha inválidos.', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# — Rotas protegidas servem a interface web (somente após login) —
@app.route('/')
@login_required
def index():
    clients = {}
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT mac, nome, ip, ativo, last_seen, expiration_timestamp FROM clients"
            )
            for mac,nome,ip,ativo,last_seen,exp_ts in cur.fetchall():
                iso   = exp_ts.strftime("%Y-%m-%dT%H:%M:%SZ") if exp_ts else None
                human = exp_ts.strftime("%Y-%m-%d %H:%M UTC") if exp_ts else None
                clients[mac] = {
                    "nome":nome,
                    "ip":ip,
                    "ativo":ativo,
                    "expiration":iso,
                    "expiration_human":human
                }
    # junta temporários
    for mac,data in temp_clients.items():
        if mac not in clients:
            clients[mac] = {
                "nome":data["nome"],
                "ip":data["ip"],
                "ativo":data["ativo"],
                "expiration":None,
                "expiration_human":None
            }
    return render_template(
        'index.html',
        clients=clients,
        temp_clients=set(temp_clients.keys())
    )

@app.route('/set/<mac>/<status>', methods=['POST'])
@login_required
def set_status(mac, status):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            if status == "ACTIVE":
                cur.execute(
                    "UPDATE clients SET ativo=TRUE, expiration_timestamp=NULL WHERE mac=%s",
                    (mac,)
                )
            else:
                cur.execute(
                    "UPDATE clients SET ativo=FALSE WHERE mac=%s",
                    (mac,)
                )
            conn.commit()
    return redirect(url_for('index'))

@app.route('/rename/<mac>', methods=['POST'])
@login_required
def rename(mac):
    new_name = request.form.get("nome")
    date_str = request.form.get("expiration_date")
    secs_str = request.form.get("expiration_seconds")
    exp_ts   = None

    if date_str:
        try:
            exp_ts = datetime.fromisoformat(date_str)
        except:
            pass
    elif secs_str:
        try:
            exp_ts = datetime.utcnow() + timedelta(seconds=int(secs_str))
        except:
            pass

    if not new_name:
        return redirect(url_for('index'))

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM clients WHERE mac=%s", (mac,))
            if cur.fetchone():
                cur.execute(
                    "UPDATE clients SET nome=%s, expiration_timestamp=%s WHERE mac=%s",
                    (new_name, exp_ts, mac)
                )
            else:
                temp = temp_clients.get(mac, {})
                ip   = temp.get("ip") or request.remote_addr
                last = temp.get("last_seen") or datetime.utcnow().isoformat()
                cur.execute("""
                    INSERT INTO clients
                        (mac, nome, ip, ativo, last_seen, expiration_timestamp)
                    VALUES
                        (%s, %s, %s, FALSE, %s, %s)
                """, (mac, new_name, ip, last, exp_ts))
                temp_clients.pop(mac, None)
            conn.commit()
    return redirect(url_for('index'))

@app.route('/delete/<mac>', methods=['POST'])
@login_required
def delete(mac):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM clients WHERE mac=%s", (mac,))
            conn.commit()
    temp_clients.pop(mac, None)
    return redirect(url_for('index'))

# — Worker que bloqueia expirados —
def expiration_worker():
    while True:
        now = datetime.utcnow()
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        UPDATE clients SET ativo=FALSE
                         WHERE expiration_timestamp<=%s AND ativo=TRUE
                    """, (now,))
                    conn.commit()
        except:
            pass
        time.sleep(60)

if __name__ == "__main__":
    init_db()
    t = threading.Thread(target=expiration_worker, daemon=True)
    t.start()
    app.run(host='0.0.0.0', port=10000)
