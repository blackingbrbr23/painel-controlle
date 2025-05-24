import requests

client_id = '0766a7f1-da46-4ef4-8994-823d2cfeda74'  # Altere para o ID do cliente
url = f'http://127.0.0.1:10000/command?id={client_id}'  # Ajuste para o endereço do seu servidor

try:
    response = requests.get(url)
    data = response.json()
    status = data.get('status')

    if status == 'ativo':
        print(f"✅ Cliente {client_id} ATIVO.")
    else:
        print(f"🚫 Cliente {client_id} BLOQUEADO. Contate o suporte.")
except Exception as e:
    print(f"Erro na conexão ou processamento: {e}")
