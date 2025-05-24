import requests
import sys
import uuid

def get_client_id():
    path = 'client_id.txt'
    try:
        with open(path, 'r') as f:
            return f.read().strip()
    except FileNotFoundError:
        cid = str(uuid.uuid4())
        with open(path, 'w') as f:
            f.write(cid)
        return cid

def get_public_ip():
    try:
        return requests.get("https://api.ipify.org").text.strip()
    except:
        return 'N/A'

# ✅ Atualize aqui com o link gerado pelo Render
SERVER = 'https://painel-api-k2v2.onrender.com'

if __name__ == '__main__':
    cid = get_client_id()
    ip_publico = get_public_ip()
    try:
        resp = requests.get(f'{SERVER}/command', params={'id': cid, 'public_ip': ip_publico}, timeout=5)
        resp.raise_for_status()
        cmd = resp.json().get('command')

        if cmd == 'ACTIVATE':
            print(f'✅ Cliente {cid} ATIVADO. Iniciando processo...')
            # Coloque aqui a função principal do seu programa, por exemplo:
            # from seu_script import run_automation
            # run_automation()
        else:
            print(f'🚫 Cliente {cid} BLOQUEADO. Contate o suporte.')
            sys.exit(1)

    except Exception as e:
        print('❌ Erro ao conectar ao painel:', e)
        sys.exit(2)
