"""Três planos pagos, dois ciclos, e o preço vindo de uma fonte só.

O que este arquivo protege:

1. O preço NÃO mora no código. Se morasse, um dia o Stripe cobraria R$ 69 e a
   tela anunciaria R$ 39 — e o cliente teria razão em reclamar.
2. Falha ao ler o preço não vira número inventado. Some o valor, não a verdade.
3. A configuração antiga (STRIPE_PRICE_STARTER, sem sufixo de ciclo) continua
   valendo como mensal. Sem isso, o deploy apagaria os planos que já estão
   configurados no Render e o sintoma seria "sumiu a tela de planos".
"""

import os, sys, shutil

os.environ['VARVID_DATA'] = '/tmp/vartest/planos'
os.environ['RENDER_BACKEND'] = 'local'
os.environ['VARVID_SWEEPER'] = 'off'
shutil.rmtree('/tmp/vartest/planos', ignore_errors=True)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import local_app as A

c = A.app.test_client()
ok = fail = 0


def check(n, cond, extra=''):
    global ok, fail
    if cond:
        ok += 1; print(f"  ✓ {n}")
    else:
        fail += 1; print(f"  ✗ {n} {extra}")


class PrecoFalso:
    """Dublê do Stripe. Guarda quantas vezes foi consultado, pra provar o cache."""
    consultas = 0
    tabela = {
        'price_starter_m': 3900,  'price_starter_a': 39000,
        'price_pro_m':     6900,  'price_pro_a':     69000,
        'price_studio_m': 11700,  'price_studio_a': 117000,
    }

    @staticmethod
    def retrieve(pid):
        PrecoFalso.consultas += 1
        if pid not in PrecoFalso.tabela:
            raise RuntimeError('No such price: ' + pid)
        return {'unit_amount': PrecoFalso.tabela[pid], 'currency': 'brl'}


class StripeFalso:
    Price = PrecoFalso


A.AUTH_ENABLED = False
A.CREDITS_ENABLED = False
A.STRIPE_ENABLED = True
A.stripe = StripeFalso
A.STRIPE_PRICE_IDS = {
    'starter': {'mensal': 'price_starter_m', 'anual': 'price_starter_a'},
    'pro':     {'mensal': 'price_pro_m',     'anual': 'price_pro_a'},
    'studio':  {'mensal': 'price_studio_m',  'anual': 'price_studio_a'},
}

print("\n[1] Os três planos, com as quantidades combinadas")
check('free dá 10 vídeos', A.PLANS['free'] == 10, A.PLANS['free'])
check('starter dá 50', A.PLANS['starter'] == 50, A.PLANS['starter'])
check('pro dá 150', A.PLANS['pro'] == 150, A.PLANS['pro'])
check('studio dá 400', A.PLANS['studio'] == 400, A.PLANS['studio'])
check('a ordem na tela é starter → pro → studio',
      A.PLANS_PAGOS == ('starter', 'pro', 'studio'), A.PLANS_PAGOS)

print("\n[2] Preço vem do Stripe, não do código")
d = c.get('/billing/plans').get_json()
planos = {p['key']: p for p in d['plans']}
check('os três aparecem', list(planos) == ['starter', 'pro', 'studio'], list(planos))
check('starter mensal vem R$ 39',
      planos['starter']['ciclos']['mensal']['preco']['texto'] == 'R$ 39',
      planos['starter']['ciclos']['mensal']['preco'])
check('studio anual vem R$ 1170',
      planos['studio']['ciclos']['anual']['preco']['texto'] == 'R$ 1170,00'
      or planos['studio']['ciclos']['anual']['preco']['valor'] == 117000,
      planos['studio']['ciclos']['anual']['preco'])
check('o app sinaliza que existe anual', d.get('temAnual') is True)
# A prova de que o preço não está no código: mudo o valor SÓ no dublê e a
# resposta acompanha. Se algum número estivesse escrito no local_app.py, este
# teste falharia.
A._preco_cache.clear()
PrecoFalso.tabela['price_starter_m'] = 9900
d2 = c.get('/billing/plans').get_json()
novo = [p for p in d2['plans'] if p['key'] == 'starter'][0]['ciclos']['mensal']['preco']
check('mudou no Stripe, mudou na tela', novo['texto'] == 'R$ 99', novo)
PrecoFalso.tabela['price_starter_m'] = 3900
A._preco_cache.clear()

print("\n[3] Cache: preço não muda toda hora, não precisa perguntar toda vez")
A._preco_cache.clear()
c.get('/billing/plans')                 # primeira chamada: aquece o cache
antes = PrecoFalso.consultas
c.get('/billing/plans')                 # segunda: não deve tocar no Stripe
check('segunda chamada não consulta o Stripe de novo',
      PrecoFalso.consultas == antes, f'{antes} → {PrecoFalso.consultas}')

print("\n[4] Falha ao ler o preço não vira número inventado")
A._preco_cache.clear()
A.STRIPE_PRICE_IDS = dict(A.STRIPE_PRICE_IDS)
A.STRIPE_PRICE_IDS['pro'] = {'mensal': 'price_que_nao_existe'}
d = c.get('/billing/plans').get_json()
pro = [p for p in d['plans'] if p['key'] == 'pro'][0]
check('preço volta nulo', pro['ciclos']['mensal']['preco'] is None, pro['ciclos'])
check('o plano continua assinável', pro['ciclos']['mensal']['price_id'] == 'price_que_nao_existe')
check('os outros planos não são afetados',
      [p['key'] for p in d['plans']] == ['starter', 'pro', 'studio'])

print("\n[5] Plano sem mensal configurado não aparece")
A._preco_cache.clear()
A.STRIPE_PRICE_IDS = {
    'starter': {'mensal': 'price_starter_m', 'anual': 'price_starter_a'},
    'pro':     {'mensal': '', 'anual': ''},
    'studio':  {'mensal': 'price_studio_m', 'anual': ''},
}
d = c.get('/billing/plans').get_json()
check('pro some da tela', [p['key'] for p in d['plans']] == ['starter', 'studio'],
      [p['key'] for p in d['plans']])
check('studio aparece só com mensal',
      list([p for p in d['plans'] if p['key'] == 'studio'][0]['ciclos']) == ['mensal'])

print("\n[6] Formatação em reais")
check('39,00 vira "R$ 39"', A._fmt_moeda(3900, 'brl') == 'R$ 39', A._fmt_moeda(3900, 'brl'))
check('39,90 mantém os centavos', A._fmt_moeda(3990, 'brl') == 'R$ 39,90', A._fmt_moeda(3990, 'brl'))
check('1170,00 vira "R$ 1170"', A._fmt_moeda(117000, 'brl') == 'R$ 1170', A._fmt_moeda(117000, 'brl'))

print("\n[7] A configuração que já está no Render continua valendo")
# Antes existia só STRIPE_PRICE_STARTER, sem ciclo. Se o deploy exigisse o nome
# novo, os planos sumiriam no ar até alguém reconfigurar — e ninguém saberia por quê.
for k in list(os.environ):
    if k.startswith('STRIPE_PRICE'):
        os.environ.pop(k)
os.environ['STRIPE_PRICE_STARTER'] = 'price_velho'
os.environ['STRIPE_PRICE_PRO_ANUAL'] = 'price_novo_anual'
# Na máquina do Vinícius existe um supabase_config.json de verdade, e
# _load_stripe_config lê o arquivo ANTES do ambiente. Sem isolar, este teste
# leria as chaves reais dele e falharia — teste que só passa numa máquina não
# é teste. Apontamos a busca do arquivo para uma pasta vazia.
_base_real = A.BASE_DIR
A.BASE_DIR = '/tmp/vartest/sem-config'
os.makedirs(A.BASE_DIR, exist_ok=True)
try:
    _sk, _wh, ids = A._load_stripe_config()
finally:
    A.BASE_DIR = _base_real
check('nome antigo é lido como mensal', ids['starter']['mensal'] == 'price_velho', ids['starter'])
check('nome novo com ciclo também é lido', ids['pro']['anual'] == 'price_novo_anual', ids['pro'])
check('o que não foi configurado fica vazio', ids['studio']['mensal'] == '', ids['studio'])

print("\n[8] Checkout recusa ciclo inventado")
A.STRIPE_PRICE_IDS = {'starter': {'mensal': 'price_starter_m', 'anual': 'price_starter_a'}}
r = c.post('/billing/checkout', json={'plan': 'starter', 'ciclo': 'semanal'})
check('ciclo inválido é recusado', r.status_code == 400, r.status_code)
check('com nome do erro', (r.get_json() or {}).get('error') == 'ciclo_invalido', r.get_json())
r = c.post('/billing/checkout', json={'plan': 'studio', 'ciclo': 'mensal'})
check('plano sem preço configurado é recusado', r.status_code == 400, r.status_code)

print("\n[9] Portal do Cliente: o caminho pra cancelar")
# Não existir esse caminho era problema legal (o CDC pede que cancelar seja tão
# fácil quanto contratar) e financeiro: quem não consegue cancelar abre disputa
# no cartão, que custa taxa e mancha a conta no Stripe.
A.CREDITS_ENABLED = True
PERFIS = {'sem_cliente': {'plan': 'free', 'credits': 10},
          'com_cliente': {'plan': 'pro', 'credits': 10,
                          'stripe_customer_id': 'cus_123'}}
QUEM = {'id': 'sem_cliente'}
A.get_or_create_profile = lambda uid=None, email=None: dict(PERFIS[QUEM['id']])
A.current_user_id = lambda: QUEM['id']


class PortalFalso:
    class Session:
        @staticmethod
        def create(customer, return_url):
            assert customer == 'cus_123'
            return type('S', (), {'url': 'https://billing.stripe.com/p/sessao'})


StripeFalso.billing_portal = PortalFalso
A.stripe = StripeFalso

r = c.post('/billing/portal')
check('quem nunca assinou é recusado com nome', (r.get_json() or {}).get('error') == 'sem_assinatura',
      r.get_json())

QUEM['id'] = 'com_cliente'
r = c.post('/billing/portal')
check('assinante recebe o link do Stripe',
      (r.get_json() or {}).get('url', '').startswith('https://billing.stripe.com/'), r.get_json())

d = c.get('/billing/plans').get_json()
check('a tela sabe que há assinatura pra gerenciar', d.get('temAssinatura') is True, d.get('temAssinatura'))
QUEM['id'] = 'sem_cliente'
d = c.get('/billing/plans').get_json()
check('e sabe quando não há', d.get('temAssinatura') is False, d.get('temAssinatura'))

print(f"\n{ok} passaram · {fail} falharam")
sys.exit(1 if fail else 0)
