import os
import json
import dropbox
from flask import Flask, request, jsonify

app = Flask(__name__)
DROPBOX_TOKEN = os.getenv("DROPBOX_TOKEN")
DROPBOX_PATH = "/clients.json"

# Inicializa o cliente Dropbox
dbx = dropbox.Dropbox(DROPBOX_TOKEN)

def carregar_json_dropbox():
    try:
        _, res = dbx.files_download(DROPBOX_PATH)
        data = json.loads(res.content)
        return data
    except dropbox.exceptions.ApiError:
        # Se o arquivo não existe ainda, retorna lista vazia
        return []

def salvar_json_dropbox(data):
    json_data = json.dumps(data, indent=2)
    dbx.files_upload(
        json_data.encode('utf-8'),
        DROPBOX_PATH,
        mode=dropbox.files.WriteMode.overwrite
    )

@app.route("/salvar_cliente", methods=["POST"])
def salvar_cliente():
    novo_cliente = request.json
    clientes = carregar_json_dropbox()

    # Verifica se já existe cliente com mesmo MAC
    for c in clientes:
        if c["mac"] == novo_cliente["mac"]:
            return jsonify({"erro": "Cliente já cadastrado."}), 400

    clientes.append(novo_cliente)
    salvar_json_dropbox(clientes)
    return jsonify({"mensagem": "Cliente salvo com sucesso."}), 200

@app.route("/clientes", methods=["GET"])
def listar_clientes():
    clientes = carregar_json_dropbox()
    return jsonify(clientes)

if __name__ == "__main__":
    app.run(debug=True)
