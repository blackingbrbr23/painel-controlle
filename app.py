### app.py

```python
from flask import Flask, request, jsonify, render_template, redirect
import sqlite3, os, json
from datetime import datetime

app = Flask(__name__)

# Path para o banco SQLite (criado automaticamente se não existir)
DB_PATH = os.path.join(app.root_path, "clients.db")
JSON_PATH = os.path.join(app.root_path, "clients.json")

# Cria conexão SQLite e garante tabela

def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

conn = get_conn()
conn.execute("""
CREATE TABLE IF NOT EXISTS clients (
  mac TEXT PRIMARY KEY,
  nome TEXT NOT NULL,
  ip TEXT,
  ativo INTEGER NOT NULL DEFAULT 0,
  last_seen TEXT
)
""")
conn.commit()

# Função para exportar apenas os nomes para JSON

def dump_names_to_json():
    cur = conn.execute("SELECT nome FROM clients")
    names = [row["nome"] for row in cur.fetchall()]
    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(names, f, indent=2, ensure_ascii=False)


def normalize_mac(mac: str) -> str:
    return mac.strip().lower()

@app.route("/command")
def command():
    raw_mac = request.args.get("mac")
    ip = request.args.get("public_ip")
    if not raw_mac:
        return jsonify({"error": "MAC não fornecido"}), 400

    mac = normalize_mac(raw_mac)
    now_iso = datetime.utcnow().isoformat()

    cur = conn.execute("SELECT * FROM clients WHERE mac = ?", (mac,))
    row = cur.fetchone()
    if row is None:
        conn.execute(
            "INSERT INTO clients(mac, nome, ip, ativo, last_seen) VALUES (?, ?, ?, ?, ?)",
            (mac, "Sem nome", ip, 0, now_iso)
        )
    else:
        conn.execute(
            "UPDATE clients SET ip = ?, last_seen = ? WHERE mac = ?",
            (ip, now_iso, mac)
        )
    conn.commit()
    dump_names_to_json()

    cur = conn.execute("SELECT ativo FROM clients WHERE mac = ?", (mac,))
    ativo = bool(cur.fetchone()["ativo"])
    return jsonify({"ativo": ativo})

@app.route("/")
def index():
    cur = conn.execute("SELECT mac, nome, ip, ativo, last_seen FROM clients")
    clients = [dict(r) for r in cur.fetchall()]
    return render_template("index.html", clients=clients)

@app.route("/set", methods=["POST"])
def set_status():
    mac = normalize_mac(request.form.get("mac"))
    status = request.form.get("status")
    ativo = 1 if status == "ACTIVE" else 0
    conn.execute("UPDATE clients SET ativo = ? WHERE mac = ?", (ativo, mac))
    conn.commit()
    dump_names_to_json()
    return redirect("/")

@app.route("/rename", methods=["POST"])
def rename():
    mac = normalize_mac(request.form.get("mac"))
    new_name = request.form.get("nome")
    if new_name:
        conn.execute("UPDATE clients SET nome = ? WHERE mac = ?", (new_name, mac))
        conn.commit()
        dump_names_to_json()
    return redirect("/")

@app.route("/delete", methods=["POST"])
def delete():
    mac = normalize_mac(request.form.get("mac"))
    conn.execute("DELETE FROM clients WHERE mac = ?", (mac,))
    conn.commit()
    dump_names_to_json()
    return redirect("/")

# Rota para exportar todos os clientes (opcional)
@app.route("/export_json")
def export_json():
    cur = conn.execute("SELECT mac, nome, ip, ativo, last_seen FROM clients")
    clients = [
        {"mac": row["mac"], "nome": row["nome"], "ip": row["ip"],
         "ativo": bool(row["ativo"]), "last_seen": row["last_seen"]}
        for row in cur.fetchall()
    ]
    return jsonify(clients)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
```

### templates/index.html

```html
<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Painel de Controle</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
  <style>
    body { background-color: #f8f9fa; padding: 40px; }
    .table th, .table td { vertical-align: middle; }
    .form-inline { display: flex; gap: 10px; }
    .btn-sm { padding: 0.25rem 0.5rem; }
  </style>
</head>
<body>
  <div class="container">
    <h1 class="mb-4">Painel de Controle</h1>
    <table class="table table-bordered table-hover">
      <thead class="table-light">
        <tr>
          <th>MAC</th>
          <th>Nome</th>
          <th>IP</th>
          <th>Status</th>
          <th>Último Ping (UTC)</th>
          <th>Ações</th>
        </tr>
      </thead>
      <tbody>
        {% for client in clients %}
        <tr>
          <td class="text-break">{{ client.mac }}</td>
          <td>
            <form action="/rename" method="post" class="form-inline">
              <input type="hidden" name="mac" value="{{ client.mac }}">
              <input type="text" name="nome" value="{{ client.nome }}" class="form-control form-control-sm">
              <button type="submit" class="btn btn-primary btn-sm">Salvar</button>
            </form>
          </td>
          <td>{{ client.ip }}</td>
          <td>
            {% if client.ativo %}
              <span class="badge bg-success">Ativo</span>
            {% else %}
              <span class="badge bg-danger">Bloqueado</span>
            {% endif %}
          </td>
          <td>{{ client.last_seen or '—' }}</td>
          <td>
            <form action="/set" method="post" style="display:inline">
              <input type="hidden" name="mac" value="{{ client.mac }}">
              <input type="hidden" name="status" value="ACTIVE">
              <button type="submit" class="btn btn-success btn-sm">Ativar</button>
            </form>
            <form action="/set" method="post" style="display:inline">
              <input type="hidden" name="mac" value="{{ client.mac }}">
              <input type="hidden" name="status" value="BLOCKED">
              <button type="submit" class="btn btn-danger btn-sm">Bloquear</button>
            </form>
            <form action="/delete" method="post" style="display:inline" onsubmit="return confirm('Tem certeza que deseja excluir este cliente?');">
              <input type="hidden" name="mac" value="{{ client.mac }}">
              <button type="submit" class="btn btn-warning btn-sm">Excluir</button>
            </form>
          </td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
  <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
```

```html
<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Painel de Controle</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
  <style>
    body { background-color: #f8f9fa; padding: 40px; }
    .table th, .table td { vertical-align: middle; }
    .form-inline { display: flex; gap: 10px; }
    .btn-sm { padding: 0.25rem 0.5rem; }
  </style>
</head>
<body>
  <div class="container">
    <h1 class="mb-4">Painel de Controle</h1>
    <table class="table table-bordered table-hover">
      <thead class="table-light">
        <tr>
          <th>MAC</th>
          <th>Nome</th>
          <th>IP</th>
          <th>Status</th>
          <th>Último Ping (UTC)</th>
          <th>Ações</th>
        </tr>
      </thead>
      <tbody>
        {% for client in clients %}
        <tr>
          <td class="text-break">{{ client.mac }}</td>
          <td>
            <form action="/rename" method="post" class="form-inline">
              <input type="hidden" name="mac" value="{{ client.mac }}">
              <input type="text" name="nome" value="{{ client.nome }}" class="form-control form-control-sm">
              <button type="submit" class="btn btn-primary btn-sm">Salvar</button>
            </form>
          </td>
          <td>{{ client.ip }}</td>
          <td>
            {% if client.ativo %}
              <span class="badge bg-success">Ativo</span>
            {% else %}
              <span class="badge bg-danger">Bloqueado</span>
            {% endif %}
          </td>
          <td>{{ client.last_seen or '—' }}</td>
          <td>
            <form action="/set" method="post" style="display:inline">
              <input type="hidden" name="mac" value="{{ client.mac }}">
              <input type="hidden" name="status" value="ACTIVE">
              <button type="submit" class="btn btn-success btn-sm">Ativar</button>
            </form>
            <form action="/set" method="post" style="display:inline">
              <input type="hidden" name="mac" value="{{ client.mac }}">
              <input type="hidden" name="status" value="BLOCKED">
              <button type="submit" class="btn btn-danger btn-sm">Bloquear</button>
            </form>
            <form action="/delete" method="post" style="display:inline" onsubmit="return confirm('Tem certeza que deseja excluir este cliente?');">
              <input type="hidden" name="mac" value="{{ client.mac }}">
              <button type="submit" class="btn btn-warning btn-sm">Excluir</button>
            </form>
          </td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
  <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
```
