from flask import Flask, request, jsonify, render_template, redirect
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os

app = Flask(__name__)
# Configuração do banco SQLite
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///clients.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Modelo de Cliente
class Client(db.Model):
    mac       = db.Column(db.String(17), primary_key=True)
    nome      = db.Column(db.String(100), nullable=False, default='Sem nome')
    ip        = db.Column(db.String(45))
    ativo     = db.Column(db.Boolean, default=False)
    last_seen = db.Column(db.DateTime)

# Cria o banco e as tabelas caso não existam
with app.app_context():
    db.create_all()

@app.route("/command")
def command():
    mac = request.args.get("mac")
    ip  = request.args.get("public_ip")
    if not mac:
        return jsonify({"error": "MAC não fornecido"}), 400

    cliente = Client.query.get(mac)
    now = datetime.utcnow()
    if not cliente:
        # novo cliente
        cliente = Client(mac=mac, ip=ip, last_seen=now)
        db.session.add(cliente)
    else:
        # atualiza IP e timestamp
        cliente.ip = ip
        cliente.last_seen = now

    db.session.commit()
    return jsonify({"ativo": cliente.ativo})

@app.route("/")
def index():
    # lista todos os clientes ordenados por MAC
    clients = Client.query.order_by(Client.mac).all()
    return render_template("index.html", clients=clients)

@app.route("/set/<mac>/<status>", methods=["POST"])
def set_status(mac, status):
    c = Client.query.get(mac)
    if c:
        c.ativo = (status == "ACTIVE")
        db.session.commit()
    return redirect("/")

@app.route("/rename/<mac>", methods=["POST"])
def rename(mac):
    new_name = request.form.get("nome")
    c = Client.query.get(mac)
    if c and new_name:
        c.nome = new_name
        db.session.commit()
    return redirect("/")

@app.route("/delete/<mac>", methods=["POST"])
def delete(mac):
    c = Client.query.get(mac)
    if c:
        db.session.delete(c)
        db.session.commit()
    return redirect("/")

if __name__ == "__main__":
    # host e porta podem ser ajustados conforme necessidade
    app.run(host="0.0.0.0", port=10000)
