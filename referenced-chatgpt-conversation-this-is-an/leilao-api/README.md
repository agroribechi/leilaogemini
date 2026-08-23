# Arremate API — desenvolvimento local

API local que recebe leituras do capturador e envia eventos em tempo real aos painéis e aplicativos.

## Iniciar

No Windows, a forma mais simples é dar duplo clique em `Iniciar-API.cmd`.

Se preferir usar o PowerShell, primeiro entre na pasta `leilao-api` e execute:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn --app-dir . app.main:app --reload
```

O serviço abre em `http://127.0.0.1:8000`; a documentação interativa fica em `http://127.0.0.1:8000/docs`.

## Fluxo de dados

1. Crie um leilão em `POST /api/auctions`.
2. O capturador envia um evento para `POST /api/readings`.
3. O painel e o aplicativo assinam `ws://127.0.0.1:8000/ws/auctions/{auction_id}`.
4. Uma correção humana é publicada em `POST /api/readings/{reading_id}/corrections`.

SQLite é usado somente no desenvolvimento. A futura camada Supabase substituirá `app/database.py`, mantendo os contratos da API.
