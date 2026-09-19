# Versão NOITE: a arquitetura que já está no Render — topo + duas colunas de
# 340px — com a linguagem que veio da Console: superfícies, fade, marca nova,
# contador de crédito em evidência e os avisos redesenhados.
#
# O escuro deixa de ser chapado. Em vez de #080808 com borda #1e1e1e, cada
# bloco tem seu próprio nível de elevação e as placas dissolvem no fundo.

HEAD = """<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <script src="./support.js"></script>
</head>
<body>
<x-dc>
<helmet>
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700&display=swap">
  <style>
    body { margin: 0; }
    a { color: #FFC700; } a:hover { color: #FFD84A; }
  </style>
</helmet>
"""

FOOT = """</x-dc>
</body>
</html>
"""

# ── paleta ──────────────────────────────────────────────────────────────────
BG    = '#0B0E12'   # fundo da aplicação
BG2   = '#101419'   # cartão
BG3   = '#151A20'   # cartão elevado / campo
LINHA = '#212932'
LIN2  = '#1A2028'
AM    = '#FFC700'
AM2   = '#FFD336'
AMSUA = 'rgba(255, 199, 0, 0.10)'
AMBOR = 'rgba(255, 199, 0, 0.28)'
T     = '#FFFFFF'
T2    = '#C6CDD6'
T3    = '#98A1AC'
T4    = '#6C7681'
T5    = '#4B545E'

# A placa: o gradiente que apoia texto sem virar caixa.
PLACA = f'background: linear-gradient(180deg, #1A212A 0%, rgba(11, 14, 18, 0) 100%);'
CARTAO = f'background: {BG2}; border: 1px solid {LINHA}; border-radius: 12px;'
ELEV   = f'background: {BG3}; border: 1px solid {LINHA}; border-radius: 10px;'
ROTULO = (f'font-size: 10.5px; font-weight: 600; letter-spacing: 0.14em; '
          f'text-transform: uppercase; color: {T4};')

MARCA = ('<svg width="22" height="22" viewBox="0 0 22 22" fill="none">'
         '<rect x="1" y="6" width="4" height="10" rx="2" fill="#FFFFFF"></rect>'
         '<rect x="7" y="2" width="4" height="18" rx="2" fill="#FFFFFF"></rect>'
         '<rect x="13" y="5" width="4" height="12" rx="2" fill="#FFC700"></rect>'
         '<rect x="19" y="8" width="3" height="6" rx="1.5" fill="#FFFFFF" opacity="0.3"></rect></svg>')


def topo(creditos='1.284', baixo=False):
    """O contador de crédito é o elemento mais forte do topo: amarelo cheio
    sobre escuro, com o número em destaque. Antes ele era só mais uma pílula."""
    if baixo:
        pilula = (f'<div style="display: flex; align-items: center; gap: 9px; background: {BG3}; '
                  f'border: 1px solid {AMBOR}; border-radius: 999px; padding: 7px 15px 7px 12px;">'
                  f'<span style="width: 7px; height: 7px; border-radius: 50%; background: {AM};"></span>'
                  f'<span style="font-size: 15px; font-weight: 700; color: {AM}; letter-spacing: -0.02em;">{creditos}</span>'
                  f'<span style="font-size: 12px; color: {T3};">créditos</span></div>')
    else:
        pilula = (f'<div style="display: flex; align-items: baseline; gap: 7px; background: {AM}; '
                  f'border-radius: 999px; padding: 7px 16px;">'
                  f'<span style="font-size: 15px; font-weight: 700; color: #101318; letter-spacing: -0.02em;">{creditos}</span>'
                  f'<span style="font-size: 12px; font-weight: 500; color: #6B5A00;">créditos</span></div>')
    return f"""  <div style="height: 58px; flex-shrink: 0; background: {BG2}; border-bottom: 1px solid {LINHA}; display: flex; align-items: center; justify-content: space-between; padding: 0 20px;">
    <div style="display: flex; align-items: center; gap: 10px;">
      {MARCA}
      <span style="font-size: 17px; font-weight: 700; letter-spacing: -0.022em; color: {T};">varvid</span>
      <span style="font-family: ui-monospace, monospace; font-size: 10px; color: {T4}; background: {BG3}; border: 1px solid {LINHA}; border-radius: 999px; padding: 3px 9px; margin-left: 2px;">v6.0</span>
    </div>
    <div style="display: flex; align-items: center; gap: 12px;">
      {pilula}
      <button style="font-family: inherit; font-size: 12.5px; font-weight: 500; color: {T2}; background: transparent; border: 1px solid {LINHA}; border-radius: 9px; padding: 8px 14px; cursor: pointer;">Planos</button>
      <span style="font-size: 12.5px; color: {T4};">vinicius@omnisblue.com.br</span>
      <button style="font-family: inherit; font-size: 12.5px; color: {T4}; background: transparent; border: none; cursor: pointer;">Sair</button>
    </div>
  </div>
"""


def tela(nome, esquerda, direita, creditos='1.284', baixo=False):
    html = (HEAD +
            f'\n<div style="width: 1440px; height: 900px; background: {BG}; color: {T}; '
            "font-family: 'Poppins', system-ui, sans-serif; display: flex; "
            'flex-direction: column; overflow: hidden;">\n\n' +
            topo(creditos, baixo) +
            '\n  <div style="flex: 1; min-height: 0; display: grid; grid-template-columns: 340px 1fr;">\n\n'
            f'    <div style="border-right: 1px solid {LINHA}; display: flex; flex-direction: column; min-height: 0;">\n'
            + esquerda + '\n    </div>\n\n'
            f'    <div style="background: {BG}; display: flex; flex-direction: column; gap: 16px; padding: 18px; min-height: 0; overflow: hidden;">\n'
            + direita + '\n    </div>\n  </div>\n</div>\n' + FOOT)
    open(nome, 'w', encoding='utf-8').write(html)
    print('escrito', nome)


def abas(ativa):
    def b(txt, icone, on):
        if on:
            return (f'<button style="flex: 1; height: 40px; font-family: inherit; font-size: 12.5px; '
                    f'font-weight: 600; color: #101318; background: {AM}; border: none; border-radius: 8px; '
                    f'display: flex; align-items: center; justify-content: center; gap: 7px; cursor: pointer;">'
                    f'<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#101318" '
                    f'stroke-width="1.9">{icone}</svg>{txt}</button>')
        return (f'<button style="flex: 1; height: 40px; font-family: inherit; font-size: 12.5px; '
                f'font-weight: 500; color: {T3}; background: transparent; border: none; border-radius: 8px; '
                f'display: flex; align-items: center; justify-content: center; gap: 7px; cursor: pointer;">'
                f'<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="{T3}" '
                f'stroke-width="1.8">{icone}</svg>{txt}</button>')
    ico_remix = ('<rect x="3" y="3" width="7" height="7" rx="1.5"></rect><rect x="14" y="3" width="7" height="7" rx="1.5"></rect>'
                 '<rect x="3" y="14" width="7" height="7" rx="1.5"></rect><rect x="14" y="14" width="7" height="7" rx="1.5"></rect>')
    ico_unico = '<polygon points="23 7 16 12 23 17 23 7"></polygon><rect x="1" y="5" width="15" height="14" rx="2"></rect>'
    return f"""      <div style="padding: 16px 16px 0;">
        <div style="display: flex; gap: 5px; background: {BG2}; border: 1px solid {LINHA}; border-radius: 11px; padding: 5px;">
          {b('Remix de takes', ico_remix, ativa == 'remix')}{b('Vídeo único', ico_unico, ativa == 'unico')}
        </div>
      </div>"""


def sec(rotulo, corpo, acao='', passo=None, placa=False):
    """Seção da coluna esquerda. Com placa, o rótulo se apoia num degradê que
    dissolve — é o que tira o texto de cima do fundo cru."""
    num = ''
    if passo:
        num = (f'<span style="width: 22px; height: 22px; border-radius: 50%; border: 1.5px solid {AMBOR}; '
               f'background: {AMSUA}; color: {AM}; font-size: 10px; font-weight: 600; display: flex; '
               f'align-items: center; justify-content: center; flex-shrink: 0;">{passo}</span>')
    fundo = PLACA if placa else ''
    return f"""      <div style="padding: 16px; border-bottom: 1px solid {LIN2}; display: flex; flex-direction: column; gap: 12px; {fundo}">
        <div style="display: flex; align-items: center; justify-content: space-between; gap: 10px;">
          <div style="display: flex; align-items: center; gap: 10px;">{num}<span style="{ROTULO}">{rotulo}</span></div>
          {acao}
        </div>
{corpo}
      </div>"""
