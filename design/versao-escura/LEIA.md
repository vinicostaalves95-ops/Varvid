# Versão escura — pronta e alinhada com a produção

Estes dois arquivos são o redesenho escuro do VarVid, **já com todas as
funcionalidades que estão no ar em 19/09/2026**. Eles não são servidos: o app lê
`app.html` e `login.html` da raiz, não daqui.

- `app-escuro.html`   → vira `app.html` quando você decidir
- `login-escuro.html` → vira `login.html` junto

## O que foi feito em 19/09

O redesenho tinha sido criado a partir da versão de 13/09 e ficou parado enquanto
a produção andava. As duas linhas foram juntadas por merge de três vias, com a
versão de 13/09 como base comum. Seis conflitos, todos resolvidos mantendo o
visual do escuro e trazendo a função da produção:

- a linha de duração saiu do fim da coluna e foi pra baixo do upload
- o Limpar ganhou o id que o faz virar a própria pergunta antes de apagar
- entrou o botão "Indique e ganhe" na barra do topo
- entrou o modal de indicação inteiro, desenhado nos tokens do escuro
- entrou o CSS dos dois, também nos tokens do escuro

## A garantia

Os dois arquivos são **funcionalmente idênticos** aos que estão no ar. Conferido
por comparação, não por leitura:

- o JavaScript é o mesmo, ignorando comentários e espaços
- os mesmos ids de elemento, nos dois arquivos
- os mesmos handlers `onclick`/`onchange` no HTML
- as mesmas rotas chamadas no servidor
- todos os 16 ganchos de classe e `data-*` que o JS usa existem nos dois

E a suíte inteira (307 testes) passa com estes arquivos no lugar dos de produção,
mais os roteiros de tela: login, indicação e contador de duração.

## O que muda de verdade

Só o visual — e um ganho: **o escuro tem media queries, a produção não**. Ou
seja, trocar resolve também o item de mobile da planilha de QA.

## Detalhe pra não esquecer na hora de trocar

O escuro tem três textos com número fixo que a produção não tem:
"até 1min30" (duas vezes) e "Seus vídeos ficam por 48 horas". Hoje batem com o
servidor. Se o limite de duração ou a retenção mudarem, esses textos passam a
mentir — o `results-warn` se atualiza sozinho, esses três não. Vale ligá-los ao
servidor antes de trocar, ou aceitar o risco sabendo dele.
