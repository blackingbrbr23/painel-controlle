import os
import jsonrom flask import Flask, request, jsonify, render_template, redirect
from datetime import datetime

# Configuração da aplicação
app = Flask(__name__)

# Caminho do disco persistente (Render)
PERSISTENT_PATH = os.getenv('RENDER_PERSISTENT_DISK_PATH', '/data')
DATA_FILE = os.path.join(PERSISTENT_PATH, 'clients.json')

# Garante diretório e arquivo
os.makedirs(PERSISTENT_PATH, exist_ok=True)
if not os.path.isfile(DATA_FILE):
    with open(DATA_FILE, 'w') as f:
        json.dump({}, f)

# Funções utilitárias para JSON
def load_clients():
    with open(DATA_FILE, 'r') as f:
        return json.load(f)

def save_clients(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2, default=str)

@app.route("/command")
def command():
    mac = request.args.get("mac")
    ip  = request.args.get("public_ip")
    if not mac:
        return jsonify({"error": "MAC não fornecido"}), 400

    clients = load_clients()
    now = datetime.utcnow().isoformat()

    if mac not in clients:
        clients[mac] = {
            'nome': 'Sem nome',
            'ip': ip,
            'ativo': False,
            'cadastrado': False,
            'last_seen': now
        }
    else:
        clients[mac]['ip'] = ip
        clients[mac]['last_seen'] = now

    save_clients(clients)
    return jsonify({"ativo": clients[mac]['ativo']})

@app.route("/")
def index():
    clients = load_clients()
    # Converte dict para lista de objetos para template
    clients_list = []
    for mac, data in sorted(clients.items()):
        obj = {'mac': mac}
        obj.update(data)
        clients_list.append(obj)
    return render_template("index.html", clients=clients_list)

@app.route("/set/<mac>/<status>", methods=["POST"])
def set_status(mac, status):
    clients = load_clients()
    if mac in clients:
        clients[mac]['ativo'] = (status == "ACTIVE")
        save_clients(clients)
    return redirect("/")

@app.route("/rename/<mac>", methods=["POST"])
def rename(mac):
    new_name = request.form.get("nome")
    clients = load_clients()
    if mac in clients and new_name:
        clients[mac]['nome'] = new_name
        clients[mac]['cadastrado'] = True
        save_clients(clients)
    return redirect("/")

@app.route("/delete/<mac>", methods=["POST"])
def delete(mac):
    clients = load_clients()
    if mac in clients:
        del clients[mac]
        save_clients(clients)
    return redirect("/")

if __name__ == "__main__":
    port = int(os.getenv('PORT', 10000))
    app.run(host="0.0.0.0", port=port)
