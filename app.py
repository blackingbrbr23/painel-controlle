import os
import eventlet
eventlet.monkey_patch()

from datetime import datetime
from flask import Flask, request, jsonify, render_template, redirect
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO

app = Flask(__name__)
# Usa PostgreSQL em produção (DATABASE_URL) ou SQLite local
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///clients.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
# Eventlet automaticamente fará o servidor web + WS
socketio = SocketIO(app, cors_allowed_origins="*")

class Client(db.Model):
    mac = db.Column(db.String, primary_key=True)
    nome = db.Column(db.String, default='Sem nome')
    ip = db.Column(db.String)
    ativo = db.Column(db.Boolean, default=False)
    last_seen = db.Column(db.DateTime)

def emit_update(client: Client):
    payload = {
        'mac': client.mac,
        'nome': client.nome,
        'ip': client.ip,
        'ativo': client.ativo,
        'last_seen': client.last_seen.isoformat() if client.last_seen else None
    }
    socketio.emit('client_update', payload)

@app.route('/')
def index():
    clients = Client.query.all()
    clients_dict = {
        c.mac: {
            'nome': c.nome,
            'ip': c.ip,
            'ativo': c.ativo,
            'last_seen': c.last_seen.isoformat() if c.last_seen else ''
        } for c in clients
    }
    return render_template('index.html', clients=clients_dict)

@app.route('/command')
def command():
    mac = request.args.get('mac')
    ip = request.args.get('public_ip')
    if not mac:
        return jsonify({'error': 'MAC não fornecido'}), 400

    now = datetime.utcnow()
    client = Client.query.get(mac)
    if client:
        client.ip = ip
        client.last_seen = now
        ativo = client.ativo
    else:
        client = Client(mac=mac, nome='Sem nome', ip=ip, ativo=False, last_seen=now)
        db.session.add(client)
        ativo = False

    db.session.commit()
    emit_update(client)
    return jsonify({'ativo': ativo})

@app.route('/rename/<mac>', methods=['POST'])
def rename(mac):
    nome = request.form.get('nome','').strip()
    client = Client.query.get(mac)
    if client and nome:
        client.nome = nome
        db.session.commit()
        emit_update(client)
    return redirect('/')

@app.route('/set/<mac>/<status>', methods=['POST'])
def set_status(mac, status):
    client = Client.query.get(mac)
    if client:
        client.ativo = (status == 'ACTIVE')
        db.session.commit()
        emit_update(client)
    return redirect('/')

@app.route('/delete/<mac>', methods=['POST'])
def delete(mac):
    client = Client.query.get(mac)
    if client:
        db.session.delete(client)
        db.session.commit()
        socketio.emit('client_delete', {'mac': mac})
    return redirect('/')

if __name__ == '__main__':
    # Cria as tabelas dentro do contexto da app
    with app.app_context():
        db.create_all()

    # Roda com Eventlet (HTTP + WS) sem o erro de Werkzeug
    socketio.run(app, host='0.0.0.0', port=10000)
