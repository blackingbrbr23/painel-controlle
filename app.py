{% raw %}
<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <title>Painel de Controle</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body class="p-4">
  <div class="container">
    <h1 class="mb-4">Painel de Controle</h1>
    <table class="table table-bordered table-hover">
      <thead class="table-light">
        <tr>
          <th>MAC</th>
          <th>Nome</th>
          <th>IP</th>
          <th>Status</th>
          <th>Último Ping</th>
          <th>Ações</th>
        </tr>
      </thead>
      <tbody>
        {% for mac, data in clients.items() %}
        <tr>
          <td>{{ mac }}</td>
          <td>
            <form action="/rename" method="post" class="d-flex gap-1">
              <input type="hidden" name="mac" value="{{ mac }}">
              <input type="text" name="nome" value="{{ data.nome }}" class="form-control form-control-sm">
              <button class="btn btn-primary btn-sm">Salvar</button>
            </form>
          </td>
          <td>{{ data.ip }}</td>
          <td>
            {% if data.ativo %}
              <span class="badge bg-success">Ativo</span>
            {% else %}
              <span class="badge bg-danger">Bloqueado</span>
            {% endif %}
          </td>
          <td>{{ data.last_seen or "—" }}</td>
          <td>
            <form action="/set" method="post" style="display:inline">
              <input type="hidden" name="mac" value="{{ mac }}">
              <input type="hidden" name="status" value="ACTIVE">
              <button class="btn btn-success btn-sm">Ativar</button>
            </form>
            <form action="/set" method="post" style="display:inline">
              <input type="hidden" name="mac" value="{{ mac }}">
              <input type="hidden" name="status" value="BLOCKED">
              <button class="btn btn-danger btn-sm">Bloquear</button>
            </form>
            <form action="/delete" method="post" style="display:inline">
              <input type="hidden" name="mac" value="{{ mac }}">
              <button class="btn btn-warning btn-sm">Excluir</button>
            </form>
          </td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
</body>
</html>
{% endraw %}
