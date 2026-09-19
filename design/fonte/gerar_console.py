# Gera as telas da direção C · Console a partir de um chrome compartilhado,
# para que nav, topo e tokens sejam idênticos em todas.

HEAD = """<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <script src="./support.js"></script>
</head>
<body>
<x-dc>
<helmet>
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700;800&display=swap">
  <style>
    body { margin: 0; }
    a { color: #101318; } a:hover { color: #8A6E00; }
  </style>
</helmet>
"""

FOOT = """</x-dc>
</body>
</html>
"""

MARK = ('<svg width="22" height="22" viewBox="0 0 22 22" fill="none">'
        '<rect x="1" y="6" width="4" height="10" rx="2" fill="{c}"></rect>'
        '<rect x="7" y="2" width="4" height="18" rx="2" fill="{c}"></rect>'
        '<rect x="13" y="5" width="4" height="12" rx="2" fill="#FFC700"></rect>'
        '<rect x="19" y="8" width="3" height="6" rx="1.5" fill="{c}" opacity="0.3"></rect></svg>')

ICON = {
 'gerar': '<polygon points="6 4 20 12 6 20 6 4"></polygon>',
 'biblioteca': '<rect x="3" y="3" width="18" height="18" rx="2"></rect><path d="M3 9h18M9 21V9"></path>',
 'consumo': '<path d="M3 17l6-6 4 4 8-8"></path><path d="M21 7v6h-6"></path>',
 'plano': '<rect x="2" y="5" width="20" height="14" rx="2"></rect><path d="M2 10h20"></path>',
 'conta': '<circle cx="12" cy="8" r="4"></circle><path d="M4 21c0-4.4 3.6-7 8-7s8 2.6 8 7"></path>',
}
LABEL = {'gerar': 'Gerar', 'biblioteca': 'Biblioteca', 'consumo': 'Consumo',
         'plano': 'Plano e cobrança', 'conta': 'Conta'}


def nav_item(key, active, badge=None):
    if active:
        return (f'<div style="display: flex; align-items: center; gap: 11px; background: #101318; '
                f'color: #FFFFFF; border-radius: 9px; padding: 10px 12px;">'
                f'<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="#FFC700" '
                f'stroke-width="1.8">{ICON[key]}</svg>'
                f'<span style="font-size: 13.5px; font-weight: 500;">{LABEL[key]}</span></div>')
    b = ('' if badge is None else
         f'<span style="margin-left: auto; font-family: ui-monospace, monospace; font-size: 11px; '
         f'color: #8A93A0;">{badge}</span>')
    return (f'<div style="display: flex; align-items: center; gap: 11px; border-radius: 9px; '
            f'padding: 10px 12px; color: #4A525E;">'
            f'<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
            f'stroke-width="1.7">{ICON[key]}</svg>'
            f'<span style="font-size: 13.5px;">{LABEL[key]}</span>{b}</div>')


def nav(active, biblioteca='128', zerado=False):
    itens = ''.join([
        nav_item('gerar', active == 'gerar'),
        nav_item('biblioteca', active == 'biblioteca', biblioteca),
        nav_item('consumo', active == 'consumo'),
        nav_item('plano', active == 'plano'),
        nav_item('conta', active == 'conta'),
    ])
    if zerado:
        saldo, plano, pct, nota, cor = ('0', 'plano Free', 0,
                                        'Cota esgotada · reinicia em 14/10/2026', '#8A93A0')
    else:
        saldo, plano, pct, nota, cor = ('1.284', 'plano Pro', 71,
                                        'Repõe 1.800 em 14/09/2027', '#101318')
    return f"""  <div style="background: #FFFFFF; border-right: 1px solid #E3E6EA; display: flex; flex-direction: column; padding: 18px 14px; gap: 22px;">
    <div style="display: flex; align-items: center; gap: 9px; padding: 0 6px;">
      {MARK.format(c='#101318')}
      <span style="font-size: 18px; font-weight: 700; letter-spacing: -0.022em;">varvid</span>
    </div>

    <div style="display: flex; flex-direction: column; gap: 3px;">{itens}</div>

    <div style="margin-top: auto; display: flex; flex-direction: column; gap: 11px; background: #F2F3F5; border: 1px solid #E3E6EA; border-radius: 11px; padding: 14px;">
      <div style="display: flex; align-items: baseline; justify-content: space-between;">
        <span style="font-size: 11.5px; color: #5B6470;">Saldo</span>
        <span style="font-family: ui-monospace, monospace; font-size: 10.5px; color: #8A93A0;">{plano}</span>
      </div>
      <div style="display: flex; align-items: baseline; gap: 6px;">
        <span style="font-size: 28px; font-weight: 700; letter-spacing: -0.028em; line-height: 1; color: {cor};">{saldo}</span>
        <span style="font-size: 12px; color: #5B6470;">créditos</span>
      </div>
      <div style="height: 5px; border-radius: 3px; background: #E9EDF2; overflow: hidden;"><div style="width: {pct}%; height: 100%; background: #FFC700;"></div></div>
      <span style="font-size: 11px; color: #8A93A0; line-height: 1.45;">{nota}</span>
    </div>
  </div>
"""


def topbar(*crumbs):
    sep = ('<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#C3C9D1" '
           'stroke-width="2"><polyline points="9 18 15 12 9 6"></polyline></svg>')
    parts = []
    for i, c in enumerate(crumbs):
        last = i == len(crumbs) - 1
        cor = 'font-weight: 500;' if last else 'color: #8A93A0;'
        parts.append(f'<span style="{cor}">{c}</span>')
        if not last:
            parts.append(sep)
    return f"""    <div style="height: 56px; flex-shrink: 0; background: #FFFFFF; border-bottom: 1px solid #E3E6EA; display: flex; align-items: center; justify-content: space-between; padding: 0 24px;">
      <div style="display: flex; align-items: center; gap: 9px; font-size: 13px;">{''.join(parts)}</div>
      <div style="display: flex; align-items: center; gap: 14px;">
        <span style="font-size: 12.5px; color: #5B6470;">vinicius@omnisblue.com.br</span>
        <div style="width: 30px; height: 30px; border-radius: 50%; background: #101318; color: #FFFFFF; display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 600;">VC</div>
      </div>
    </div>
"""


def tela(nome, corpo, ativo='gerar', crumbs=('Estúdio',), biblioteca='128', zerado=False):
    html = (HEAD +
            '\n<div style="width: 1440px; height: 900px; background: #F2F3F5; color: #101318; '
            "font-family: 'Poppins', system-ui, sans-serif; display: grid; "
            'grid-template-columns: 236px 1fr; overflow: hidden;">\n\n' +
            nav(ativo, biblioteca, zerado) +
            '\n  <div style="display: flex; flex-direction: column; min-width: 0;">\n\n' +
            topbar(*crumbs) + '\n' + corpo +
            '\n  </div>\n</div>\n' + FOOT)
    open(nome, 'w', encoding='utf-8').write(html)
    print('escrito', nome)


ROTULO = ('font-size: 10.5px; font-weight: 600; letter-spacing: 0.14em; '
          'text-transform: uppercase; color: #8A93A0;')
CARTAO = 'background: #FFFFFF; border: 1px solid #E3E6EA; border-radius: 12px;'


def abas(ativa):
    def b(txt, on):
        if on:
            return ('<button style="font-family: inherit; font-size: 12.5px; font-weight: 500; '
                    'color: #FFFFFF; background: #101318; border: none; border-radius: 7px; '
                    f'padding: 7px 14px; cursor: pointer;">{txt}</button>')
        return ('<button style="font-family: inherit; font-size: 12.5px; font-weight: 500; '
                'color: #5B6470; background: transparent; border: none; border-radius: 7px; '
                f'padding: 7px 14px; cursor: pointer;">{txt}</button>')
    return ('<div style="display: inline-flex; background: #F2F3F5; border: 1px solid #E3E6EA; '
            'border-radius: 9px; padding: 3px; gap: 3px;">'
            + b('Remix de takes', ativa == 'remix') + b('Vídeo único', ativa == 'unico') + '</div>')


def cabecalho(titulo, nota, direita):
    marca = ('' if not nota else
             '<span style="font-family: ui-monospace, monospace; font-size: 11.5px; '
             f'color: #8A93A0;">{nota}</span>')
    return f"""        <div style="{CARTAO} padding: 12px 16px; display: flex; align-items: center; justify-content: space-between; gap: 16px;">
          <div style="display: flex; align-items: baseline; gap: 11px;">
            <h1 style="margin: 0; font-size: 22px; font-weight: 700; letter-spacing: -0.028em;">{titulo}</h1>
            {marca}
          </div>
          {direita}
        </div>"""
