# Fonte do design do varvid

Isto aqui é o material que **gera** as telas. As telas prontas para olhar estão
um nível acima, em `design/telas/` — abra `design/index.html` para ver o índice.

## O que é cada coisa

```
telas/*.dc.html        as 33 pranchas, uma por tela
  Noite*.dc.html       a versão escura — é a que está no app hoje
  Console*.dc.html     a versão clara, arquivada
  Marca*.dc.html       as três direções de marca (Console foi a escolhida)
  Oficio*/Sinal*       direções não escolhidas, arquivo

gerar_noite.py         paleta, topo e esqueleto da versão escura
telas_noite.py         os pedaços reutilizáveis (balão, guia, variações…)
build_noite.py         monta as 12 telas escuras a partir dos dois acima

gerar_console.py       o mesmo, para a versão clara
telas_console.py
exportar.py            transforma cada .dc.html numa página que abre sozinha
canvas.json            o manifesto do canvas (4 páginas, 33 pranchas)

versao-clara/          o app.html e o login.html da versão clara, como estavam
                       antes de trocar para a escura — caso você queira voltar
```

## Para mexer nas telas escuras

```bash
python3 build_noite.py     # regera as 12 telas escuras
python3 exportar.py        # regera as páginas navegáveis
```

`build_noite.py` monta cada tela chamando os helpers: `palco()` é a coluna
central de leitura, `balao()` é a área de arrastar arquivos, `bloco_esq()` é um
bloco da coluna de apoio. A ordem do mockup é sempre a mesma: balão, variações,
botão de gerar.

## A paleta (escura)

| token | cor | onde |
|---|---|---|
| `--bg` | `#0B0E12` | o fundo de tudo |
| `--bg2` | `#101419` | topo, caixas |
| `--bg3` | `#151A20` | campos, botões neutros |
| `--linha` | `#212932` | bordas |
| `--linha2` | `#1A2028` | divisórias internas |
| `--amarelo` | `#FFC700` | ação primária, um número por bloco |
| texto | `#FFFFFF` · `#C6CDD6` · `#98A1AC` · `#6C7681` · `#4B545E` | do mais forte ao mais apagado |

Tipografia: **Poppins** (400/500/600/700). Tracking apertado nos títulos
(−2,8% a −3,2%), zero no corpo — Poppins é larga e redonda demais para tracking
padrão em display.

**A regra que sustenta tudo:** nada de texto solto no preto. Toda área de apoio
é uma placa que começa um degrau acima do fundo e dissolve num gradiente. O
amarelo cheio aparece só na ação primária e num número por bloco.

## Como isso virou código

`app.html` e `login.html` foram reescritos a partir destes mockups mantendo o
`<script>` byte-a-byte idêntico e todos os ids. Quem garante isso são os dois
arquivos de teste da raiz do projeto:

```bash
node test_login.js    # 30 testes
node test_front.js    # 40 testes
```

Eles montam um DOM falso que cria qualquer elemento por id — por isso a marcação
pode ser reescrita à vontade, desde que o script e os ids sobrevivam. Rode os
dois antes de subir qualquer mudança de tela.

## O que ficou em aberto

- **Mobile** — as telas foram desenhadas em 1440×900. O CSS tem os breakpoints,
  mas ninguém desenhou o mobile de verdade ainda.
- **Member get member** — o próximo da fila.
- A copy "mais venda entrando" (tela 11) é promessa de resultado financeiro.
  Decidir antes de ir ao ar.
