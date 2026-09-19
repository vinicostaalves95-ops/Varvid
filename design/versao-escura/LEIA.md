# Versão escura — guardada aqui, fora do caminho

Estes dois arquivos são o redesenho escuro do VarVid, do jeito que estavam na
pasta do projeto em 19/09/2026. Eles **não** são servidos: o app lê `app.html` e
`login.html` da raiz, não daqui.

- `app-escuro.html`   → vira `app.html` quando for a hora
- `login-escuro.html` → vira `login.html` quando for a hora

## Por que saíram da raiz

O `subir.sh` publica **tudo** que estiver na pasta. Enquanto o design escuro
estivesse em `app.html`, qualquer deploy levaria ele pro ar junto — inclusive um
deploy feito só pra corrigir outra coisa. Tirar daqui não é abandonar o
redesenho: é separar as duas versões de verdade, como você pediu.

## Quando for implementar

O `app.html` da raiz andou depois disto (correção de cobrança e confirmação do
Limpar). Então não é copiar por cima: é trazer as mudanças da raiz pra dentro do
escuro, ou o contrário. Me chame quando chegar a hora e eu faço a junção
olhando as duas versões lado a lado.
