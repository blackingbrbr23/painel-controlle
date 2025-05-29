from flask import Flask, request, redirect, render_template
import os
import dropbox
import json

app = Flask(__name__)

# Conectar ao Dropbox
DROPBOX_TOKEN = os.getenv("DROPBOX_TOKEN")
if not DROPBOX_TOKEN:
    raise ValueError("DROPBOX_TOKEN não definido nas variáveis de ambiente.")

dbx = dropbox.Dropbox(DROPBOX_TOKEN)

# Dicionário de clientes
clientes = {}

@app.route('/')
def index():
    return render_template('index.html', clients=clientes)

@app.route('/rename/<mac>', methods=['POST'])
def rename(mac):
    novo_nome = request.form['nome']
    if mac in clientes:
        clientes[mac]['nome'] = novo_nome
    else:
        clientes[mac] = {'mac': mac, 'nome': novo_nome, 'ip': '', 'ativo': True}

    salvar_cliente_dropbox(clientes[mac])
    return redirect('/')

@app.route('/command')
def command():
    mac = request.args.get('mac')
    public_ip = request.args.get('public_ip')

    if mac:
        if mac not in clientes:
            clientes[mac] = {
                'mac': mac,
                'nome': 'Desconhecido',
                'ip': public_ip,
                'ativo': True
            }
        else:
            clientes[mac]['ip'] = public_ip

        salvar_cliente_dropbox(clientes[mac])

    return "OK"

@app.route('/set/<mac>/<status>', methods=['POST'])
def set_status(mac, status):
    if mac in clientes:
        clientes[mac]['ativo'] = (status == 'ACTIVE')
        salvar_cliente_dropbox(clientes[mac])
    return redirect('/')

@app.route('/delete/<mac>', methods=['POST'])
def delete(mac):
    if mac in clientes:
        del clientes[mac]
        caminho = f"/clientes/{mac.replace(':', '_')}.json"
        try:
            dbx.files_delete_v2(caminho)
        except Exception as e:
            print(f"[!] Erro ao deletar no Dropbox: {e}")
    return redirect('/')

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

