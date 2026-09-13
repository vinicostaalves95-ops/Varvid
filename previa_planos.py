"""Fotografa o modal de Planos nos dois ciclos, com os preços vindos do Stripe.

Sobe o app com um Stripe dublê (preços R$ 39 / 69 / 117 e os anuais ×10) e
abre o modal. Serve pra olhar antes de criar qualquer preço de verdade.

Uso:  python3 previa_planos.py
"""

import os
import sys
import time
import asyncio
import threading

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)

os.environ['VARVID_DATA'] = '/tmp/vartest/planos-previa'
os.environ['RENDER_BACKEND'] = 'local'
os.environ['VARVID_SWEEPER'] = 'off'

import local_app as A                                # noqa: E402

PORTA = 5197
TABELA = {
    'p_starter_m': 3900,  'p_starter_a': 39000,
    'p_pro_m':     6900,  'p_pro_a':     69000,
    'p_studio_m': 11700,  'p_studio_a': 117000,
}


class PrecoFalso:
    @staticmethod
    def retrieve(pid):
        return {'unit_amount': TABELA[pid], 'currency': 'brl'}


class StripeFalso:
    Price = PrecoFalso


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

    threading.Thread(
        target=lambda: A.app.run(port=PORTA, debug=False, use_reloader=False),
        daemon=True).start()
    time.sleep(2)
    asyncio.run(olhar())


async def olhar():
    from playwright.async_api import async_playwright

    saida = os.path.join(BASE, 'previa')
    os.makedirs(saida, exist_ok=True)

    async with async_playwright() as p:
        nav = await p.chromium.launch(
            executable_path='/opt/pw-browsers/chromium-1194/chrome-linux/chrome')
        pag = await nav.new_page(viewport={'width': 980, 'height': 640},
                                 device_scale_factor=2)
        await pag.goto('http://127.0.0.1:%d/' % PORTA)
        await pag.wait_for_function('typeof openPlans === "function"')
        # No modo local (sem Supabase) o boot nem chama o loadBilling — planos
        # só existem com login. Aqui chamamos na mão só pra poder fotografar.
        await pag.evaluate('loadBilling()')
        await pag.wait_for_function(
            'typeof PLANS_DATA !== "undefined" && PLANS_DATA'
            ' && PLANS_DATA.plans && PLANS_DATA.plans.length===3',
            timeout=15000)
        for ciclo in ('mensal', 'anual'):
            await pag.evaluate('openPlans()')
            await pag.evaluate('setCiclo(%r)' % ciclo)
            await pag.wait_for_timeout(250)
            destino = os.path.join(saida, 'planos-%s.png' % ciclo)
            await pag.screenshot(path=destino)
            print('  ', destino)
        await nav.close()


main()
