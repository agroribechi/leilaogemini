# Leilão OCR — MVP local

Protótipo desktop em Python para ler dados exibidos em uma transmissão de leilão aberta na tela. Ele captura somente as regiões calibradas de **lote**, **preço** e **descrição**, aplica OCR local, normaliza os valores e grava mudanças estáveis em um histórico SQLite local.

## O que este MVP faz

- Calibra, por arraste, a área do vídeo e as três regiões de leitura.
- Salva a calibração em `data/calibration.json`.
- Captura a tela a cada 1,2 segundos sem baixar nem retransmitir o vídeo.
- Usa Tesseract com pré-processamento de imagem e idioma português.
- Só registra uma alteração após duas leituras consecutivas iguais, reduzindo ruído do OCR.
- Exibe a leitura atual e mantém o histórico em `data/auction.db`.
- Possui um painel operacional para escolher ou cadastrar o leilão que receberá os eventos.

## Requisitos

1. Windows 10/11 e Python 3.11 ou superior.
2. [Tesseract OCR para Windows](https://github.com/UB-Mannheim/tesseract/wiki), instalado com o pacote de idioma **Português (`por`)**.

## Instalação e execução

Abra o PowerShell nesta pasta e execute:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app.py
```

Se o executável do Tesseract não estiver disponível automaticamente, informe o caminho:

```powershell
python app.py --tesseract "C:\Program Files\Tesseract-OCR\tesseract.exe"
```

Depois da primeira instalação, também é possível iniciar por duplo clique em `Iniciar-Leilao-OCR.cmd`. Ele já está configurado para usar `C:\Program Files\Tesseract-OCR\tesseract.exe`.

## Como usar

1. Abra a transmissão no navegador e deixe o player no tamanho/monitor que será usado.
2. Clique em **Capturar e calibrar**. No quadro exibido, selecione cada opção e arraste: área do vídeo, lote, preço e descrição.
3. Salve a calibração e clique em **Iniciar leitura**.
4. Confirme os dados no painel e consulte os eventos na lista ao lado.

Recalibre sempre que o tamanho do navegador, o zoom, a resolução ou a posição do player mudarem. Para melhor resultado, use o player em tela cheia, resolução alta e regiões de texto sem bordas/ícones.

## Estrutura e próximos passos

```text
app.py                 interface local e orquestração
leilao_ocr/capture.py  captura de tela
leilao_ocr/ocr.py      OCR e preparação de imagem
leilao_ocr/normalization.py  conversão para lote/preço/descrição
leilao_ocr/history.py  armazenamento local (SQLite)
leilao_ocr/publisher.py ponto de integração externa
```

Para a próxima fase, mantenha este capturador como um agente local e implemente um `FastApiPublisher` em `publisher.py`, que envie o `Reading.as_dict()` autenticado para uma API FastAPI. Essa API validará o evento e o gravará no Supabase; o aplicativo dos assinantes consumirá as atualizações via Supabase Realtime. Dessa forma, somente dados estruturados e imagens autorizadas seguem para os usuários, sem depender do OCR no celular ou de redistribuir o vídeo do YouTube.

O painel **Operação do leilão** do aplicativo local já grava a escolha no campo `auction_id` de cada leitura. Na integração com a API, esse mesmo campo será a chave que direciona o evento para a transmissão e os assinantes corretos.

### Publicação em tempo real (API local)

Com a API da pasta `../leilao-api` em execução, inicie o capturador pelo PowerShell assim:

```powershell
$env:LEILAO_API_URL = "http://127.0.0.1:8000"
python app.py --tesseract "C:\Program Files\Tesseract-OCR\tesseract.exe"
```

O indicador muda para **API em tempo real** e cada leitura estável é enviada para `POST /api/readings`.

Para facilitar a operação diária, com a API já aberta, dê duplo clique em `Iniciar-Leilao-Online.cmd`. O iniciador padrão continua disponível para uso somente local.

## Limites importantes

O MVP não baixa vídeo do YouTube, não redistribui a transmissão e não substitui permissões de uso do organizador. Antes de oferecer o vídeo aos assinantes, obtenha autorização do titular e avalie as regras da plataforma e os direitos de transmissão.
