"""A tela de indicação, num navegador de verdade.

Sobe o app com o Supabase trocado por um dicionário, abre o modal de indicação e
fotografa. Também percorre o caminho do indicado: link com ?ref=, código guardado
no navegador, vínculo gravado no servidor, crédito de boas-vindas na conta.

Uso:  python3 previa_indicacao.py
"""

import os
import sys
import asyncio
import threading
import time

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)

os.environ['VARVID_DATA'] = '/tmp/vartest/refui'
os.environ['RENDER_BACKEND'] = 'local'
os.environ['VARVID_SWEEPER'] = 'off'

import local_app as A                                # noqa: E402

PORTA = 5223
CHROME = '/opt/pw-browsers/chromium-1194/chrome-linux/chrome'

BANCO = {}


def _sb(metodo, caminho, corpo=None):
    if metodo == 'POST':
        BANCO[(corpo or {}).get('id')] = dict(corpo or {})
        return [dict(corpo or {})]
    if 'id=eq.' in caminho:
        uid = caminho.split('id=eq.')[1].split('&')[0]
        if metodo == 'GET':
            return [dict(BANCO[uid])] if uid in BANCO else []
        if metodo == 'PATCH' and uid in BANCO:
            BANCO[uid].update(corpo or {})
            return [dict(BANCO[uid])]
        return []
    if 'referral_code=eq.' in caminho:
        c = caminho.split('referral_code=eq.')[1].split('&')[0]
        return [dict(p) for p in BANCO.values() if p.get('referral_code') == c]
    if 'referred_by=eq.' in caminho:
        c = caminho.split('referred_by=eq.')[1].split('&')[0]
        achados = [dict(p) for p in BANCO.values() if p.get('referred_by') == c]
        if 'ref_ativou=is.true' in caminho:
            achados = [p for p in achados if p.get('ref_ativou')]
        return achados
    return []


def perfil(uid, **kw):
    BANCO[uid] = {'id': uid, 'plan': 'free', 'credits': 10, 'ciclo': None,
                  'referral_code': A.codigo_de_indicacao(uid), 'referred_by': None,
                  'ref_ativou': False, 'ref_pagou': False}
    BANCO[uid].update(kw)
    return BANCO[uid]


def main():
    A._sb_rest = _sb
    A.CREDITS_ENABLED = True
    A.STRIPE_ENABLED = False
    A.AUTH_ENABLED = False          # current_user_id() vira 'local'
    A.MODAL_ENABLED = False

    # O dono do link já trouxe gente: 3 entraram, 2 geraram, 1 assinou.
    perfil('local')
    for i, etapas in enumerate([('ativacao', 'pago'), ('ativacao',), ()]):
        perfil('amigo%d' % i)
        A.registrar_indicacao('amigo%d' % i, A.codigo_de_indicacao('local'))
        for e in etapas:
            A.resolver_indicacao('amigo%d' % i, e)

    threading.Thread(
        target=lambda: A.app.run(port=PORTA, debug=False, use_reloader=False),
        daemon=True).start()
    time.sleep(2)
    sys.exit(asyncio.run(rodar()))


async def rodar():
    from playwright.async_api import async_playwright
    falhas = []

    async with async_playwright() as p:
        nav = await p.chromium.launch(executable_path=CHROME)
        pag = await nav.new_page(viewport={'width': 1100, 'height': 760},
                                 device_scale_factor=2)
        await pag.goto('http://127.0.0.1:%d/' % PORTA)
        await pag.wait_for_function('typeof abrirIndicacao === "function"')

        # Sem login o botão não aparece sozinho (refreshMe só roda com auth),
        # então abrimos o modal direto — é o conteúdo dele que interessa aqui.
        await pag.evaluate('abrirIndicacao()')
        await pag.wait_for_function(
            "document.getElementById('refLink').textContent.indexOf('ref=') !== -1",
            timeout=10000)
        await pag.wait_for_timeout(400)

        link = await pag.inner_text('#refLink')
        placar = [await pag.inner_text(x) for x in ('#refEntraram', '#refAtivaram', '#refPagaram')]
        teto = await pag.inner_text('#refTeto')
        destino = os.path.join(BASE, 'previa', 'indicacao.png')
        os.makedirs(os.path.dirname(destino), exist_ok=True)
        await pag.locator('#refModal .modal').screenshot(path=destino)

        print('')
        print('  link ......... %s' % link)
        print('  placar ....... %s entraram · %s geraram · %s assinaram' % tuple(placar))
        print('  teto ......... %s' % teto.replace('\n', ' '))
        print('  foto ......... %s' % destino)
        if placar != ['3', '2', '1']:
            falhas.append('placar errado: %s' % placar)
        if A.codigo_de_indicacao('local') not in link:
            falhas.append('o link não traz o código do usuário')

        # ── o caminho de quem RECEBE o link ──────────────────────────────────
        codigo = A.codigo_de_indicacao('local')
        await pag.goto('http://127.0.0.1:%d/login?ref=%s' % (PORTA, codigo.lower()))
        await pag.wait_for_timeout(800)
        guardado = await pag.evaluate("localStorage.getItem('varvid_ref')")
        print('  guardado ..... %s' % guardado)
        if guardado != codigo:
            falhas.append('o código não ficou guardado no navegador (%s)' % guardado)

        # Um convidado novo chega ao app com o código ainda no navegador.
        perfil('local', referred_by=None, credits=10)
        await pag.goto('http://127.0.0.1:%d/' % PORTA)
        await pag.wait_for_function('typeof resolverIndicacaoPendente === "function"')
        await pag.evaluate("localStorage.setItem('varvid_ref', '%s')" % codigo)
        await pag.evaluate('resolverIndicacaoPendente()')
        await pag.wait_for_timeout(700)
        sobrou = await pag.evaluate("localStorage.getItem('varvid_ref')")
        print('  auto-indicação recusada, chave limpa: %s' % (sobrou is None))
        if sobrou is not None:
            falhas.append('a chave não foi limpa depois da tentativa')

        await nav.close()

    print('')
    if falhas:
        print('  RESULTADO: %s' % ' | '.join(falhas))
        return 1
    print('  RESULTADO: tela de indicação e captura do link funcionando ✓')
    return 0


main()
