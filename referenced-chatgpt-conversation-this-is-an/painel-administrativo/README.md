# Arremate Operações — painel administrativo

Protótipo navegável do painel usado pela equipe de operação. Ele é separado do aplicativo dos assinantes e do capturador OCR local.

## Abrir

Dê duplo clique em `Iniciar-Painel-Administrativo.cmd`. Ele abre o painel no endereço `http://127.0.0.1:5173` e evita usar uma cópia antiga da página no navegador.

Antes, deixe a API aberta com `../leilao-api/Iniciar-API.cmd`.

## Incluído nesta versão

- Painel de acompanhamento do leilão ao vivo.
- Leitura atual, preço, lote, descrição e precisão do OCR.
- Fila de revisão e correção manual.
- Cadastro de leilões.
- Visões de leilões, assinantes e configurações.

Os dados ainda são demonstrativos. A próxima integração conectará o painel à FastAPI e ao Supabase para receber as leituras do capturador e publicar as correções em tempo real.
