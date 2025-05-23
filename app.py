from flask import Flask, request, jsonify
import json
import os

app = Flask(__name__)

CLIENTS_FILE = 'clients.json'
clients = {}

def load_clients():
    global clients
    if os.path.exists(CLIENTS_FILE):
        try:
            with open(CLIENTS_FILE, 'r') as f:
                clients = json.load(f)
        except Exception as e:
            print("Erro ao carregar clients.json:", e)
            clients = {}

def save_clients():
    try:
        with open(CLIENTS_FILE, 'w') as f:
            json.dump(clients, f, indent=2)
    except Exception as e:
        print("Erro ao salvar clients.json:", e)

@app.route('/command', methods=['GET'])
def get_command():
    client_id = request.args.get('id')
    public_ip = request.args.get('public_ip') or request.remote_addr

    if not client_id:
        return jsonify({'error': 'Missing id parameter'}), 400

    if client_id not in clients:
        clients[client_id] = {
            'command': 'BLOCK',
            'ip': public_ip,
            'name': 'Desconhecido'
        }
    else:
        clients[client_id]['ip'] = public_ip

    save_clients()
    return jsonify({'command': clients[client_id]['command']})

@app.route('/set/<client_id>/<cmd>', methods=['POST'])
def set_command(client_id, cmd):
    if client_id not in clients:
        return jsonify({'status': 'error', 'message': 'Client not found'}), 404
    if cmd.upper() in ['ACTIVATE', 'BLOCK']:
        clients[client_id]['command'] = cmd.upper()
        save_clients()
        return jsonify({'status': 'ok', 'client_id': client_id, 'command': cmd.upper()})
    return jsonify({'status': 'error', 'message': 'Invalid command'}), 400

@app.route('/rename/<client_id>', methods=['POST'])
def rename_client(client_id):
    data = request.get_json()
    new_name = data.get('name')
    if client_id not in clients:
        return jsonify({'status': 'error', 'message': 'Client not found'}), 404
    if not new_name:
        return jsonify({'status': 'error', 'message': 'Name is required'}), 400
    clients[client_id]['name'] = new_name
    save_clients()
    return jsonify({'status': 'ok', 'client_id': client_id, 'new_name': new_name})

@app.route('/clients', methods=['GET'])
def list_clients():
    return jsonify(clients)

if __name__ == '__main__':
    load_clients()
    port = int(os.environ.get('PORT', 5000))  # Para compatibilidade com Render
    app.run(host='0.0.0.0', port=port)
