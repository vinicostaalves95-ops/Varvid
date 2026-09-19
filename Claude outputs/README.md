# Design do varvid — direção C · Console

Mockups da nova identidade visual e da nova arquitetura de tela.
**Nada aqui roda em produção.** É referência para implementar.

O app atual (`app.html`, `login.html`, `legal.html`, na raiz do repositório)
segue intocado.

---

## O que tem aqui

```
design/
├── tokens.css                      variáveis de cor, tipografia e forma
├── varvid-identidade-visual.html   o canvas inteiro, abre no navegador
└── telas/
    ├── 01-login.html
    ├── 02-inicio.html
    ├── 03-remix-de-takes.html
    ├── 04-video-unico.html
    ├── 05-gerando.html
    ├── 06-resultados.html
    ├── 07-popup-planos.html
    ├── 08-popup-legal.html
    ├── marca-console.html          símbolo, paleta, tipografia, componentes
    └── arquivo-*.html              as duas direções não escolhidas
```

Cada arquivo em `telas/` abre sozinho no navegador — duplo clique resolve.
São HTML estático com estilo em linha, feitos para serem lidos ao lado do
código na hora de implementar.

`varvid-identidade-visual.html` é o canvas completo, com as três páginas e as
anotações de decisão. É o mesmo conteúdo, visto de cima.

---

## As decisões

**Marca.** Barras verticais de alturas diferentes — quadros da mesma peça, a
mesma peça em versões diferentes. Some o verde-limão.

**Cor.** Grafite `#101318`, amarelo `#FFC700`, fundo frio `#F2F3F5`.
O amarelo marca a ação primária e **um número por cartão**. Em nenhum outro
lugar.

**Tipografia.** Poppins em tudo — 400/500/600 na interface, 700/800 no display.
Mono do sistema para dados (id de job, nome de arquivo). Como Poppins é mais
larga que a maioria, o tracking negativo é contido: ver `--vv-track-*`.

**Superfícies.** Nenhum texto solto no fundo. Todo bloco se apoia num cartão
branco ou numa placa, e a placa é um gradiente que dissolve no fundo em vez de
virar caixa. Título de várias linhas escurece para claro.

**Arquitetura.** Menu fixo à esquerda — Gerar, Biblioteca, Consumo, Plano e
cobrança, Conta. Trilha de navegação no topo, cartão de saldo no pé do menu.
As duas abas (Remix de takes e Vídeo único) vivem no mesmo cabeçalho: trocar de
modo não troca de tela.

---

## O que a Console exige que hoje não existe

Ela pressupõe que **o job é um registro permanente**, não só um arquivo
temporário de 48 horas:

- **Biblioteca** — lista de jobs com id, modo, quantidade e data, que continua
  existindo depois de os arquivos serem apagados.
- **Consumo** — quanto da cota do ciclo já foi usado.
- **Plano e cobrança** dentro do app, não só num modal.

É a maior diferença em relação ao que está no ar. As telas 05 e 06 mostram o
mesmo job em dois momentos justamente para deixar claro o que precisa
sobreviver ao fim do render.

---

## Pendências que as telas deixam visíveis

Na tela `08-popup-legal.html`, os campos em amarelo marcam o que falta escrever
nos documentos: **nome do responsável, CPF/CNPJ e canal de contato**. É
exigência da LGPD e é o que protege numa disputa de cartão — precisa entrar
antes da primeira cobrança. Reembolso proporcional em 7 dias e limite de
responsabilidade seguem para revisão jurídica.

**Mobile ainda não foi desenhado.** Continua como prioridade 1 de código: o
`app.html` não tem uma única media query.

---

## Como editar

O canvas editável vive como artifact no Claude, com as três páginas e o
histórico de versões. Os arquivos aqui são uma exportação: mexer neles não
volta para o canvas.
