from flask import Flask, request, jsonify
import json

app = Flask(__name__)

@app.route('/command')
def command():
    client_id = request.args.get('id')
    if not client_id:
        return jsonify({"error": "ID não fornecido"}), 400

    try:
        with open('clients.json', 'r') as f:
            clients = json.load(f)
    except Exception as e:
        return jsonify({"error": "Erro ao ler clients.json", "details": str(e)}), 500

    client = clients.get(client_id)
    if not client:
        return jsonify({"status": "bloqueado", "message": "Cliente não encontrado"})

    if client.get("ativo", False):
        return jsonify({"status": "ativo", "message": "Cliente liberado"})
    else:
        return jsonify({"status": "bloqueado", "message": "Cliente bloqueado"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
