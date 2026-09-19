from gerar_noite import (tela, abas, BG, BG2, BG3, LINHA, LIN2, AM, AM2,
                         AMSUA, AMBOR, T, T2, T3, T4, T5, PLACA, CARTAO, ELEV, ROTULO)
from telas_noite import (PLAY, BAIXAR, SETA, BTN_AM, BTN_LIN, BTN_FANT,
                         guia_nomes, arquivos, painel, estrutura)

# A virada desta leva: o trabalho saiu da coluna estreita e foi para o meio da
# tela. O balão de arquivos é o herói, as variações vêm logo abaixo e o botão
# de gerar fecha a sequência — tudo na mesma coluna de leitura.
# A esquerda virou apoio: modo, guia, headline e o que o varvid detectou.


# ══════════════════════════════════════════════════ coluna esquerda (apoio) ══
def bloco_esq(rotulo, corpo, acao='', placa=False, cresce=False):
    fundo = PLACA if placa else ''
    f = ' flex: 1; min-height: 0;' if cresce else ''
    return f"""      <div style="padding: 16px; border-bottom: 1px solid {LIN2}; display: flex; flex-direction: column; gap: 12px; {fundo}{f}">
        <div style="display: flex; align-items: center; justify-content: space-between; gap: 10px;">
          <span style="{ROTULO}">{rotulo}</span>
          {acao}
        </div>
{corpo}
      </div>"""


def headline_esq(dim=False, texto='Ninguém te contou isso sobre tráfego pago'):
    op = ' opacity: .45;' if dim else ''
    cor = T if not dim else T4
    corpo = f"""        <div style="display: flex; flex-direction: column; gap: 8px;{op}">
          <div style="{ELEV} padding: 11px 12px; font-size: 12.5px; line-height: 1.45; color: {cor}; min-height: 62px;">{texto}</div>
          <div style="display: flex; align-items: center; justify-content: space-between; gap: 10px; {ELEV} padding: 9px 12px;">
            <span style="font-size: 11.5px; color: {T3};">Fica na tela por</span>
            <div style="display: flex; align-items: baseline; gap: 5px;">
              <span style="font-size: 17px; font-weight: 700; color: {T};">3</span>
              <span style="font-size: 10.5px; color: {T4};">segundos</span>
            </div>
          </div>
        </div>
        <div style="font-size: 11px; line-height: 1.5; color: {T4};">Escrito por cima do vídeo, com um estilo diferente em cada variação.</div>"""
    return bloco_esq('Headline no vídeo', corpo,
                     acao=f'<span style="font-size: 10.5px; color: {T5};">opcional</span>')


def qual_modo():
    corpo = f"""        <div style="display: flex; flex-direction: column; gap: 11px;">
          <div style="display: flex; flex-direction: column; gap: 2px; border-left: 2px solid {AM}; padding-left: 11px;">
            <span style="font-size: 12px; font-weight: 500; color: {T};">Tenho o vídeo pronto</span>
            <span style="font-size: 11px; line-height: 1.5; color: {T4};">quero várias versões dele → este modo</span>
          </div>
          <div style="display: flex; flex-direction: column; gap: 2px; border-left: 2px solid {LINHA}; padding-left: 11px;">
            <span style="font-size: 12px; font-weight: 500; color: {T2};">Tenho takes separados</span>
            <span style="font-size: 11px; line-height: 1.5; color: {T4};">hook, story, CTA → Remix de takes</span>
          </div>
        </div>"""
    return bloco_esq('Qual modo usar', corpo)


def estrutura_esq(vazio=False):
    if vazio:
        corpo = f"""        <div style="font-size: 11.5px; line-height: 1.6; color: {T4};">Assim que os arquivos entram, o varvid lê os nomes e mostra aqui quais blocos giram e quais ficam.</div>"""
        return bloco_esq('Estrutura detectada', corpo, cresce=True)
    chips_v = ''.join(
        f'<span style="font-size: 11.5px; font-weight: 500; color: {AM}; background: {AMSUA}; '
        f'border: 1px solid {AMBOR}; border-radius: 7px; padding: 5px 10px;">{c}</span>'
        for c in ['Hook ×3', 'CTA ×1'])
    chips_f = ''.join(
        f'<span style="font-size: 11.5px; font-weight: 500; color: {T3}; background: {BG3}; '
        f'border: 1px solid {LINHA}; border-radius: 7px; padding: 5px 10px;">{c}</span>'
        for c in ['Story', 'Prova'])
    corpo = f"""        <div style="display: flex; flex-direction: column; gap: 10px;">
          <div style="display: flex; flex-direction: column; gap: 6px;">
            <span style="font-size: 11px; color: {T4};">Remixam entre si</span>
            <div style="display: flex; flex-wrap: wrap; gap: 6px;">{chips_v}</div>
          </div>
          <div style="display: flex; flex-direction: column; gap: 6px;">
            <span style="font-size: 11px; color: {T4};">Ficam iguais</span>
            <div style="display: flex; flex-wrap: wrap; gap: 6px;">{chips_f}</div>
          </div>
        </div>
        <div style="{PLACA} border-radius: 10px; padding: 13px; display: flex; align-items: flex-end; gap: 10px;">
          <span style="font-size: 34px; font-weight: 700; letter-spacing: -0.035em; line-height: 1; color: {AM};">3</span>
          <span style="font-size: 11.5px; line-height: 1.4; color: {T3}; padding-bottom: 3px;">combinações<br>de takes</span>
        </div>
        <div style="font-size: 11px; line-height: 1.55; color: {T4};">Esgotadas as combinações, ele aplica micro-cortes e zoom para continuar gerando arquivos únicos.</div>"""
    return bloco_esq('Estrutura detectada', corpo, cresce=True)


# ══════════════════════════════════════════════════════ área principal (meio) ══
def palco(titulo, sub, blocos, largura=700):
    """Uma coluna de leitura só, centrada: arquivos → variações → gerar."""
    return f"""      <div style="flex: 1; min-height: 0; overflow-y: auto; display: flex; justify-content: center; padding: 30px 24px;">
        <div style="width: {largura}px; display: flex; flex-direction: column; gap: 18px;">
          <div style="display: flex; flex-direction: column; gap: 5px;">
            <h1 style="margin: 0; font-size: 26px; font-weight: 700; letter-spacing: -0.03em; color: {T};">{titulo}</h1>
            <span style="font-size: 13.5px; line-height: 1.55; color: {T3};">{sub}</span>
          </div>
{blocos}
        </div>
      </div>"""


def balao(principal, sub, chip, alto=250):
    return f"""          <div style="border: 1px dashed {LINHA}; border-radius: 14px; min-height: {alto}px; background: linear-gradient(180deg, {BG2} 0%, rgba(11, 14, 18, 0) 100%); display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 12px;">
            <div style="width: 54px; height: 54px; border-radius: 15px; background: {BG3}; border: 1px solid {LINHA}; display: flex; align-items: center; justify-content: center;">
              <svg width="23" height="23" viewBox="0 0 24 24" fill="none" stroke="{AM}" stroke-width="1.6" stroke-linecap="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="17 8 12 3 7 8"></polyline><line x1="12" y1="3" x2="12" y2="15"></line></svg>
            </div>
            <div style="display: flex; flex-direction: column; align-items: center; gap: 3px;">
              <span style="font-size: 16px; font-weight: 600; color: {T};">{principal}</span>
              <span style="font-size: 12.5px; color: {T3};">{sub}</span>
            </div>
            <span style="font-family: ui-monospace, monospace; font-size: 11px; color: {T4}; background: {BG}; border: 1px solid {LINHA}; border-radius: 7px; padding: 5px 11px;">{chip}</span>
          </div>"""


def caixa_arquivos():
    return f"""          <div style="{CARTAO} padding: 18px; display: flex; flex-direction: column; gap: 13px;">
            <div style="display: flex; align-items: center; justify-content: space-between;">
              <span style="{ROTULO}">6 arquivos · estrutura reconhecida</span>
              <button style="{BTN_FANT}">✕ trocar takes</button>
            </div>
{arquivos()}
          </div>"""


def variacoes_meio(dim=False):
    op = ' opacity: .4;' if dim else ''
    p = ''
    for n in (5, 10, 15, 20, 25, 30):
        if n == 15 and not dim:
            p += (f'<div style="height: 46px; background: linear-gradient(180deg, {AM} 0%, {AM2} 100%); '
                  f'border-radius: 9px; display: flex; align-items: center; justify-content: center; '
                  f'font-size: 15px; font-weight: 700; color: #101318;">15</div>')
        else:
            p += (f'<div style="height: 46px; background: {BG3}; border: 1px solid {LINHA}; border-radius: 9px; '
                  f'display: flex; align-items: center; justify-content: center; font-size: 15px; '
                  f'font-weight: 600; color: {T4};">{n}</div>')
    nota = ('escolha depois de subir os arquivos' if dim
            else '1 crédito por vídeo entregue — cobrado só na entrega')
    return f"""          <div style="{CARTAO} padding: 18px; display: flex; flex-direction: column; gap: 12px;">
            <div style="display: flex; align-items: center; justify-content: space-between; gap: 10px;">
              <span style="{ROTULO}">Quantas variações</span>
              <span style="font-size: 11px; color: {T4};">{nota}</span>
            </div>
            <div style="display: grid; grid-template-columns: repeat(6, minmax(0, 1fr)); gap: 7px;{op}">{p}</div>
          </div>"""


def gerar(ativo=True, rotulo='Gerar variações', dur='', aviso=''):
    if ativo:
        botao = f'<button style="{BTN_AM} flex: 1; height: 54px; font-size: 15.5px;">{PLAY}{rotulo}</button>'
    else:
        botao = (f'<button style="font-family: inherit; flex: 1; height: 54px; font-size: 15.5px; '
                 f'font-weight: 600; color: {T5}; background: {BG3}; border: 1px solid {LINHA}; '
                 f'border-radius: 9px; display: flex; align-items: center; justify-content: center; gap: 9px;">{PLAY}{rotulo}</button>')
    linha = ('' if not dur else
             f'<div style="font-size: 12px; line-height: 1.5; color: #6FD08C; text-align: center;">{dur}</div>')
    return f"""{aviso}
          <div style="display: flex; gap: 9px;">
            {botao}
            <button style="font-family: inherit; width: 54px; height: 54px; color: {T4}; background: transparent; border: 1px solid {LINHA}; border-radius: 9px; display: flex; align-items: center; justify-content: center; cursor: pointer;">
              <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"></path></svg>
            </button>
          </div>
{linha}"""


# ═══════════════════════════════════════════════════════════════ 02 · INÍCIO ══
def modo(titulo, desc, itens, icone, primario):
    lista = ''.join(
        f'<div style="display: flex; align-items: flex-start; gap: 9px;">'
        f'<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="{AM}" stroke-width="2.4" '
        f'style="flex-shrink: 0; margin-top: 3px;"><polyline points="20 6 9 17 4 12"></polyline></svg>'
        f'<span style="font-size: 12.5px; line-height: 1.5; color: {T3};">{i}</span></div>' for i in itens)
    if primario:
        botao = f'<button style="{BTN_AM} width: 100%; height: 46px; font-size: 14px;">Começar{SETA}</button>'
        quadro, stroke = f'background: {AM};', '#101318'
    else:
        botao = f'<button style="{BTN_LIN} width: 100%; height: 46px; display: flex; align-items: center; justify-content: center; gap: 9px;">Começar{SETA}</button>'
        quadro, stroke = f'background: {BG3}; border: 1px solid {LINHA};', T2
    return f"""          <div style="{CARTAO} padding: 22px; display: flex; flex-direction: column; gap: 15px;">
            <div style="width: 44px; height: 44px; border-radius: 13px; {quadro} display: flex; align-items: center; justify-content: center;">
              <svg width="21" height="21" viewBox="0 0 24 24" fill="none" stroke="{stroke}" stroke-width="1.8">{icone}</svg>
            </div>
            <div style="display: flex; flex-direction: column; gap: 5px;">
              <span style="font-size: 18px; font-weight: 600; letter-spacing: -0.022em; color: {T};">{titulo}</span>
              <span style="font-size: 12.5px; line-height: 1.55; color: {T3};">{desc}</span>
            </div>
            <div style="display: flex; flex-direction: column; gap: 8px; flex-grow: 1;">{lista}</div>
            {botao}
          </div>"""


ICO_REMIX = ('<rect x="3" y="3" width="7" height="7" rx="1.5"></rect><rect x="14" y="3" width="7" height="7" rx="1.5"></rect>'
             '<rect x="3" y="14" width="7" height="7" rx="1.5"></rect><rect x="14" y="14" width="7" height="7" rx="1.5"></rect>')
ICO_UNICO = '<polygon points="23 7 16 12 23 17 23 7"></polygon><rect x="1" y="5" width="15" height="14" rx="2"></rect>'

geracoes = ''.join(
    f'<div style="display: flex; align-items: center; gap: 11px; {ELEV} padding: 10px 12px;">'
    f'<div style="display: flex; flex-direction: column; gap: 2px; flex-grow: 1;">'
    f'<span style="font-size: 12px; font-weight: 500; color: {T2};">{t}</span>'
    f'<span style="font-family: ui-monospace, monospace; font-size: 10px; color: {T5};">{s}</span></div>'
    f'<span style="font-family: ui-monospace, monospace; font-size: 9.5px; color: {c}; background: {BG}; '
    f'border: 1px solid {LINHA}; border-radius: 5px; padding: 4px 7px;">{tag}</span></div>'
    for t, s, tag, c in [('Remix · 15 vídeos', 'id_7c19b4 · ontem 18:22', 'EXPIRA 6h', AM),
                         ('Vídeo único · 10 vídeos', 'id_5a02de · 11/09 09:41', 'EXPIRADO', T5),
                         ('Remix · 30 vídeos', 'id_2b77f0 · 10/09 15:08', 'EXPIRADO', T5)])

inicio_esq = (abas('remix') + '\n' + guia_nomes() + '\n'
              + bloco_esq('Últimas gerações',
                          f'        <div style="display: flex; flex-direction: column; gap: 8px;">{geracoes}</div>',
                          cresce=True))
inicio_meio = f"""      <div style="flex: 1; min-height: 0; overflow-y: auto; display: flex; justify-content: center; padding: 30px 24px;">
        <div style="width: 760px; display: flex; flex-direction: column; gap: 20px;">
          <div style="{PLACA} border-radius: 14px; padding: 22px 22px 28px; display: flex; flex-direction: column; gap: 6px;">
            <h1 style="margin: 0; font-size: 30px; font-weight: 700; letter-spacing: -0.032em; color: {T};">Bom te ver, Vinícius.</h1>
            <span style="font-size: 14px; color: {T3};">Grave uma vez hoje. Poste a semana inteira.</span>
          </div>
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px;">
{modo('Remix de takes', 'Grave os blocos separados e o varvid monta o vídeo, girando hooks e CTAs.', ['Hook, Story, Revelação, Prova e CTA', 'Cada arquivo com assinatura própria'], ICO_REMIX, True)}
{modo('Vídeo único', 'Já tem o vídeo pronto? Ele devolve dezenas de cópias, cada uma lida como um arquivo diferente.', ['Micro-cortes e reenquadramento sutil', 'mp4 ou mov, até 1min30'], ICO_UNICO, False)}
          </div>
        </div>
      </div>"""
tela('NoiteInicio.dc.html', inicio_esq, inicio_meio)


# ═══════════════════════════════════════════ 03 · REMIX ANTES DOS ARQUIVOS ══
esq3 = (abas('remix') + '\n' + guia_nomes() + '\n'
        + headline_esq(dim=True, texto='Texto do headline… (vazio = sem texto)') + '\n'
        + estrutura_esq(vazio=True))
meio3 = palco('Solte seus takes aqui',
              'Em minutos eles viram dezenas de vídeos prontos para postar.',
              balao('Arraste seus takes', 'ou clique para escolher vários de uma vez',
                    'mp4 · mov · até 1min30 cada') + '\n'
              + variacoes_meio(dim=True) + '\n' + gerar(False))
tela('NoiteRemixVazio.dc.html', esq3, meio3)


# ═══════════════════════════════════════════════ 04 · REMIX COM OS TAKES ══
esq4 = (abas('remix') + '\n' + guia_nomes() + '\n' + headline_esq() + '\n' + estrutura_esq())
meio4 = palco('Tudo pronto.',
              'Três hooks e um CTA girando em cima da mesma história.',
              caixa_arquivos() + '\n' + variacoes_meio() + '\n'
              + gerar(True, dur='Seu vídeo vai ter até 52s · dentro do limite de 1min30'))
tela('NoiteRemixCheio.dc.html', esq4, meio4)


# ═════════════════════════════════════════════════════════ 05 · VÍDEO ÚNICO ══
guia_unico = f"""      <div style="padding: 16px; border-bottom: 1px solid {LIN2}; background: linear-gradient(180deg, rgba(255, 199, 0, 0.07) 0%, rgba(11, 14, 18, 0) 78%); display: flex; flex-direction: column; gap: 12px;">
        <div style="display: flex; align-items: center; gap: 11px;">
          <span style="width: 28px; height: 28px; border-radius: 9px; background: {AM}; display: flex; align-items: center; justify-content: center; flex-shrink: 0;">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#101318" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><path d="M12 16v-4M12 8h.01"></path></svg>
          </span>
          <div style="display: flex; flex-direction: column; gap: 1px;">
            <span style="font-size: 13px; font-weight: 600; color: {T};">Um vídeo vira muitos</span>
            <span style="font-size: 11px; color: {AM}; opacity: .8;">sem você abrir editor</span>
          </div>
        </div>
        <div style="font-size: 12px; line-height: 1.6; color: {T3};">Cada cópia sai com cortes de quadros, enquadramento e assinatura digital diferentes. As plataformas leem como vídeos distintos — você posta mais sem gravar mais.</div>
      </div>"""
esq5 = (abas('unico') + '\n' + guia_unico + '\n'
        + headline_esq(dim=True, texto='Texto do headline… (vazio = sem texto)') + '\n'
        + qual_modo())
meio5 = palco('Solte seu vídeo aqui',
              'Um arquivo entra. Dezenas de versões únicas saem.',
              balao('Arraste seu vídeo', 'ou clique para escolher', 'mp4 · mov · até 1min30') + '\n'
              + variacoes_meio(dim=True) + '\n' + gerar(False))
tela('NoiteUnico.dc.html', esq5, meio5)


# ═════════════════════════════════════════════════════════════ 06 · GERANDO ══
def _etapas():
    linhas = ''.join(
        f'<div style="display: flex; align-items: center; gap: 10px;">'
        f'<span style="width: 16px; height: 16px; border-radius: 50%; {m} flex-shrink: 0;"></span>'
        f'<span style="font-size: 12.5px; color: {c};">{t}</span></div>'
        for t, m, c in [
            ('Arquivos recebidos', f'background: {AM};', T2),
            ('Combinações montadas', f'background: {AM};', T2),
            ('Renderizando as variações', f'border: 2px solid {AM};', T),
            ('Enviando para o armazenamento', f'border: 2px solid {LINHA};', T5)])
    return '        <div style="display: flex; flex-direction: column; gap: 10px;">' + linhas + '</div>'


barras = ''.join(f'<span style="flex-grow: 1; height: 20px; border-radius: 2px; background: {c};"></span>'
                 for c in [AM] * 9 + [BG3] * 6)

esq6 = (abas('remix') + '\n'
        + bloco_esq('Em andamento', f"""        <div style="display: flex; align-items: baseline; justify-content: space-between; gap: 10px;">
          <div style="display: flex; align-items: baseline; gap: 8px;">
            <span style="font-size: 32px; font-weight: 700; letter-spacing: -0.032em; line-height: 1; color: {AM};">9</span>
            <span style="font-size: 12.5px; color: {T3};">de 15 prontos</span>
          </div>
          <span style="font-family: ui-monospace, monospace; font-size: 10px; color: {AM};">RENDERIZANDO</span>
        </div>
        <div style="display: flex; gap: 3px;">{barras}</div>
        <span style="font-family: ui-monospace, monospace; font-size: 10.5px; color: {T5};">id_8f3a21 · iniciado 12:04</span>""",
                    placa=True) + '\n'
        + bloco_esq('O que está acontecendo', _etapas()) + '\n'
        + bloco_esq('Estrutura', f'        <div style="font-size: 11.5px; line-height: 1.6; color: {T4};">Três hooks e um CTA girando sobre a mesma história. O crédito é debitado no fim, só pelo que for entregue.</div>',
                    cresce=True))

# A grade é a mesma de "Resultados": as prontas acendem, as pendentes seguem
# apagadas no mesmo lugar. Gerando e concluído passam a ser a mesma tela em
# dois momentos, não duas telas diferentes.
grade6 = ''
for i in range(1, 16):
    if i <= 9:
        grade6 += (f'<div style="display: flex; flex-direction: column; gap: 6px;">'
                   f'<div style="aspect-ratio: 9 / 16; border-radius: 10px; background: {BG3}; '
                   f'border: 1px solid {LINHA}; position: relative; display: flex; align-items: flex-end; '
                   f'justify-content: center; padding-bottom: 9px;">'
                   f'<span style="position: absolute; top: 8px; left: 8px; width: 16px; height: 16px; '
                   f'border-radius: 50%; background: {AM}; display: flex; align-items: center; justify-content: center;">'
                   f'<svg width="9" height="9" viewBox="0 0 24 24" fill="none" stroke="#101318" stroke-width="3.6">'
                   f'<polyline points="20 6 9 17 4 12"></polyline></svg></span>'
                   f'<span style="font-family: ui-monospace, monospace; font-size: 9px; color: {T3}; '
                   f'background: rgba(11,14,18,.75); border-radius: 4px; padding: 2px 6px;">0:37</span></div>'
                   f'<div style="display: flex; align-items: center; justify-content: space-between; gap: 5px;">'
                   f'<span style="font-family: ui-monospace, monospace; font-size: 10.5px; color: {T3};">v{i:02d}</span>'
                   f'<span style="width: 20px; height: 20px; border-radius: 6px; border: 1px solid {LINHA}; '
                   f'color: {T3}; display: flex; align-items: center; justify-content: center;">{BAIXAR}</span></div></div>')
    else:
        grade6 += (f'<div style="display: flex; flex-direction: column; gap: 6px; opacity: .45;">'
                   f'<div style="aspect-ratio: 9 / 16; border-radius: 10px; background: {BG2}; '
                   f'border: 1px dashed {LINHA};"></div>'
                   f'<span style="font-family: ui-monospace, monospace; font-size: 10.5px; color: {T5};">v{i:02d}</span></div>')

meio6 = f"""      <div style="flex: 1; min-height: 0; overflow-y: auto; display: flex; justify-content: center; padding: 30px 24px;">
        <div style="width: 820px; display: flex; flex-direction: column; gap: 18px;">
          <div style="{PLACA} border-radius: 14px; padding: 20px 20px 24px; display: flex; flex-direction: column; gap: 14px;">
            <div style="display: flex; align-items: flex-end; justify-content: space-between; gap: 20px;">
              <div style="display: flex; flex-direction: column; gap: 4px;">
                <h1 style="margin: 0; font-size: 26px; font-weight: 700; letter-spacing: -0.03em; color: {T};">Renderizando seus vídeos</h1>
                <span style="font-size: 13px; color: {T3};">Os prontos já podem ser baixados — não precisa esperar o resto.</span>
              </div>
              <div style="display: flex; align-items: baseline; gap: 7px; flex-shrink: 0;">
                <span style="font-size: 26px; font-weight: 700; letter-spacing: -0.03em; color: {AM};">9</span>
                <span style="font-size: 13px; color: {T3};">de 15</span>
              </div>
            </div>
            <div style="height: 6px; border-radius: 3px; background: {BG3}; overflow: hidden;">
              <div style="width: 60%; height: 100%; background: linear-gradient(90deg, {AM} 0%, {AM2} 100%);"></div>
            </div>
          </div>

          <div style="{CARTAO} padding: 18px; display: flex; flex-direction: column; gap: 14px;">
            <div style="display: flex; align-items: center; justify-content: space-between; gap: 12px;">
              <span style="{ROTULO}">Os arquivos</span>
              <button style="{BTN_AM} height: 38px; padding: 0 18px; font-size: 12.5px;">{BAIXAR}Baixar os 9 prontos</button>
            </div>
            <div style="display: grid; grid-template-columns: repeat(8, minmax(0, 1fr)); gap: 10px;">{grade6}</div>
          </div>

          <div style="display: flex; justify-content: center;">
            <button style="{BTN_LIN}">Cancelar a geração</button>
          </div>
        </div>
      </div>"""
tela('NoiteGerando.dc.html', esq6, meio6)


# ══════════════════════════════════════════════════════════ 07 · RESULTADOS ══
grade7 = ''.join(
    f'<div style="display: flex; flex-direction: column; gap: 6px;">'
    f'<div style="aspect-ratio: 9 / 16; border-radius: 10px; background: {BG3}; border: 1px solid {LINHA}; '
    f'display: flex; align-items: flex-end; justify-content: center; padding-bottom: 9px;">'
    f'<span style="font-family: ui-monospace, monospace; font-size: 9px; color: {T3}; '
    f'background: rgba(11,14,18,.75); border-radius: 4px; padding: 2px 6px;">0:37</span></div>'
    f'<div style="display: flex; align-items: center; justify-content: space-between; gap: 5px;">'
    f'<span style="font-family: ui-monospace, monospace; font-size: 10.5px; color: {T3};">v{i:02d}</span>'
    f'<span style="width: 20px; height: 20px; border-radius: 6px; border: 1px solid {LINHA}; color: {T3}; '
    f'display: flex; align-items: center; justify-content: center;">{BAIXAR}</span></div></div>'
    for i in range(1, 16))

esq7 = (abas('remix') + '\n' + guia_nomes() + '\n' + headline_esq() + '\n' + estrutura_esq())
meio7 = f"""      <div style="flex: 1; min-height: 0; overflow-y: auto; display: flex; justify-content: center; padding: 30px 24px;">
        <div style="width: 820px; display: flex; flex-direction: column; gap: 18px;">
          <div style="{PLACA} border-radius: 14px; padding: 20px 20px 26px; display: flex; align-items: center; justify-content: space-between; gap: 20px;">
            <div style="display: flex; align-items: center; gap: 14px;">
              <span style="width: 36px; height: 36px; border-radius: 11px; background: {AM}; display: flex; align-items: center; justify-content: center; flex-shrink: 0;">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#101318" stroke-width="2.6"><polyline points="20 6 9 17 4 12"></polyline></svg>
              </span>
              <div style="display: flex; flex-direction: column; gap: 3px;">
                <h1 style="margin: 0; font-size: 24px; font-weight: 700; letter-spacing: -0.03em; color: {T};">15 vídeos prontos</h1>
                <span style="font-family: ui-monospace, monospace; font-size: 11px; color: {T4};">id_8f3a21 · 15 créditos cobrados · expira em 47h</span>
              </div>
            </div>
            <button style="{BTN_AM} height: 46px; padding: 0 24px; font-size: 14px;">{BAIXAR}Baixar todos</button>
          </div>

          <div style="{CARTAO} padding: 18px; display: flex; flex-direction: column; gap: 14px;">
            <div style="display: flex; align-items: center; justify-content: space-between;">
              <span style="{ROTULO}">Os arquivos</span>
              <span style="font-family: ui-monospace, monospace; font-size: 10.5px; color: {T5};">1080×1920 · mp4</span>
            </div>
            <div style="display: grid; grid-template-columns: repeat(8, minmax(0, 1fr)); gap: 10px;">{grade7}</div>
            <div style="font-size: 11.5px; line-height: 1.55; color: {T4}; border-top: 1px solid {LIN2}; padding-top: 12px;">Depois de <span style="color: {T2};">48 horas</span> os arquivos são apagados. O registro da geração continua na sua conta.</div>
          </div>

          <div style="display: flex; justify-content: center;">
            <button style="{BTN_AM} height: 46px; padding: 0 24px; font-size: 14px;">{PLAY}Nova geração</button>
          </div>
        </div>
      </div>"""
tela('NoiteResultados.dc.html', esq7, meio7)


# ═══════════════════════════════════════════════════ 08 · CRÉDITOS ESGOTADOS ══
aviso = f"""          <div style="position: relative; overflow: hidden; border: 1px solid {AMBOR}; border-radius: 13px; padding: 18px 20px; display: flex; align-items: center; justify-content: space-between; gap: 22px; background: linear-gradient(140deg, rgba(255, 199, 0, 0.15) 0%, rgba(11, 14, 18, 0) 74%);">
            <div style="display: flex; align-items: center; gap: 14px;">
              <span style="width: 34px; height: 34px; border-radius: 10px; background: {AM}; display: flex; align-items: center; justify-content: center; flex-shrink: 0;">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="#101318"><polygon points="13 2 3 14 11 14 10 22 21 10 13 10 13 2"></polygon></svg>
              </span>
              <div style="display: flex; flex-direction: column; gap: 3px;">
                <span style="font-size: 14.5px; font-weight: 600; color: {AM};">Seus créditos acabaram.</span>
                <span style="font-size: 12.5px; line-height: 1.55; color: {T3};">Assine para continuar agora, ou espere até <span style="color: {T};">14/10</span> — a cota reinicia sozinha.</span>
              </div>
            </div>
            <button style="{BTN_AM} height: 46px; padding: 0 22px; font-size: 13.5px; flex-shrink: 0;">Obter mais créditos</button>
          </div>"""
esq8 = (abas('remix') + '\n' + guia_nomes() + '\n' + headline_esq() + '\n'
        + bloco_esq('Planos', ''.join(
            f'<div style="display: flex; align-items: center; justify-content: space-between; gap: 10px; '
            f'{d} border-radius: 10px; padding: 11px 12px;">'
            f'<div style="display: flex; flex-direction: column; gap: 1px;">'
            f'<span style="font-size: 12.5px; font-weight: {pe}; color: {co};">{n}</span>'
            f'<span style="font-size: 10.5px; color: {T4};">{v} vídeos por mês</span></div>'
            f'<span style="font-size: {ta}; font-weight: 700; letter-spacing: -0.02em; color: {co};">{p}</span></div>'
            for n, v, p, d, co, pe, ta in [
                ('Starter', '50', 'R$ 39', f'border: 1px solid {LINHA};', T2, '500', '13px'),
                ('Pro', '150', 'R$ 69', f'border: 1px solid {AMBOR}; background: {AMSUA};', AM, '600', '16px'),
                ('Studio', '400', 'R$ 117', f'border: 1px solid {LINHA};', T2, '500', '13px')]).join(
            ['        <div style="display: flex; flex-direction: column; gap: 8px;">', '</div>']),
            cresce=True))
meio8 = palco('Tudo pronto. Só falta crédito.',
              'Seus takes estão aqui esperando — assine e gere em seguida.',
              caixa_arquivos() + '\n' + variacoes_meio() + '\n'
              + gerar(False, aviso=aviso))
tela('NoiteSemCreditos.dc.html', esq8, meio8, creditos='0', baixo=True)
