from gerar_noite import (HEAD, FOOT, MARCA, tela, abas, sec, topo,
                         BG, BG2, BG3, LINHA, LIN2, AM, AM2, AMSUA, AMBOR,
                         T, T2, T3, T4, T5, PLACA, CARTAO, ELEV, ROTULO)

PLAY = '<svg width="15" height="15" viewBox="0 0 24 24" fill="currentColor"><polygon points="6 4 20 12 6 20 6 4"></polygon></svg>'
BAIXAR = ('<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">'
          '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>'
          '<polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>')
SETA = ('<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2">'
        '<line x1="5" y1="12" x2="19" y2="12"></line><polyline points="12 5 19 12 12 19"></polyline></svg>')

BTN_AM = (f'font-family: inherit; font-weight: 600; color: #101318; '
          f'background: linear-gradient(180deg, {AM} 0%, {AM2} 100%); border: none; '
          f'border-radius: 9px; cursor: pointer; display: flex; align-items: center; '
          f'justify-content: center; gap: 9px;')
BTN_LIN = (f'font-family: inherit; font-size: 13px; font-weight: 500; color: {T2}; '
           f'background: {BG3}; border: 1px solid {LINHA}; border-radius: 9px; '
           f'padding: 10px 15px; cursor: pointer;')
BTN_FANT = (f'font-family: inherit; font-size: 11.5px; font-weight: 500; color: {T3}; '
            f'background: transparent; border: 1px solid {LINHA}; border-radius: 8px; '
            f'padding: 6px 11px; cursor: pointer;')


# ══════════════════════════════════════════════════ peças da coluna esquerda ══
def guia_nomes():
    linhas = ''.join(
        f'<div style="display: flex; align-items: center; justify-content: space-between; gap: 10px;">'
        f'<div style="display: flex; flex-direction: column; gap: 1px;">'
        f'<span style="font-size: 12.5px; font-weight: 500; color: {T};">{n}</span>'
        f'<span style="font-size: 10.5px; color: {T4};">{d}</span></div>'
        f'<span style="font-family: ui-monospace, monospace; font-size: 11px; color: {T2}; '
        f'background: {BG}; border: 1px solid {LINHA}; border-radius: 6px; padding: 4px 8px; '
        f'flex-shrink: 0;">{a}</span></div>'
        for n, d, a in [('Hook', 'o gancho que prende', 'Hook1.mp4'),
                        ('CTA', 'a chamada pra agir', 'CTA1.mp4'),
                        ('Story', 'a história / contexto', 'Story.mp4'),
                        ('Revelação', 'a virada', 'Revelacao.mp4'),
                        ('Prova', 'resultado / prova social', 'Prova.mp4')])
    return f"""      <div style="padding: 16px; border-bottom: 1px solid {LIN2}; background: linear-gradient(180deg, rgba(255, 199, 0, 0.07) 0%, rgba(11, 14, 18, 0) 78%); display: flex; flex-direction: column; gap: 13px;">
        <div style="display: flex; align-items: center; gap: 11px;">
          <span style="width: 28px; height: 28px; border-radius: 9px; background: {AM}; display: flex; align-items: center; justify-content: center; flex-shrink: 0;">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#101318" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z"></path><line x1="7" y1="7" x2="7.01" y2="7"></line></svg>
          </span>
          <div style="display: flex; flex-direction: column; gap: 1px;">
            <span style="font-size: 13px; font-weight: 600; color: {T};">Como nomear os arquivos</span>
            <span style="font-size: 11px; color: {AM}; opacity: .8;">comece por aqui</span>
          </div>
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="{T4}" stroke-width="2" style="margin-left: auto; transform: rotate(180deg);"><path d="M6 9l6 6 6-6"></path></svg>
        </div>
        <div style="display: flex; flex-direction: column; gap: 10px;">{linhas}</div>
        <div style="font-size: 11px; line-height: 1.55; color: {T3}; border-top: 1px solid {LIN2}; padding-top: 11px;">Numere para multiplicar: <span style="font-family: ui-monospace, monospace; color: {AM};">Hook1</span>, <span style="font-family: ui-monospace, monospace; color: {AM};">Hook2</span>. Bloco longo quebra em <span style="font-family: ui-monospace, monospace; color: {AM};">_pt1</span>, <span style="font-family: ui-monospace, monospace; color: {AM};">_pt2</span>.</div>
      </div>"""


def drop(principal, sub, chip, alto=True):
    pad = '30px 16px' if alto else '22px 16px'
    return f"""        <div style="border: 1px dashed {LINHA}; background: {BG2}; border-radius: 12px; padding: {pad}; display: flex; flex-direction: column; align-items: center; gap: 9px;">
          <div style="width: 44px; height: 44px; border-radius: 12px; background: {BG3}; border: 1px solid {LINHA}; display: flex; align-items: center; justify-content: center;">
            <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="{AM}" stroke-width="1.6" stroke-linecap="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="17 8 12 3 7 8"></polyline><line x1="12" y1="3" x2="12" y2="15"></line></svg>
          </div>
          <div style="display: flex; flex-direction: column; align-items: center; gap: 2px;">
            <span style="font-size: 13.5px; font-weight: 500; color: {T};">{principal}</span>
            <span style="font-size: 11.5px; color: {T3};">{sub}</span>
          </div>
          <span style="font-family: ui-monospace, monospace; font-size: 10.5px; color: {T4}; background: {BG}; border: 1px solid {LINHA}; border-radius: 6px; padding: 4px 9px;">{chip}</span>
        </div>"""


def arquivos():
    itens = ''.join(
        f'<div style="display: flex; align-items: center; gap: 10px; {ELEV} padding: 9px 11px;">'
        f'<span style="width: 5px; height: 22px; border-radius: 3px; background: {cor}; flex-shrink: 0;"></span>'
        f'<div style="display: flex; flex-direction: column; gap: 1px; flex-grow: 1;">'
        f'<span style="font-family: ui-monospace, monospace; font-size: 11.5px; color: {T};">{n}</span>'
        f'<span style="font-size: 10px; color: {T4};">{d}</span></div></div>'
        for n, d, cor in [('Hook1.mp4', 'Hook · 4s', AM), ('Hook2.mp4', 'Hook · 5s', AM),
                          ('Hook3.mp4', 'Hook · 4s', AM), ('Story.mp4', 'fixo · 18s', '#3C4854'),
                          ('Prova.mp4', 'fixo · 9s', '#3C4854'), ('CTA1.mp4', 'CTA · 6s', AM)])
    return f'        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 7px;">{itens}</div>'


def variacoes(dim=False):
    op = ' opacity: .45;' if dim else ''
    p = ''
    for n in (5, 10, 15, 20, 25, 30):
        if n == 15 and not dim:
            p += (f'<div style="height: 38px; background: {AM}; border-radius: 8px; display: flex; '
                  f'align-items: center; justify-content: center; font-size: 13px; font-weight: 700; '
                  f'color: #101318;">15</div>')
        else:
            p += (f'<div style="height: 38px; background: {BG3}; border: 1px solid {LINHA}; border-radius: 8px; '
                  f'display: flex; align-items: center; justify-content: center; font-size: 13px; '
                  f'font-weight: 600; color: {T4};">{n}</div>')
    corpo = (f'        <div style="display: grid; grid-template-columns: repeat(6, minmax(0, 1fr)); gap: 5px;{op}">{p}</div>\n'
             f'        <div style="font-size: 11px; line-height: 1.5; color: {T4};">1 crédito por vídeo entregue — cobrado só na entrega.</div>')
    return sec('Quantas variações', corpo, passo='3')


def headline(dim=False, texto='Ninguém te contou isso sobre tráfego pago'):
    op = ' opacity: .45;' if dim else ''
    cor = T if not dim else T4
    corpo = f"""        <div style="display: flex; gap: 7px;{op}">
          <div style="flex-grow: 1; {ELEV} padding: 10px 12px; font-size: 12.5px; line-height: 1.45; color: {cor}; min-height: 56px;">{texto}</div>
          <div style="width: 66px; {ELEV} display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 1px;">
            <span style="font-size: 19px; font-weight: 700; color: {T};">3</span>
            <span style="font-size: 9.5px; color: {T4};">seg</span>
          </div>
        </div>"""
    return sec('Headline no vídeo', corpo, passo='4',
               acao=f'<span style="font-size: 10.5px; color: {T5};">opcional</span>')


def barra(ativo=True, aviso='', dur=''):
    if ativo:
        botao = f'<button style="{BTN_AM} flex: 1; height: 48px; font-size: 14.5px;">{PLAY}Gerar variações</button>'
    else:
        botao = (f'<button style="font-family: inherit; flex: 1; height: 48px; font-size: 14.5px; '
                 f'font-weight: 600; color: {T5}; background: {BG3}; border: 1px solid {LINHA}; '
                 f'border-radius: 9px; display: flex; align-items: center; justify-content: center; gap: 9px;">{PLAY}Gerar variações</button>')
    linha_dur = ('' if not dur else
                 f'<div style="font-size: 11.5px; line-height: 1.5; color: #6FD08C;">{dur}</div>')
    return f"""      <div style="margin-top: auto; flex-shrink: 0; border-top: 1px solid {LINHA}; background: {BG2}; padding: 14px 16px; display: flex; flex-direction: column; gap: 10px;">
{aviso}
        <div style="display: flex; gap: 8px;">
          {botao}
          <button style="font-family: inherit; width: 48px; height: 48px; color: {T4}; background: transparent; border: 1px solid {LINHA}; border-radius: 9px; display: flex; align-items: center; justify-content: center; cursor: pointer;">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"></path></svg>
          </button>
        </div>
{linha_dur}
      </div>"""


# ══════════════════════════════════════════════════ peças da coluna direita ══
def painel(rotulo, corpo, cresce=False):
    f = ' flex: 1; min-height: 0;' if cresce else ''
    return f"""      <div style="{CARTAO} padding: 16px; display: flex; flex-direction: column; gap: 13px;{f}">
        <span style="{ROTULO}">{rotulo}</span>
{corpo}
      </div>"""


def estrutura(vazio=False):
    if vazio:
        corpo = f"""        <div style="{PLACA} border-radius: 10px; padding: 16px; display: flex; flex-direction: column; gap: 7px;">
          <span style="font-size: 13px; font-weight: 500; color: {T2};">Nada enviado ainda</span>
          <span style="font-size: 11.5px; line-height: 1.55; color: {T4};">Assim que os arquivos entram, o varvid lê os nomes e mostra aqui quais blocos giram e quais ficam.</span>
        </div>"""
        return painel('Estrutura detectada', corpo)
    chips_v = ''.join(
        f'<span style="font-size: 11.5px; font-weight: 500; color: {AM}; background: {AMSUA}; '
        f'border: 1px solid {AMBOR}; border-radius: 7px; padding: 5px 10px;">{c}</span>'
        for c in ['Hook ×3', 'CTA ×1'])
    chips_f = ''.join(
        f'<span style="font-size: 11.5px; font-weight: 500; color: {T3}; background: {BG3}; '
        f'border: 1px solid {LINHA}; border-radius: 7px; padding: 5px 10px;">{c}</span>'
        for c in ['Story', 'Prova'])
    corpo = f"""        <div style="display: flex; flex-direction: column; gap: 11px;">
          <div style="display: flex; flex-direction: column; gap: 7px;">
            <span style="font-size: 11.5px; color: {T4};">Remixam entre si</span>
            <div style="display: flex; flex-wrap: wrap; gap: 6px;">{chips_v}</div>
          </div>
          <div style="display: flex; flex-direction: column; gap: 7px;">
            <span style="font-size: 11.5px; color: {T4};">Ficam iguais</span>
            <div style="display: flex; flex-wrap: wrap; gap: 6px;">{chips_f}</div>
          </div>
        </div>
        <div style="{PLACA} border-radius: 10px; padding: 14px; display: flex; align-items: flex-end; justify-content: space-between; gap: 14px;">
          <div style="display: flex; align-items: flex-end; gap: 11px;">
            <span style="font-size: 40px; font-weight: 700; letter-spacing: -0.035em; line-height: 1; color: {AM};">3</span>
            <span style="font-size: 12.5px; color: {T3}; padding-bottom: 4px;">combinações de takes</span>
          </div>
          <span style="font-family: ui-monospace, monospace; font-size: 11px; color: {T5}; padding-bottom: 5px;">3 × 1</span>
        </div>
        <div style="font-size: 11.5px; line-height: 1.55; color: {T4};">Esgotadas as combinações, ele aplica micro-cortes e zoom para continuar gerando arquivos únicos.</div>"""
    return painel('Estrutura detectada', corpo)


def ajustes():
    def linha(n, s, on):
        if on:
            tag = (f'<span style="font-family: ui-monospace, monospace; font-size: 9.5px; color: #101318; '
                   f'background: {AM}; border-radius: 5px; padding: 4px 7px;">ATIVO</span>')
            borda, cor = f'border: 1px solid {AMBOR}; background: {AMSUA};', T
        else:
            tag = (f'<span style="font-family: ui-monospace, monospace; font-size: 9.5px; color: {T5}; '
                   f'background: {BG3}; border-radius: 5px; padding: 4px 7px;">EM BREVE</span>')
            borda, cor = f'border: 1px solid {LINHA};', T4
        return (f'<div style="{borda} border-radius: 9px; padding: 10px 11px; display: flex; '
                f'align-items: center; gap: 10px;">'
                f'<div style="display: flex; flex-direction: column; gap: 1px; flex-grow: 1;">'
                f'<span style="font-size: 12px; font-weight: 500; color: {cor};">{n}</span>'
                f'<span style="font-size: 10px; color: {T5};">{s}</span></div>{tag}</div>')
    corpo = (f'        <div style="display: flex; flex-direction: column; gap: 7px;">'
             + linha('Micro-cortes', '1–4 quadros no início · 1–3 no fim', True)
             + linha('Zoom sutil', 'reenquadra 1,02× a 1,06×', True)
             + linha('Variação de cor', 'brilho e saturação', False)
             + linha('Pitch de áudio', 'micro ajuste de tom', False)
             + '</div>\n'
             f'        <div style="font-size: 11.5px; line-height: 1.55; color: {T4}; border-top: 1px solid {LIN2}; padding-top: 11px;">Visualmente iguais, com assinatura distinta — arquivo, duração e enquadramento levemente diferentes.</div>')
    return painel('O que muda em cada cópia', corpo)


def vazio_direita(texto):
    return f"""      <div style="flex: 1; min-height: 0; border: 1px dashed {LINHA}; border-radius: 12px; display: flex; align-items: center; justify-content: center; padding: 30px;">
        <div style="font-size: 12px; line-height: 2.1; color: {T5}; text-align: center;">{texto}</div>
      </div>"""
