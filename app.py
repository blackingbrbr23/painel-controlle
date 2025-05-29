from flask import Flask, request, redirect, render_template
import os
import dropbox
import json

app = Flask(__name__)

# Conectar ao Dropbox
DROPBOX_TOKEN = os.getenv("DROPBOX_TOKEN")
dbx = dropbox.Dropbox(DROPBOX_TOKEN)

# Dicionário de clientes (você pode integrar com banco depois)
clientes = {}

@app.route('/')
def index():
    return render_template('index.html', clientes=clientes)

@app.route('/rename/<mac>', methods=['POST'])
def rename(mac):
    novo_nome = request.form['new_name']
    
    clientes[mac] = {
        'mac': mac,
        'nome': novo_nome
    }

    salvar_cliente_dropbox(clientes[mac])
    return redirect('/')

@app.route('/command')
def command():
    mac = request.args.get('mac')
    public_ip = request.args.get('public_ip')

    # Se ainda não registrado
    if mac and mac not in clientes:
        clientes[mac] = {
            'mac': mac,
            'nome': 'Desconhecido',
            'ip': public_ip
        }
        salvar_cliente_dropbox(clientes[mac])

    return "OK"

def salvar_cliente_dropbox(cliente):
    try:
        dados = json.dumps(cliente, indent=4)
        caminho = f"/clientes/{cliente['mac'].replace(':', '_')}.json"
        dbx.files_upload(dados.encode(), caminho, mode=dropbox.files.WriteMode.overwrite)
        print(f"[✓] Cliente salvo no Dropbox: {caminho}")
    except Exception as e:
        print(f"[X] Erro ao salvar cliente no Dropbox: {e}")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
