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
    ├── 01-login.html                  entrada, a única tela escura e com movimento
    ├── 02-inicio.html                 escolha do modo, consumo, últimas gerações
    ├── 03-remix-antes-dos-arquivos.html
    ├── 04-remix-com-takes.html
    ├── 05-video-unico.html
    ├── 06-gerando.html
    ├── 07-resultados.html
    ├── 08-creditos-esgotados.html
    ├── 09-popup-planos.html
    ├── 10-popup-legal.html
    ├── 11-como-funciona.html          página aberta, antes do login
    ├── 12-roteiro-pronto.html         página aberta, com o prompt
    ├── marca-console.html             símbolo, paleta, tipografia, componentes
    └── arquivo-*.html                 as duas direções não escolhidas
```

Cada arquivo em `telas/` abre sozinho no navegador — duplo clique resolve.
São HTML estático com estilo em linha, feitos para serem lidos ao lado do
código na hora de implementar.

`varvid-identidade-visual.html` é o canvas completo, com as três páginas e as
anotações de decisão.

---

## As decisões

**Marca.** Barras verticais de alturas diferentes — quadros da mesma peça, a
mesma peça em versões diferentes. Some o verde-limão.

**Cor.** Grafite `#101318`, amarelo `#FFC700`, fundo frio `#F2F3F5`.
O amarelo marca a ação primária e **um número por cartão**. Em nenhum outro
lugar.

**Tipografia.** Poppins em tudo — 400/500/600 na interface, 700/800 no display.
Mono do sistema para dados (id de geração, nome de arquivo). Como Poppins é mais
larga que a maioria, o tracking negativo é contido: ver `--vv-track-*`.

**Superfícies.** Nenhum texto solto no fundo. Todo bloco se apoia num cartão
branco ou numa placa, e a placa é um gradiente que dissolve no fundo em vez de
virar caixa. Título de várias linhas escurece para claro.

**Peso escuro é reservado.** O único bloco escuro do produto é o aviso de
créditos esgotados, e mesmo ele em degradê. Em toda outra tela, destaque é
amarelo sobre claro. A regra: escuro só quando existe uma ação imediata e clara
a tomar.

**Arquitetura.** Menu fixo à esquerda — Gerar, Biblioteca, Consumo, Plano e
cobrança, Conta. Trilha de navegação no topo, cartão de saldo no pé do menu.
As duas abas (Remix de takes e Vídeo único) vivem no mesmo cabeçalho: trocar de
modo não troca de tela.

**Vocabulário.** O que a pessoa faz é uma **geração**, nunca "job". O
identificador é `id_8f3a21`.

---

## O que a Console exige que hoje não existe

Ela pressupõe que **a geração é um registro permanente**, não só um arquivo
temporário de 48 horas:

- **Biblioteca** — lista de gerações com id, modo, quantidade e data, que
  continua existindo depois de os arquivos serem apagados.
- **Consumo** — quanto da cota do ciclo já foi usado.
- **Plano e cobrança** dentro do app, não só num modal.

As telas 06 e 07 mostram a mesma geração em dois momentos justamente para
deixar claro o que precisa sobreviver ao fim do render.

---

## Pendências que as telas deixam visíveis

Na tela `10-popup-legal.html`, os campos em amarelo marcam o que falta escrever
nos documentos: **nome do responsável, CPF/CNPJ e canal de contato**. É
exigência da LGPD e é o que protege numa disputa de cartão — precisa entrar
antes da primeira cobrança.

Nas telas `11` e `12` há dois espaços marcados para preencher: a **foto de quem
faz o varvid** e o **nome** de quem assina a citação. Uma imagem de gente vale
mais ali do que qualquer ilustração.

O prompt da tela 12 mora dentro do botão — o texto completo está no documento
`prompt-roteiro-varvid.md`, no projeto do Claude.

**Mobile ainda não foi desenhado.** Continua como prioridade 1 de código: o
`app.html` não tem uma única media query.

---

## Como editar

O canvas editável vive como artifact no Claude, com as três páginas e o
histórico de versões. Os arquivos aqui são uma exportação: mexer neles não
volta para o canvas.
