from gerar_console import (HEAD, FOOT, MARK, tela, abas, cabecalho, ROTULO, CARTAO)

SETA = ('<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="2"><line x1="5" y1="12" x2="19" y2="12"></line>'
        '<polyline points="12 5 19 12 12 19"></polyline></svg>')
PLAY = '<svg width="15" height="15" viewBox="0 0 24 24" fill="currentColor"><polygon points="6 4 20 12 6 20 6 4"></polygon></svg>'
BAIXAR = ('<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
          'stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>'
          '<polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>')
CHECK = ('<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#101318" '
         'stroke-width="2.4"><polyline points="20 6 9 17 4 12"></polyline></svg>')

BTN_AMARELO = ('font-family: inherit; font-size: 14px; font-weight: 600; color: #101318; '
               'background: #FFC700; border: none; border-radius: 9px; padding: 13px 24px; '
               'display: flex; align-items: center; gap: 9px; cursor: pointer;')
BTN_PRETO = ('font-family: inherit; font-size: 13.5px; font-weight: 500; color: #FFFFFF; '
             'background: #101318; border: none; border-radius: 9px; padding: 11px 18px; '
             'display: flex; align-items: center; gap: 8px; cursor: pointer;')
BTN_LINHA = ('font-family: inherit; font-size: 13.5px; font-weight: 500; color: #101318; '
             'background: #FFFFFF; border: 1px solid #D5DAE1; border-radius: 9px; '
             'padding: 11px 18px; display: flex; align-items: center; gap: 8px; cursor: pointer;')


def area(conteudo, direita=None):
    """Área de conteúdo: uma coluna larga e, opcionalmente, a coluna de estado."""
    if direita is None:
        return ('    <div style="flex: 1; padding: 24px; display: flex; flex-direction: column; '
                'gap: 16px; min-height: 0; overflow: hidden;">\n' + conteudo + '\n    </div>\n')
    return ('    <div style="flex: 1; padding: 24px; display: grid; grid-template-columns: 1fr 328px; '
            'gap: 20px; min-height: 0; overflow: hidden;">\n'
            '      <div style="display: flex; flex-direction: column; gap: 16px; min-height: 0;">\n'
            + conteudo + '\n      </div>\n'
            '      <div style="display: flex; flex-direction: column; gap: 16px; min-height: 0;">\n'
            + direita + '\n      </div>\n    </div>\n')


def entradas(dim=False):
    op = ' opacity: 0.55;' if dim else ''
    arquivos = [('Hook1.mp4', 'bloco Hook · 4s'), ('Hook2.mp4', 'bloco Hook · 5s'),
                ('Hook3.mp4', 'bloco Hook · 4s'), ('Story.mp4', 'bloco fixo · 18s'),
                ('Prova.mp4', 'bloco fixo · 9s')]
    itens = ''.join(
        '<div style="border: 1px solid #EBEEF1; border-radius: 9px; padding: 10px 12px; '
        'display: flex; flex-direction: column; gap: 3px;">'
        f'<span style="font-family: ui-monospace, monospace; font-size: 12px;">{n}</span>'
        f'<span style="font-size: 10.5px; color: #8A93A0;">{d}</span></div>' for n, d in arquivos)
    if not dim:
        itens += ('<div style="border: 1px dashed #C3C9D1; border-radius: 9px; padding: 10px 12px; '
                  'display: flex; align-items: center; justify-content: center; gap: 7px; color: #8A93A0;">'
                  '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
                  'stroke-width="1.9"><line x1="12" y1="5" x2="12" y2="19"></line>'
                  '<line x1="5" y1="12" x2="19" y2="12"></line></svg>'
                  '<span style="font-size: 12px;">adicionar</span></div>')
    else:
        itens += ('<div style="border: 1px solid #EBEEF1; border-radius: 9px; padding: 10px 12px; '
                  'display: flex; flex-direction: column; gap: 3px;">'
                  '<span style="font-family: ui-monospace, monospace; font-size: 12px;">CTA1.mp4</span>'
                  '<span style="font-size: 10.5px; color: #8A93A0;">bloco CTA · 6s</span></div>')
    troca = ('' if dim else '<a style="font-size: 12.5px; font-weight: 500; text-decoration: none;">trocar</a>')
    return f"""        <div style="{CARTAO} padding: 18px; display: flex; flex-direction: column; gap: 14px;{op}">
          <div style="display: flex; align-items: center; justify-content: space-between;">
            <span style="{ROTULO}">Entradas · 6 arquivos</span>
            {troca}
          </div>
          <div style="display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 8px;">{itens}</div>
        </div>"""


def variacoes(dim=False):
    op = ' opacity: 0.55;' if dim else ''
    pills = ''
    for n in (5, 10, 15, 20, 25, 30):
        if n == 15:
            pills += ('<div style="height: 38px; background: #101318; border-radius: 8px; display: flex; '
                      'align-items: center; justify-content: center; font-size: 13px; font-weight: 700; '
                      'color: #FFC700;">15</div>')
        else:
            pills += ('<div style="height: 38px; border: 1px solid #E3E6EA; border-radius: 8px; '
                      'display: flex; align-items: center; justify-content: center; font-size: 13px; '
                      f'font-weight: 600; color: #8A93A0;">{n}</div>')
    return f"""          <div style="{CARTAO} padding: 18px; display: flex; flex-direction: column; gap: 12px;{op}">
            <span style="{ROTULO}">Variações</span>
            <div style="display: grid; grid-template-columns: repeat(6, minmax(0, 1fr)); gap: 5px;">{pills}</div>
            <div style="display: flex; align-items: baseline; gap: 7px; border-top: 1px solid #EBEEF1; padding-top: 11px;">
              <span style="font-size: 17px; font-weight: 700;">3</span>
              <span style="font-size: 12px; color: #5B6470;">combinações reais · o resto sai por micro-corte e zoom</span>
            </div>
          </div>"""


def headline(dim=False, texto='Ninguém te contou isso sobre tráfego pago', nota='Estilo diferente em cada variação.'):
    op = ' opacity: 0.55;' if dim else ''
    return f"""          <div style="{CARTAO} padding: 18px; display: flex; flex-direction: column; gap: 12px;{op}">
            <div style="display: flex; align-items: center; justify-content: space-between;">
              <span style="{ROTULO}">Headline</span>
              <span style="font-size: 11px; color: #A3ABB6;">opcional</span>
            </div>
            <div style="display: flex; gap: 8px;">
              <div style="flex-grow: 1; border: 1px solid #E3E6EA; border-radius: 8px; padding: 10px 12px; font-size: 13px; line-height: 1.45; min-height: 58px;">{texto}</div>
              <div style="width: 70px; border: 1px solid #E3E6EA; border-radius: 8px; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 1px;">
                <span style="font-size: 20px; font-weight: 700;">3</span>
                <span style="font-size: 10px; color: #8A93A0;">seg</span>
              </div>
            </div>
            <div style="font-size: 12px; color: #5B6470; border-top: 1px solid #EBEEF1; padding-top: 11px;">{nota}</div>
          </div>"""


def barra_gerar(ativo=True):
    if ativo:
        botao = f'<button style="{BTN_AMARELO} padding: 14px 28px;">{PLAY}Gerar variações</button>'
    else:
        botao = ('<button style="font-family: inherit; font-size: 14px; font-weight: 600; '
                 'color: #A3ABB6; background: #E9EDF2; border: none; border-radius: 9px; '
                 f'padding: 14px 28px; display: flex; align-items: center; gap: 9px;">{PLAY}Gerar variações</button>')
    return f"""        <div style="{CARTAO} padding: 16px 18px; display: flex; align-items: center; justify-content: space-between; gap: 20px; margin-top: auto;">
          <div style="display: flex; gap: 26px;">
            <div style="display: flex; flex-direction: column; gap: 1px;"><span style="font-size: 19px; font-weight: 700; letter-spacing: -0.022em;">15</span><span style="font-size: 11.5px; color: #5B6470;">vídeos</span></div>
            <div style="display: flex; flex-direction: column; gap: 1px;"><span style="font-size: 19px; font-weight: 700; letter-spacing: -0.022em;">15</span><span style="font-size: 11.5px; color: #5B6470;">créditos</span></div>
          </div>
          {botao}
        </div>"""


def ultimas_geracoes(vazio=False, altura=True):
    if vazio:
        corpo = ('<div style="border: 1px dashed #D5DAE1; border-radius: 10px; padding: 26px 16px; '
                 'display: flex; flex-direction: column; align-items: center; gap: 6px; text-align: center;">'
                 '<span style="font-size: 13px; font-weight: 500;">Nenhuma geração ainda</span>'
                 '<span style="font-size: 11.5px; color: #8A93A0; line-height: 1.5;">O primeiro aparece aqui '
                 'assim que você gerar.</span></div>')
    else:
        linhas = [('Remix · 15 vídeos', 'id_7c19b4 · ontem 18:22', 'EXPIRA 6h', '#5B6470'),
                  ('Vídeo único · 10 vídeos', 'id_5a02de · 11/09 09:41', 'EXPIRADO', '#8A93A0'),
                  ('Remix · 30 vídeos', 'id_2b77f0 · 10/09 15:08', 'EXPIRADO', '#8A93A0')]
        corpo = ''.join(
            '<div style="display: flex; align-items: center; gap: 11px; border: 1px solid #EBEEF1; '
            'border-radius: 9px; padding: 11px 12px;">'
            '<div style="display: flex; flex-direction: column; gap: 2px; flex-grow: 1;">'
            f'<span style="font-size: 12.5px; font-weight: 500;">{t}</span>'
            f'<span style="font-family: ui-monospace, monospace; font-size: 10.5px; color: #8A93A0;">{s}</span></div>'
            f'<span style="font-family: ui-monospace, monospace; font-size: 10px; background: #E9EDF2; '
            f'color: {c}; border-radius: 5px; padding: 4px 7px;">{tag}</span></div>'
            for t, s, tag, c in linhas)
        corpo = f'<div style="display: flex; flex-direction: column; gap: 9px;">{corpo}</div>'
    cresce = ' flex-grow: 1; min-height: 0;' if altura else ''
    return f"""        <div style="{CARTAO} padding: 18px; display: flex; flex-direction: column; gap: 13px;{cresce}">
          <div style="display: flex; align-items: center; justify-content: space-between;">
            <span style="{ROTULO}">Últimas gerações</span>
            <a style="font-size: 12px; font-weight: 500; text-decoration: none;">ver tudo</a>
          </div>
          {corpo}
          <div style="margin-top: auto; font-size: 11.5px; line-height: 1.5; color: #5B6470; border-top: 1px solid #EBEEF1; padding-top: 12px;">Os arquivos ficam no varvid por <span style="font-weight: 600; color: #101318;">48 horas</span>. A biblioteca guarda o registro da geração mesmo depois disso.</div>
        </div>"""


# ─────────────────────────────────────────────────────────── INÍCIO ──
def modo_card(titulo, desc, itens, icone, primario):
    lista = ''.join(
        '<div style="display: flex; align-items: flex-start; gap: 9px;">'
        f'{CHECK}<span style="font-size: 12.5px; line-height: 1.5; color: #4A525E;">{i}</span></div>'
        for i in itens)
    if primario:
        botao = f'<button style="{BTN_AMARELO} width: 100%; justify-content: center;">Começar{SETA}</button>'
        quadro = 'background: #FFC700;'
    else:
        botao = f'<button style="{BTN_LINHA} width: 100%; justify-content: center; padding: 13px 18px;">Começar{SETA}</button>'
        quadro = 'background: #E9EDF2;'
    return f"""          <div style="{CARTAO} padding: 22px; display: flex; flex-direction: column; gap: 15px;">
            <div style="width: 44px; height: 44px; border-radius: 12px; {quadro} display: flex; align-items: center; justify-content: center;">
              <svg width="21" height="21" viewBox="0 0 24 24" fill="none" stroke="#101318" stroke-width="1.8">{icone}</svg>
            </div>
            <div style="display: flex; flex-direction: column; gap: 5px;">
              <span style="font-size: 18px; font-weight: 700; letter-spacing: -0.025em;">{titulo}</span>
              <span style="font-size: 13px; line-height: 1.55; color: #5B6470;">{desc}</span>
            </div>
            <div style="display: flex; flex-direction: column; gap: 8px; flex-grow: 1;">{lista}</div>
            {botao}
          </div>"""


ICO_REMIX = ('<rect x="3" y="3" width="7" height="7" rx="1.5"></rect><rect x="14" y="3" width="7" height="7" rx="1.5"></rect>'
             '<rect x="3" y="14" width="7" height="7" rx="1.5"></rect><rect x="14" y="14" width="7" height="7" rx="1.5"></rect>')
ICO_UNICO = '<polygon points="23 7 16 12 23 17 23 7"></polygon><rect x="1" y="5" width="15" height="14" rx="2"></rect>'

passos = ''.join(
    '<div style="display: flex; align-items: flex-start; gap: 11px;">'
    f'<span style="font-family: ui-monospace, monospace; font-size: 11px; color: #101318; '
    f'background: #FFC700; border-radius: 5px; padding: 3px 7px; flex-shrink: 0;">{n}</span>'
    f'<span style="font-size: 12.5px; line-height: 1.5; color: #4A525E;">{t}</span></div>'
    for n, t in [('01', 'Suba os arquivos — no Remix, o nome de cada um diz de que bloco ele é.'),
                 ('02', 'Escolha quantas variações quer e, se quiser, um headline por cima.'),
                 ('03', 'Baixe tudo de uma vez. O crédito só é cobrado pelo que for entregue.')])

home = f"""      {cabecalho('Bem-vindo de volta, Vinícius', '',
                     f'<button style="{BTN_LINHA}">Abrir biblioteca{SETA}</button>')}

        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px;">
{modo_card('Remix de takes', 'Você grava os blocos separados e o varvid monta o vídeo, girando hooks e CTAs para gerar combinações diferentes.', ['Hook, Story, Revelação, Prova e CTA', 'Cada arquivo com fingerprint distinto'], ICO_REMIX, True)}
{modo_card('Vídeo único', 'Você já tem o vídeo pronto e quer várias cópias dele, cada uma lida como um arquivo diferente pelas plataformas.', ['Micro-cortes e reenquadramento sutil', 'mp4 ou mov, até 1min30'], ICO_UNICO, False)}
        </div>

        <div style="{CARTAO} padding: 18px; display: flex; flex-direction: column; gap: 13px;">
          <span style="{ROTULO}">Como funciona</span>
          <div style="display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16px;">{passos}</div>
        </div>"""

home_dir = f"""        <div style="{CARTAO} padding: 18px; display: flex; flex-direction: column; gap: 13px;">
          <span style="{ROTULO}">Consumo do mês</span>
          <div style="display: flex; align-items: baseline; gap: 7px;">
            <span style="font-size: 30px; font-weight: 700; letter-spacing: -0.028em; line-height: 1;">516</span>
            <span style="font-size: 13px; color: #5B6470;">de 1.800 vídeos</span>
          </div>
          <div style="display: flex; gap: 3px;">{''.join('<span style="flex-grow: 1; height: 22px; border-radius: 2px; background: %s;"></span>' % ('#FFC700' if i < 4 else '#E9EDF2') for i in range(14))}</div>
          <div style="font-size: 11.5px; color: #5B6470; border-top: 1px solid #EBEEF1; padding-top: 11px; line-height: 1.5;">Setembro até agora. O saldo não zera na virada do mês — ele acumula.</div>
        </div>
{ultimas_geracoes()}"""

tela('ConsoleHome.dc.html', area(home, home_dir), ativo='gerar', crumbs=('Estúdio',))


# ────────────────────────────────────────────── REMIX (tela principal) ──
remix = f"""      {cabecalho('Remix de takes', '', abas('remix'))}

{entradas()}

        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px;">
{variacoes()}
{headline()}
        </div>

{barra_gerar(True)}"""

remix_dir = f"""        <div style="{CARTAO} padding: 18px; display: flex; flex-direction: column; gap: 13px;">
          <span style="{ROTULO}">Estrutura detectada</span>
          <div style="display: flex; flex-direction: column; gap: 10px;">
            <div style="display: flex; flex-direction: column; gap: 7px;">
              <span style="font-size: 12px; font-weight: 500; color: #5B6470;">Remixam entre si</span>
              <div style="display: flex; flex-wrap: wrap; gap: 6px;">
                <span style="font-size: 12px; font-weight: 500; background: #FFF6D4; border: 1px solid #F0DC93; border-radius: 7px; padding: 5px 10px;">Hook ×3</span>
                <span style="font-size: 12px; font-weight: 500; background: #FFF6D4; border: 1px solid #F0DC93; border-radius: 7px; padding: 5px 10px;">CTA ×1</span>
              </div>
            </div>
            <div style="display: flex; flex-direction: column; gap: 7px;">
              <span style="font-size: 12px; font-weight: 500; color: #5B6470;">Ficam iguais</span>
              <div style="display: flex; flex-wrap: wrap; gap: 6px;">
                <span style="font-size: 12px; font-weight: 500; background: #F2F3F5; border: 1px solid #E3E6EA; border-radius: 7px; padding: 5px 10px; color: #5B6470;">Story</span>
                <span style="font-size: 12px; font-weight: 500; background: #F2F3F5; border: 1px solid #E3E6EA; border-radius: 7px; padding: 5px 10px; color: #5B6470;">Prova</span>
              </div>
            </div>
          </div>
          <div style="font-size: 11.5px; line-height: 1.5; color: #5B6470; border-top: 1px solid #EBEEF1; padding-top: 12px;">Nome do arquivo é o que define o bloco. Numere para multiplicar: <span style="font-family: ui-monospace, monospace; color: #101318;">Hook1</span>, <span style="font-family: ui-monospace, monospace; color: #101318;">Hook2</span>.</div>
        </div>
{ultimas_geracoes()}"""

tela('ConsoleRemixCheio.dc.html', area(remix, remix_dir), ativo='gerar', crumbs=('Estúdio', 'Remix de takes'))


# ──────────────────────────────────────────────────────── VÍDEO ÚNICO ──
unico = f"""      {cabecalho('Vídeo único', '', abas('unico'))}

        <div style="{CARTAO} padding: 18px; display: flex; flex-direction: column; gap: 14px;">
          <span style="{ROTULO}">Entrada · um arquivo</span>
          <div style="border: 1px dashed #C3C9D1; background: #F7F8FA; border-radius: 11px; padding: 34px 20px; display: flex; flex-direction: column; align-items: center; gap: 10px;">
            <div style="width: 46px; height: 46px; border-radius: 12px; background: #FFFFFF; border: 1px solid #E3E6EA; display: flex; align-items: center; justify-content: center;">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#101318" stroke-width="1.6" stroke-linecap="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="17 8 12 3 7 8"></polyline><line x1="12" y1="3" x2="12" y2="15"></line></svg>
            </div>
            <div style="display: flex; flex-direction: column; align-items: center; gap: 3px;">
              <span style="font-size: 14px; font-weight: 500;">Arraste seu vídeo aqui</span>
              <span style="font-size: 12.5px; color: #5B6470;">ou clique para escolher</span>
            </div>
            <span style="font-family: ui-monospace, monospace; font-size: 11px; color: #8A93A0; background: #FFFFFF; border: 1px solid #E3E6EA; border-radius: 6px; padding: 5px 10px;">mp4 · mov · até 1min30</span>
          </div>
          <div style="font-size: 12px; color: #5B6470; line-height: 1.5; border-top: 1px solid #EBEEF1; padding-top: 12px;">A duração é conferida no navegador antes de enviar — vídeo mais longo é recusado na hora, sem esperar o upload.</div>
        </div>

        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px;">
{variacoes(dim=True)}
{headline(dim=True, texto='Texto do headline… (vazio = sem texto)', nota='Deixe em branco se o seu vídeo já tem texto.')}
        </div>

{barra_gerar(False)}"""

def ajuste(nome, sub, ligado):
    if ligado:
        tag = ('<span style="font-family: ui-monospace, monospace; font-size: 10px; background: #101318; '
               'color: #FFC700; border-radius: 5px; padding: 4px 7px;">ATIVO</span>')
        borda = 'border: 1px solid #F0DC93; background: #FFFCF0;'
        cor = '#101318'
    else:
        tag = ('<span style="font-family: ui-monospace, monospace; font-size: 10px; background: #E9EDF2; '
               'color: #8A93A0; border-radius: 5px; padding: 4px 7px;">EM BREVE</span>')
        borda = 'border: 1px solid #EBEEF1;'
        cor = '#8A93A0'
    return (f'<div style="{borda} border-radius: 9px; padding: 11px 12px; display: flex; '
            'align-items: center; gap: 10px;">'
            '<div style="display: flex; flex-direction: column; gap: 2px; flex-grow: 1;">'
            f'<span style="font-size: 12.5px; font-weight: 500; color: {cor};">{nome}</span>'
            f'<span style="font-size: 10.5px; color: #8A93A0;">{sub}</span></div>{tag}</div>')

unico_dir = f"""        <div style="{CARTAO} padding: 18px; display: flex; flex-direction: column; gap: 11px;">
          <span style="{ROTULO}">Qual modo usar</span>
          <div style="display: flex; flex-direction: column; gap: 11px;">
            <div style="display: flex; flex-direction: column; gap: 3px; border-left: 3px solid #FFC700; padding-left: 12px;">
              <span style="font-size: 12.5px; font-weight: 500;">Tenho o vídeo pronto</span>
              <span style="font-size: 11.5px; color: #5B6470; line-height: 1.5;">Quero várias versões dele, cada uma lida como arquivo diferente → Vídeo único</span>
            </div>
            <div style="display: flex; flex-direction: column; gap: 3px; border-left: 3px solid #E3E6EA; padding-left: 12px;">
              <span style="font-size: 12.5px; font-weight: 500;">Tenho takes separados</span>
              <span style="font-size: 11.5px; color: #5B6470; line-height: 1.5;">Hook, story, CTA — quero que o varvid monte → Remix de takes</span>
            </div>
          </div>
        </div>
{ultimas_geracoes()}"""

tela('ConsoleUnico.dc.html', area(unico, unico_dir), ativo='gerar', crumbs=('Estúdio', 'Vídeo único'))


# ───────────────────────────────────────────────────────────── GERANDO ──
barras = ''.join('<span style="flex-grow: 1; height: 22px; border-radius: 2px; background: %s;"></span>'
                 % ('#FFC700' if i < 9 else '#EFE3BC') for i in range(15))

def etapa(txt, estado):
    if estado == 'feito':
        marca = ('<span style="width: 18px; height: 18px; border-radius: 50%; background: #FFC700; '
                 'display: flex; align-items: center; justify-content: center; flex-shrink: 0;">'
                 '<svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="#101318" '
                 'stroke-width="3.4"><polyline points="20 6 9 17 4 12"></polyline></svg></span>')
        cor = '#101318'
    elif estado == 'agora':
        marca = ('<span style="width: 18px; height: 18px; border-radius: 50%; border: 2px solid #FFC700; '
                 'display: flex; align-items: center; justify-content: center; flex-shrink: 0;">'
                 '<span style="width: 6px; height: 6px; border-radius: 50%; background: #FFC700;"></span></span>')
        cor = '#101318'
    else:
        marca = ('<span style="width: 18px; height: 18px; border-radius: 50%; border: 2px solid #E3E6EA; '
                 'flex-shrink: 0;"></span>')
        cor = '#8A93A0'
    peso = '600' if estado == 'agora' else '400'
    return ('<div style="display: flex; align-items: center; gap: 10px;">' + marca +
            f'<span style="font-size: 12.5px; font-weight: {peso}; color: {cor};">{txt}</span></div>')

gerando = f"""      {cabecalho('Remix de takes', 'id_8f3a21 · iniciado 12:04', abas('remix'))}

{entradas(dim=True)}

        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px;">
{variacoes(dim=True)}
{headline(dim=True)}
        </div>

        <div style="background: linear-gradient(180deg, #FFFCF0 0%, #FFFFFF 58%); border: 1px solid #F0DC93; border-radius: 12px; padding: 16px 18px; display: flex; align-items: center; justify-content: space-between; gap: 20px; margin-top: auto;">
          <div style="display: flex; align-items: center; gap: 16px;">
            <span style="width: 20px; height: 20px; border-radius: 50%; border: 2.5px solid #F0DC93; border-top-color: #FFC700;"></span>
            <div style="display: flex; flex-direction: column; gap: 2px;">
              <span style="font-size: 13.5px; font-weight: 600;">Renderizando 9 de 15</span>
              <span style="font-size: 11.5px; color: #5B6470;">Os prontos já podem ser baixados enquanto o resto sai.</span>
            </div>
          </div>
          <div style="display: flex; align-items: center; gap: 10px;">
            <button style="font-family: inherit; font-size: 13px; font-weight: 500; color: #101318; background: #FFFFFF; border: 1px solid #D5DAE1; border-radius: 9px; padding: 11px 18px; cursor: pointer;">Cancelar</button>
            <button style="{BTN_AMARELO} padding: 12px 20px;">{BAIXAR}Baixar os 9 prontos</button>
          </div>
        </div>"""

gerando_dir = f"""        <div style="background: linear-gradient(180deg, #FFFCF0 0%, #FFFFFF 52%); border: 1px solid #F0DC93; border-radius: 12px; padding: 18px; display: flex; flex-direction: column; gap: 13px;">
          <div style="display: flex; align-items: center; justify-content: space-between;">
            <span style="{ROTULO}">Em andamento</span>
            <span style="font-family: ui-monospace, monospace; font-size: 10.5px; color: #8A7A45;">RENDERIZANDO</span>
          </div>
          <div style="display: flex; align-items: baseline; gap: 8px;">
            <span style="font-size: 30px; font-weight: 700; letter-spacing: -0.028em; line-height: 1;">9</span>
            <span style="font-size: 13px; color: #5B6470;">de 15 prontos</span>
          </div>
          <div style="display: flex; gap: 3px;">{barras}</div>
          <span style="font-family: ui-monospace, monospace; font-size: 11px; color: #8A93A0;">id_8f3a21 · 12:04</span>
        </div>

        <div style="{CARTAO} padding: 18px; display: flex; flex-direction: column; gap: 13px;">
          <span style="{ROTULO}">O que está acontecendo</span>
          <div style="display: flex; flex-direction: column; gap: 11px;">
            {etapa('Arquivos recebidos', 'feito')}
            {etapa('Combinações montadas', 'feito')}
            {etapa('Renderizando as variações', 'agora')}
            {etapa('Enviando para o armazenamento', 'espera')}
          </div>
          <div style="font-size: 11.5px; line-height: 1.5; color: #5B6470; border-top: 1px solid #EBEEF1; padding-top: 12px;">O crédito é debitado no fim, só pelos vídeos que forem entregues.</div>
        </div>
{ultimas_geracoes(altura=True)}"""

tela('ConsoleGerando.dc.html', area(gerando, gerando_dir), ativo='gerar',
     crumbs=('Estúdio', 'Remix de takes', 'id_8f3a21'))


# ────────────────────────────────────────────────────────── RESULTADOS ──
cartoes = ''
for i in range(1, 16):
    cartoes += (
        '<div style="display: flex; flex-direction: column; gap: 7px;">'
        '<div style="aspect-ratio: 9 / 16; border-radius: 9px; background: #E4E8ED; border: 1px solid #DCE1E7; '
        'display: flex; align-items: flex-end; justify-content: center; padding-bottom: 9px;">'
        '<span style="font-family: ui-monospace, monospace; font-size: 9.5px; color: #FFFFFF; '
        'background: rgba(16, 19, 24, 0.6); border-radius: 4px; padding: 2px 6px;">0:37</span></div>'
        '<div style="display: flex; align-items: center; justify-content: space-between; gap: 6px;">'
        f'<span style="font-family: ui-monospace, monospace; font-size: 11px; color: #4A525E;">v{i:02d}</span>'
        '<span style="width: 22px; height: 22px; border-radius: 6px; border: 1px solid #D5DAE1; '
        'display: flex; align-items: center; justify-content: center; color: #5B6470;">'
        f'{BAIXAR}</span></div></div>')

resultados = f"""      {cabecalho('Geração concluída', 'id_8f3a21 · 15 de 15', f'<div style="display: flex; align-items: center; gap: 10px;"><button style="{BTN_PRETO}">{BAIXAR}Baixar todos</button><button style="{BTN_AMARELO} padding: 11px 20px;">{PLAY}Nova geração</button></div>')}

        <div style="{CARTAO} padding: 14px 18px; display: flex; align-items: center; justify-content: space-between; gap: 20px;">
          <div style="display: flex; gap: 30px;">
            <div style="display: flex; flex-direction: column; gap: 1px;"><span style="font-size: 19px; font-weight: 700; letter-spacing: -0.022em;">15</span><span style="font-size: 11.5px; color: #5B6470;">vídeos entregues</span></div>
            <div style="display: flex; flex-direction: column; gap: 1px;"><span style="font-size: 19px; font-weight: 700; letter-spacing: -0.022em;">15</span><span style="font-size: 11.5px; color: #5B6470;">créditos cobrados</span></div>
            <div style="display: flex; flex-direction: column; gap: 1px;"><span style="font-size: 19px; font-weight: 700; letter-spacing: -0.022em;">47h</span><span style="font-size: 11.5px; color: #5B6470;">até serem apagados</span></div>
          </div>
          <div style="display: flex; align-items: center; gap: 9px; background: #F7F8FA; border: 1px solid #EBEEF1; border-radius: 9px; padding: 10px 13px; max-width: 380px;">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#5B6470" stroke-width="1.8" style="flex-shrink: 0;"><circle cx="12" cy="12" r="10"></circle><path d="M12 16v-4M12 8h.01"></path></svg>
            <span style="font-size: 11.5px; line-height: 1.5; color: #4A525E;">Depois de 48 horas os arquivos são apagados. O registro do job continua na biblioteca.</span>
          </div>
        </div>

        <div style="{CARTAO} padding: 18px; display: flex; flex-direction: column; gap: 14px; flex-grow: 1; min-height: 0;">
          <div style="display: flex; align-items: center; justify-content: space-between;">
            <span style="{ROTULO}">15 vídeos prontos</span>
            <div style="display: flex; align-items: center; gap: 14px;">
              <span style="font-family: ui-monospace, monospace; font-size: 11px; color: #8A93A0;">1080×1920 · mp4</span>
              <a style="font-size: 12px; font-weight: 500; text-decoration: none;">abrir na biblioteca</a>
            </div>
          </div>
          <div style="display: grid; grid-template-columns: repeat(8, minmax(0, 1fr)); gap: 12px;">{cartoes}</div>
        </div>"""

tela('ConsoleResultados.dc.html', area(resultados), ativo='gerar',
     crumbs=('Estúdio', 'Remix de takes', 'id_8f3a21'))


# ══════════════════════════════════════════════ REMIX · ESTADO VAZIO (Main) ══
guia_blocos = ''.join(
    '<div style="display: flex; align-items: center; justify-content: space-between; gap: 8px;">'
    f'<div style="display: flex; flex-direction: column; gap: 1px;">'
    f'<span style="font-size: 12.5px; font-weight: 500;">{nome}</span>'
    f'<span style="font-size: 10.5px; color: #8A93A0;">{desc}</span></div>'
    f'<span style="font-family: ui-monospace, monospace; font-size: 11px; color: #4A525E; '
    f'background: #F2F3F5; border: 1px solid #E3E6EA; border-radius: 6px; padding: 4px 8px; '
    f'flex-shrink: 0;">{arq}</span></div>'
    for nome, desc, arq in [
        ('Hook', 'o gancho que prende', 'Hook1.mp4'),
        ('CTA', 'a chamada pra agir', 'CTA1.mp4'),
        ('Story', 'a história / contexto', 'Story.mp4'),
        ('Revelação', 'a virada', 'Revelacao.mp4'),
        ('Prova', 'resultado / prova social', 'Prova.mp4')])

remix_vazio = f"""      {cabecalho('Remix de takes', '', abas('remix'))}

        <div style="{CARTAO} padding: 18px; display: flex; flex-direction: column; gap: 14px;">
          <span style="{ROTULO}">Entradas · seus takes</span>
          <div style="border: 1px dashed #C3C9D1; background: #F7F8FA; border-radius: 11px; padding: 40px 20px; display: flex; flex-direction: column; align-items: center; gap: 11px;">
            <div style="width: 46px; height: 46px; border-radius: 12px; background: #FFFFFF; border: 1px solid #E3E6EA; display: flex; align-items: center; justify-content: center;">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#101318" stroke-width="1.6" stroke-linecap="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="17 8 12 3 7 8"></polyline><line x1="12" y1="3" x2="12" y2="15"></line></svg>
            </div>
            <div style="display: flex; flex-direction: column; align-items: center; gap: 3px;">
              <span style="font-size: 14px; font-weight: 500;">Arraste seus takes aqui</span>
              <span style="font-size: 12.5px; color: #5B6470;">ou clique para escolher vários de uma vez</span>
            </div>
            <span style="font-family: ui-monospace, monospace; font-size: 11px; color: #8A93A0; background: #FFFFFF; border: 1px solid #E3E6EA; border-radius: 6px; padding: 5px 10px;">mp4 · mov · até 1min30 cada</span>
          </div>
          <div style="font-size: 12px; color: #5B6470; line-height: 1.5; border-top: 1px solid #EBEEF1; padding-top: 12px;">O nome de cada arquivo diz de que bloco ele é — a lista ao lado mostra como nomear. Assim que os arquivos entram, o varvid identifica a estrutura sozinho.</div>
        </div>

        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px;">
{variacoes(dim=True)}
{headline(dim=True, texto='Texto do headline… (vazio = sem texto)')}
        </div>

{barra_gerar(False)}"""

remix_vazio_dir = f"""        <div style="background: linear-gradient(180deg, #FFFCF0 0%, #FFFFFF 46%); border: 1px solid #F0DC93; border-radius: 12px; padding: 18px; display: flex; flex-direction: column; gap: 13px;">
          <div style="display: flex; align-items: center; gap: 11px;">
            <span style="width: 28px; height: 28px; border-radius: 9px; background: #FFC700; display: flex; align-items: center; justify-content: center; flex-shrink: 0;"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#101318" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z"></path><line x1="7" y1="7" x2="7.01" y2="7"></line></svg></span>
            <div style="display: flex; flex-direction: column; gap: 1px;">
              <span style="font-size: 13.5px; font-weight: 600;">Como nomear os arquivos</span>
              <span style="font-size: 11.5px; color: #8A7A45;">comece por aqui — é o nome que diz o que é cada take</span>
            </div>
          </div>
          <div style="display: flex; flex-direction: column; gap: 10px;">{guia_blocos}</div>
          <div style="font-size: 11.5px; line-height: 1.55; color: #5B6470; border-top: 1px solid #EBEEF1; padding-top: 12px;">Numere para multiplicar as versões: <span style="font-family: ui-monospace, monospace; color: #101318;">Hook1</span>, <span style="font-family: ui-monospace, monospace; color: #101318;">Hook2</span>. Bloco muito longo quebra em <span style="font-family: ui-monospace, monospace; color: #101318;">_pt1</span>, <span style="font-family: ui-monospace, monospace; color: #101318;">_pt2</span> — ele junta na ordem certa.</div>
        </div>
{ultimas_geracoes()}"""

tela('Main.dc.html', area(remix_vazio, remix_vazio_dir), ativo='gerar',
     crumbs=('Estúdio', 'Remix de takes'))


# ═══════════════════════════════════════════════════════ CRÉDITOS ESGOTADOS ══
aviso = f"""        <div style="position: relative; background: linear-gradient(118deg, #1B222B 0%, #0E1217 62%); border-radius: 12px; padding: 18px 20px; display: flex; align-items: center; justify-content: space-between; gap: 20px; overflow: hidden;">
          <div style="position: absolute; left: -60px; top: -120px; width: 340px; height: 340px; border-radius: 50%; background: radial-gradient(circle, rgba(255, 199, 0, 0.20) 0%, rgba(255, 199, 0, 0) 68%);"></div>
          <div style="position: relative; display: flex; align-items: center; gap: 14px;">
            <span style="width: 34px; height: 34px; border-radius: 10px; background: #FFC700; display: flex; align-items: center; justify-content: center; flex-shrink: 0;"><svg width="16" height="16" viewBox="0 0 24 24" fill="#101318"><polygon points="13 2 3 14 11 14 10 22 21 10 13 10 13 2"></polygon></svg></span>
            <div style="display: flex; flex-direction: column; gap: 3px; max-width: 560px;">
              <span style="font-size: 15px; font-weight: 600; color: #FFC700;">Seus créditos acabaram.</span>
              <span style="font-size: 13px; line-height: 1.55; color: #9AA3AF;">Assine um plano para continuar agora, ou aguarde até <span style="color: #FFFFFF; font-weight: 500;">14/10</span>, quando a cota do seu plano reinicia sozinha.</span>
            </div>
          </div>
          <button style="position: relative; font-family: inherit; font-size: 14px; font-weight: 600; color: #101318; background: #FFC700; border: none; border-radius: 9px; padding: 14px 24px; flex-shrink: 0; cursor: pointer;">Obter mais créditos</button>
        </div>"""

sem_creditos = f"""      {cabecalho('Remix de takes', '', abas('remix'))}

{entradas(dim=True)}

        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px;">
{variacoes(dim=True)}
{headline(dim=True)}
        </div>

        <div style="display: flex; flex-direction: column; gap: 12px; margin-top: auto;">
{aviso}
          <div style="{CARTAO} padding: 16px 18px; display: flex; align-items: center; justify-content: space-between; gap: 20px;">
            <div style="display: flex; gap: 26px;">
              <div style="display: flex; flex-direction: column; gap: 1px;"><span style="font-size: 19px; font-weight: 700; letter-spacing: -0.022em;">15</span><span style="font-size: 11.5px; color: #5B6470;">vídeos</span></div>
              <div style="display: flex; flex-direction: column; gap: 1px;"><span style="font-size: 19px; font-weight: 700; letter-spacing: -0.022em;">15</span><span style="font-size: 11.5px; color: #5B6470;">créditos</span></div>
            </div>
            <button style="font-family: inherit; font-size: 14px; font-weight: 600; color: #A3ABB6; background: #E9EDF2; border: none; border-radius: 9px; padding: 14px 28px; display: flex; align-items: center; gap: 9px;">{PLAY}Gerar variações</button>
          </div>
        </div>"""

sem_creditos_dir = f"""        <div style="background: linear-gradient(180deg, #FFFCF0 0%%, #FFFFFF 40%%); border: 1px solid #F0DC93; border-radius: 12px; padding: 18px; display: flex; flex-direction: column; gap: 14px;">
          <div style="display: flex; align-items: center; gap: 11px;">
            <span style="width: 28px; height: 28px; border-radius: 9px; background: #FFC700; display: flex; align-items: center; justify-content: center; flex-shrink: 0;"><svg width="15" height="15" viewBox="0 0 24 24" fill="#101318"><polygon points="13 2 3 14 11 14 10 22 21 10 13 10 13 2"></polygon></svg></span>
            <div style="display: flex; flex-direction: column; gap: 1px;">
              <span style="font-size: 13.5px; font-weight: 600;">O que você ganha assinando</span>
              <span style="font-size: 11.5px; color: #8A7A45;">a partir de R$ 39 por mês</span>
            </div>
          </div>
          <div style="display: flex; flex-direction: column; gap: 8px;">
            <div style="display: flex; align-items: center; justify-content: space-between; gap: 10px; border: 1px solid #EBEEF1; background: #FFFFFF; border-radius: 10px; padding: 12px 13px;">
              <div style="display: flex; flex-direction: column; gap: 1px;"><span style="font-size: 13px; font-weight: 500;">Starter</span><span style="font-size: 11px; color: #8A93A0;">50 vídeos por mês</span></div>
              <span style="font-size: 14px; font-weight: 600;">R$ 39</span>
            </div>
            <div style="display: flex; align-items: center; justify-content: space-between; gap: 10px; background: #FFC700; border-radius: 10px; padding: 13px;">
              <div style="display: flex; flex-direction: column; gap: 1px;">
                <div style="display: flex; align-items: center; gap: 8px;">
                  <span style="font-size: 14px; font-weight: 700;">Pro</span>
                  <span style="font-family: ui-monospace, monospace; font-size: 9.5px; font-weight: 500; color: #8A7A45; background: rgba(16, 19, 24, 0.09); border-radius: 4px; padding: 3px 6px;">MAIS USADO</span>
                </div>
                <span style="font-size: 11px; color: #6B5A00;">150 vídeos por mês</span>
              </div>
              <span style="font-size: 17px; font-weight: 700; letter-spacing: -0.022em;">R$ 69</span>
            </div>
            <div style="display: flex; align-items: center; justify-content: space-between; gap: 10px; border: 1px solid #EBEEF1; background: #FFFFFF; border-radius: 10px; padding: 12px 13px;">
              <div style="display: flex; flex-direction: column; gap: 1px;"><span style="font-size: 13px; font-weight: 500;">Studio</span><span style="font-size: 11px; color: #8A93A0;">400 vídeos por mês</span></div>
              <span style="font-size: 14px; font-weight: 600;">R$ 117</span>
            </div>
          </div>
          <div style="font-size: 11.5px; line-height: 1.55; color: #5B6470; border-top: 1px solid #F0DC93; padding-top: 12px;">Crédito acumula sem teto e continua seu mesmo se você cancelar.</div>
        </div>
{ultimas_geracoes()}"""

tela('ConsoleSemCreditos.dc.html', area(sem_creditos, sem_creditos_dir), ativo='gerar',
     crumbs=('Estúdio', 'Remix de takes'), zerado=True)
