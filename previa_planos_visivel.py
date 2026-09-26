"""O rodapé do modal de Planos, visto como o cliente vê — em telas de verdade.

Na planilha de QA: "o rodapé do modal de Planos não está muito visível, além do
'Gerenciar assinatura' não aparecer como clicável" e "não está claro a forma de
pagamento". O teste de tela (test_front.js) prova a lógica; ele não enxerga cor,
contraste, tamanho nem se o rodapé cabe. Aqui a página é aberta num navegador
de verdade e medida.

O que se garante, em cada tela:
  · as formas de pagamento estão escritas no modal;
  · "Gerenciar assinatura" aparece só para assinante, parece botão (cursor,
    tamanho) e é alcançável;
  · o texto do rodapé e os links têm contraste mínimo de 4,5:1 (WCAG AA) contra
    o fundo do modal, e nenhum link está no azul padrão do navegador;
  · o modal nunca passa da altura da janela, e o que sobra dá pra rolar;
  · nada estoura na horizontal.

Uso:  python3 previa_planos_visivel.py
"""

import os
import sys
import time
import asyncio
import threading

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)

os.environ['VARVID_DATA'] = '/tmp/vartest/planosvis'
os.environ['RENDER_BACKEND'] = 'local'
os.environ['VARVID_SWEEPER'] = 'off'

import local_app as A                                   # noqa: E402

PORTA = 5233
CHROME = '/opt/pw-browsers/chromium-1194/chrome-linux/chrome'

# Área ÚTIL do navegador, não resolução de monitor.
TELAS = [
    ('MacBook Air 13" ....', 1440, 700),
    ('notebook 1366x768 ..', 1366, 610),
    ('celular 390x800 ....', 390, 800),
    ('celular baixo ......', 360, 560),
    ('janela muito baixa .', 1280, 420),
]

TABELA = {'p_starter_m': 3900, 'p_starter_a': 39000, 'p_pro_m': 6900,
          'p_pro_a': 69000, 'p_studio_m': 11700, 'p_studio_a': 117000}


class PrecoFalso:
    @staticmethod
    def retrieve(pid):
        return {'unit_amount': TABELA[pid], 'currency': 'brl'}


class StripeFalso:
    Price = PrecoFalso


# Termos/Privacidade estão ocultos desde 25/09 (ver LINKS-LEGAIS-OCULTOS no app.html).
# Ao religar os links, trocar para 2 — a guarda volta a exigir contraste e alcance.
LINKS_LEGAIS = 0

MEDIR = """() => {
  const rgb = c => (c.match(/[\\d.]+/g) || []).slice(0, 3).map(Number);
  const lum = ([r, g, b]) => {
    const f = v => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); };
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b);
  };
  const razao = (a, b) => {
    if (!a) return 0;                       // elemento ausente = reprovado, não erro
    const [l1, l2] = [lum(rgb(a)), lum(rgb(b))].sort((x, y) => y - x);
    return (l1 + 0.05) / (l2 + 0.05);
  };
  const modal = document.querySelector('#plansModal .modal');
  const fundo = getComputedStyle(modal).backgroundColor;
  const cor = el => el ? getComputedStyle(el).color : null;
  const nota = modal.querySelector('.modal-note');
  const links = [...modal.querySelectorAll('.modal-note a')];
  const pay = modal.querySelector('.pay-info');
  const sub = modal.querySelector('.pay-sub');
  const portal = document.getElementById('portalLink');
  const cs = getComputedStyle(portal);
  const rp = portal.getBoundingClientRect();
  const rm = modal.getBoundingClientRect();
  return {
    textoPagamento: pay ? (pay.innerText || '').toLowerCase() : '',
    portalVisivel: cs.display !== 'none',
    portalCursor: cs.cursor,
    portalAltura: Math.round(rp.height),
    portalLargura: Math.round(rp.width),
    portalTexto: (portal.innerText || '').toLowerCase(),
    linksAzulPadrao: links.filter(a => cor(a) === 'rgb(0, 0, 238)').length,
    nLinks: links.length,
    contrasteNota: razao(cor(nota), fundo),
    contrasteLinks: links.length ? Math.min(...links.map(a => razao(cor(a), fundo))) : 0,
    contrastePay: razao(cor(pay), fundo),
    contrasteSub: razao(cor(sub), fundo),
    modalFundo: Math.round(rm.bottom), janela: window.innerHeight,
    modalTopo: Math.round(rm.top),
    rolavel: modal.scrollHeight > modal.clientHeight,
    overflowY: getComputedStyle(modal).overflowY,
    estouroLateral: modal.scrollWidth > modal.clientWidth + 1,
  };
}"""


async def rodar():
    from playwright.async_api import async_playwright

    falhas = []

    def exige(cond, msg):
        if not cond:
            falhas.append(msg)
        return cond

    async with async_playwright() as p:
        nav = await p.chromium.launch(executable_path=CHROME)
        for rotulo, larg, alt in TELAS:
            for assina in (True, False):
                nome = '%s %s' % (rotulo.strip(' .'), 'assinante' if assina else 'sem plano')
                pag = await nav.new_page(viewport={'width': larg, 'height': alt})
                await pag.goto('http://127.0.0.1:%d/' % PORTA)
                await pag.wait_for_function('typeof openPlans === "function"')
                await pag.evaluate('loadBilling()')
                await pag.wait_for_function(
                    'typeof PLANS_DATA !== "undefined" && PLANS_DATA && '
                    'PLANS_DATA.plans && PLANS_DATA.plans.length === 3', timeout=15000)
                await pag.evaluate(
                    'PLANS_DATA.temAssinatura = %s; PLANS_DATA.currentPlan = %s'
                    % ('true' if assina else 'false', "'pro'" if assina else "'free'"))
                await pag.evaluate('openPlans()')
                await pag.wait_for_timeout(200)
                m = await pag.evaluate(MEDIR)

                exige('crédito' in m['textoPagamento'], nome + ': não diz "crédito"')
                exige('débito' in m['textoPagamento'], nome + ': não fala de débito')
                exige(m['portalVisivel'] == assina,
                      nome + ': botão de gerenciar %s' % ('sumiu para assinante' if assina else 'apareceu sem assinatura'))
                if assina:
                    exige(m['portalCursor'] == 'pointer', nome + ': botão sem cursor de clique')
                    exige(m['portalAltura'] >= 40, nome + ': botão baixo demais (%dpx)' % m['portalAltura'])
                    exige('gerenciar assinatura' in m['portalTexto'], nome + ': texto do botão mudou')
                exige(m['linksAzulPadrao'] == 0, nome + ': link no azul padrão do navegador')
                exige(m['nLinks'] == LINKS_LEGAIS, nome + ': esperava %d links legais, achou %d' % (LINKS_LEGAIS, m['nLinks']))
                for chave in (('contrasteNota', 'contrastePay', 'contrasteSub') + (('contrasteLinks',) if LINKS_LEGAIS else ())):
                    exige(m[chave] >= 4.5, nome + ': %s %.1f:1 (mínimo 4,5:1)' % (chave, m[chave]))
                exige(m['modalTopo'] >= 0 and m['modalFundo'] <= m['janela'],
                      nome + ': modal passa da janela (%d..%d de %d)' % (m['modalTopo'], m['modalFundo'], m['janela']))
                exige(not m['estouroLateral'], nome + ': estoura na horizontal')

                # o que não cabe precisa ser alcançável: rola o modal até o fim
                await pag.evaluate(
                    "document.querySelector('#plansModal .modal').scrollTop = 99999")
                fim = await pag.evaluate("""() => {
                  const l = document.querySelector('#plansModal .modal-note a:last-child') || document.querySelector('#plansModal .modal-note');
                  const r = l.getBoundingClientRect();
                  return {topo: Math.round(r.top), fundo: Math.round(r.bottom), janela: window.innerHeight};
                }""")
                exige(0 <= fim['topo'] and fim['fundo'] <= fim['janela'],
                      nome + ': rodapé inalcançável (y=%d..%d, janela %d)' % (fim['topo'], fim['fundo'], fim['janela']))

                print('  %-42s %s · contraste %.1f:1 · %s' % (
                    nome, 'cabe' if not m['rolavel'] else 'rola',
                    min(m['contrasteNota'], m['contrastePay'], m['contrasteSub']),
                    'gerenciar visível' if m['portalVisivel'] else 'sem gerenciar'))
                await pag.close()
        await nav.close()
    return falhas


def main():
    A.AUTH_ENABLED = False
    A.CREDITS_ENABLED = False
    A.STRIPE_ENABLED = True
    A.stripe = StripeFalso
    A.STRIPE_PRICE_IDS = {
        'starter': {'mensal': 'p_starter_m', 'anual': 'p_starter_a'},
        'pro':     {'mensal': 'p_pro_m',     'anual': 'p_pro_a'},
        'studio':  {'mensal': 'p_studio_m',  'anual': 'p_studio_a'},
    }
    threading.Thread(target=lambda: A.app.run(port=PORTA, debug=False, use_reloader=False),
                     daemon=True).start()
    time.sleep(2)
    falhas = asyncio.run(rodar())
    print('')
    if falhas:
        print('❌ %d problema(s):' % len(falhas))
        for f in falhas:
            print('   · ' + f)
        sys.exit(1)
    print('✓ rodapé do modal de Planos legível e alcançável em todas as telas')


main()
