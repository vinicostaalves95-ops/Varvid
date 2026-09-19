"""Reposição de créditos por data, com acúmulo e confirmação no Stripe.

Por que este arquivo existe: o modelo anterior repunha crédito quando o Stripe
avisava que uma fatura tinha sido paga. Isso quebrava de duas formas — o aviso
só chega se o webhook estiver configurado (não estava, então NINGUÉM era
reposto depois do primeiro mês), e no plano anual o aviso chega uma vez por
ano, o que daria um mês de cota para quem pagou doze.

Nada disso aparece em teste de tela nem em uso normal: some silenciosamente, e
o cliente descobre primeiro.
"""

import os, sys, shutil, datetime

os.environ['VARVID_DATA'] = '/tmp/vartest/cred'
os.environ['RENDER_BACKEND'] = 'local'
os.environ['VARVID_SWEEPER'] = 'off'
shutil.rmtree('/tmp/vartest/cred', ignore_errors=True)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import local_app as A

ok = fail = 0


def check(n, cond, extra=''):
    global ok, fail
    if cond:
        ok += 1; print(f"  ✓ {n}")
    else:
        fail += 1; print(f"  ✗ {n} {extra}")


# ── Supabase de mentira: um dicionário no lugar da tabela profiles ───────────
BANCO = {}


def _sb_falso(metodo, caminho, corpo=None):
    uid = caminho.split('id=eq.')[1].split('&')[0] if 'id=eq.' in caminho else None
    if metodo == 'GET':
        return [dict(BANCO[uid])] if uid in BANCO else []
    if metodo == 'PATCH' and uid in BANCO:
        BANCO[uid].update(corpo or {})
        return [dict(BANCO[uid])]
    if metodo == 'POST':
        BANCO[(corpo or {}).get('id')] = dict(corpo or {})
        return [dict(corpo or {})]
    return []


A._sb_rest = _sb_falso
A.CREDITS_ENABLED = True
A.STRIPE_ENABLED = True

STATUS = {'sub_ok': 'active', 'sub_morta': 'canceled', 'sub_atrasada': 'past_due'}
ERRO_DE_REDE = {'valor': False}


class SubFalsa:
    @staticmethod
    def retrieve(sid):
        if ERRO_DE_REDE['valor']:
            raise RuntimeError('Stripe fora do ar')
        return {'status': STATUS.get(sid, 'canceled')}


class StripeFalso:
    Subscription = SubFalsa


A.stripe = StripeFalso


def dias_atras(n):
    return A._iso(datetime.datetime.utcnow() - datetime.timedelta(days=n))


def perfil(uid, **kw):
    BANCO[uid] = {'id': uid, 'plan': 'pro', 'ciclo': 'mensal', 'credits': 10,
                  'stripe_subscription_id': 'sub_ok'}
    BANCO[uid].update(kw)
    return BANCO[uid]


print("\n[1] Mensal: repõe a cota e empurra um mês")
perfil('u1', credits=12, renova_em=dias_atras(1))
p = A.get_or_create_profile('u1')
check('somou os 150 do Pro', p['credits'] == 162, p['credits'])
check('a próxima data ficou no futuro',
      A._do_iso(p['renova_em']) > datetime.datetime.utcnow(), p['renova_em'])

print("\n[2] Acúmulo: o que sobrou não evapora")
# Esta era a armadilha do modelo antigo: ele fazia credits = cota, então quem
# tivesse 400 guardados voltava pra 150 no dia em que pagou por mais.
perfil('u2', credits=400, renova_em=dias_atras(1))
p = A.get_or_create_profile('u2')
check('400 + 150 = 550, não 150', p['credits'] == 550, p['credits'])

print("\n[3] Anual: o ano inteiro de uma vez, e a próxima só em 12 meses")
perfil('u3', ciclo='anual', credits=0, renova_em=dias_atras(1))
p = A.get_or_create_profile('u3')
check('recebeu 12 × 150 = 1800', p['credits'] == 1800, p['credits'])
prox = A._do_iso(p['renova_em'])
meses = (prox.year - datetime.datetime.utcnow().year) * 12 + (prox.month - datetime.datetime.utcnow().month)
check('próxima reposição em ~12 meses', 11 <= meses <= 12, meses)

print("\n[4] Ninguém entrou por 3 meses: as 3 reposições são aplicadas")
# Data exata em vez de "95 dias atrás": mês tem tamanho variável, e o teste tem
# que contar ciclos, não dias.
vencida = A._mais_meses(datetime.datetime.utcnow(), -3) + datetime.timedelta(hours=1)
perfil('u4', credits=0, renova_em=A._iso(vencida))
p = A.get_or_create_profile('u4')
check('recebeu 3 cotas de uma vez', p['credits'] == 450, p['credits'])
check('e a data já está no futuro',
      A._do_iso(p['renova_em']) > datetime.datetime.utcnow(), p['renova_em'])

print("\n[5] Data corrompida não vira laço infinito")
perfil('u5', credits=0, renova_em='1970-01-01T00:00:00Z')
p = A.get_or_create_profile('u5')
check('parou no teto de 24 ciclos', p['credits'] == 24 * 150, p['credits'])

print("\n[6] Assinatura cancelada NÃO gera crédito")
perfil('u6', credits=5, renova_em=dias_atras(1), stripe_subscription_id='sub_morta')
p = A.get_or_create_profile('u6')
check('saldo intocado', p['credits'] == 5, p['credits'])
check('a data continua vencida, pra tela poder explicar',
      A._do_iso(p['renova_em']) < datetime.datetime.utcnow())

print("\n[7] Cartão atrasado também não gera crédito")
perfil('u7', credits=5, renova_em=dias_atras(1), stripe_subscription_id='sub_atrasada')
p = A.get_or_create_profile('u7')
check('saldo intocado', p['credits'] == 5, p['credits'])

print("\n[8] Stripe fora do ar: não repõe, mas TENTA DE NOVO depois")
# A diferença entre "não sei" e "não": se tratássemos erro de rede como
# assinatura inativa e empurrássemos a data, quem pagou perderia a reposição
# do mês por causa de uma instabilidade de terceiro.
ERRO_DE_REDE['valor'] = True
perfil('u8', credits=7, renova_em=dias_atras(1))
p = A.get_or_create_profile('u8')
check('não repôs no erro', p['credits'] == 7, p['credits'])
check('a data NÃO foi empurrada', A._do_iso(p['renova_em']) < datetime.datetime.utcnow())
ERRO_DE_REDE['valor'] = False
p = A.get_or_create_profile('u8')       # Stripe voltou
check('com o Stripe de volta, repõe', p['credits'] == 157, p['credits'])

print("\n[9] Free não renova — é de uso único")
perfil('u9', plan='free', credits=0, renova_em=dias_atras(400))
p = A.get_or_create_profile('u9')
check('continua zerado', p['credits'] == 0, p['credits'])

print("\n[10] Assinar SOMA ao que a pessoa já tinha")
perfil('u10', plan='free', credits=4, renova_em=None)
A.set_plan('u10', 'starter', 'mensal')
check('4 do free + 50 do Starter = 54', BANCO['u10']['credits'] == 54, BANCO['u10']['credits'])
check('ciclo gravado', BANCO['u10']['ciclo'] == 'mensal')
check('data de renovação marcada', bool(BANCO['u10'].get('renova_em')))

perfil('u11', plan='free', credits=0, renova_em=None)
A.set_plan('u11', 'studio', 'anual')
check('studio anual dá 400 × 12 = 4800', BANCO['u11']['credits'] == 4800, BANCO['u11']['credits'])

print("\n[11] Soma de meses respeita o calendário")
d = datetime.datetime(2026, 1, 31)
check('31/01 + 1 mês = 28/02 (não 03/03)', A._mais_meses(d, 1).strftime('%d/%m') == '28/02',
      A._mais_meses(d, 1))
check('31/01 + 12 meses = 31/01 do ano seguinte',
      A._mais_meses(d, 12).strftime('%d/%m/%Y') == '31/01/2027', A._mais_meses(d, 12))

print("\n[12] Quando avisar que está acabando")
# Uma regra só: 20% da cota do ciclo. No mensal isso dá 30; no anual, 360.
check('mensal Pro com 100 não incomoda', A.saldo_acabando('pro', 'mensal', 100) is False)
check('mensal Pro com 30 avisa', A.saldo_acabando('pro', 'mensal', 30) is True)
# No anual o aviso vem MUITO antes, porque a próxima reposição pode estar a 10 meses.
check('anual Pro com 360 avisa', A.saldo_acabando('pro', 'anual', 360) is True)
check('anual Pro com 500 ainda não avisa', A.saldo_acabando('pro', 'anual', 500) is False)
check('no mesmo saldo, o anual avisa e o mensal não',
      A.saldo_acabando('pro', 'anual', 200) is True
      and A.saldo_acabando('pro', 'mensal', 200) is False)
check('free nunca avisa de renovação', A.saldo_acabando('free', 'mensal', 0) is False)

print("\n[13] Cobrança pelo que foi ENTREGUE, não pelo que foi pedido")
# Antes o crédito saía no despacho. Se a renderização falhasse, a pessoa ficava
# sem o crédito E sem o vídeo — tentava de novo e perdia de novo, sem estorno.
os.makedirs(A.DATA_DIR, exist_ok=True)


def job(jid, **kw):
    j = {'status': 'done', 'user_id': 'uc', 'completed': 5,
         'count_requested': 5, 'files': []}
    j.update(kw)
    A.save_job(jid, j)
    return j


perfil('uc', credits=100, renova_em=None)
j = job('j1', completed=5)
A.cobrar_entregues('j1', j)
check('5 entregues cobram 5', BANCO['uc']['credits'] == 95, BANCO['uc']['credits'])

perfil('uc', credits=100, renova_em=None)
j = job('j2', completed=3, count_requested=5)
A.cobrar_entregues('j2', j)
check('saiu 3 dos 5 pedidos: cobra 3', BANCO['uc']['credits'] == 97, BANCO['uc']['credits'])

perfil('uc', credits=100, renova_em=None)
j = job('j3', status='error', completed=0)
A.cobrar_entregues('j3', j)
check('falhou tudo: não cobra nada', BANCO['uc']['credits'] == 100, BANCO['uc']['credits'])

perfil('uc', credits=100, renova_em=None)
j = job('j4', completed=5)
A.cobrar_entregues('j4', j)
A.cobrar_entregues('j4', A.load_job('j4'))
A.cobrar_entregues('j4', A.load_job('j4'))
check('cobrar duas vezes não cobra duas vezes', BANCO['uc']['credits'] == 95,
      BANCO['uc']['credits'])

perfil('uc', credits=100, renova_em=None)
j = job('j5', status='rendering', completed=2)
A.cobrar_entregues('j5', j)
check('job em andamento ainda não é cobrado', BANCO['uc']['credits'] == 100,
      BANCO['uc']['credits'])

perfil('uc', credits=100, renova_em=None)
j = job('j6', status='error', completed=2, count_requested=5)
A.cobrar_entregues('j6', j)
check('erro com entrega parcial cobra o que saiu', BANCO['uc']['credits'] == 98,
      BANCO['uc']['credits'])

print("\n[14] Gerar de novo no mesmo job é uma cobrança NOVA")
# O bug: a tela reaproveita o job_id quando a pessoa muda a quantidade e clica
# em GERAR outra vez. O /generate reescrevia o registro por cima mas deixava a
# marca `cobrado` de pé — e o selo que impede cobrar duas vezes pela MESMA
# entrega acabava isentando a entrega SEGUINTE. Medido no app rodando: gerar 3,
# trocar pra 4 e gerar de novo custava 3 créditos no total em vez de 7.
perfil('uc', credits=100, renova_em=None)
j = job('r1', completed=3, count_requested=3)
A.cobrar_entregues('r1', j)
check('1ª rodada: 3 entregues cobram 3', BANCO['uc']['credits'] == 97,
      BANCO['uc']['credits'])

A.preparar_nova_rodada(j, 4, '', 3)
check('a marca de cobrança não atravessa a rodada', not j.get('cobrado'), j.get('cobrado'))
j['status'] = 'done'; j['completed'] = 4
A.save_job('r1', j)
A.cobrar_entregues('r1', j)
check('2ª rodada no MESMO job cobra os 4', BANCO['uc']['credits'] == 93,
      BANCO['uc']['credits'])

# O caminho que mais doía: uma geração que falha sem entregar nada também marca
# `cobrado` (certo, não se cobra por nada). Com a marca sobrevivendo, quem batia
# num erro e tentava de novo na mesma tela nunca pagava.
perfil('uc', credits=100, renova_em=None)
j = job('r2', status='error', completed=0, count_requested=5)
A.cobrar_entregues('r2', j)
check('rodada que falhou não cobra', BANCO['uc']['credits'] == 100, BANCO['uc']['credits'])
A.preparar_nova_rodada(j, 5, '', 3)
j['status'] = 'done'; j['completed'] = 5
A.save_job('r2', j)
A.cobrar_entregues('r2', j)
check('a tentativa seguinte NÃO sai de graça', BANCO['uc']['credits'] == 95,
      BANCO['uc']['credits'])

# Dentro de uma mesma rodada o selo continua valendo: /status bate a cada 1,5s
# e o Modal também avisa — os dois chamam cobrar_entregues.
A.cobrar_entregues('r2', A.load_job('r2'))
A.cobrar_entregues('r2', A.load_job('r2'))
check('dentro da rodada, o selo segue impedindo cobrança dupla',
      BANCO['uc']['credits'] == 95, BANCO['uc']['credits'])

# Sobra de rodada anterior que confundiria a tela nova.
j = job('r3', completed=2, error='deu ruim', takes_map={'hook': ['a.mp4']})
A.preparar_nova_rodada(j, 6, 'oi', 4)
check('erro antigo some no reset', 'error' not in j, j.get('error'))
check('contagem pedida vira a nova', j['count_requested'] == 6, j['count_requested'])
check('volta pra fila zerado',
      j['status'] == 'queued' and j['completed'] == 0 and j['files'] == [],
      (j['status'], j['completed'], j['files']))


print("\n[15] Conceder o plano: uma vez por pagamento")
# /billing/success chamava set_plan() direto, e set_plan SOMA créditos. Quem
# guardasse a URL de retorno ganhava a cota inteira a cada recarga. Agora o id
# da sessão de checkout é reivindicado no banco, e só o primeiro concede.
import urllib.error                                                   # noqa: E402

CHECKOUTS = set()
_sb_original = A._sb_rest


def _sb_com_checkouts(metodo, caminho, corpo=None):
    if caminho.startswith('checkouts_processados'):
        if metodo == 'POST':
            sid = (corpo or {}).get('session_id')
            if sid in CHECKOUTS:
                raise urllib.error.HTTPError(caminho, 409, 'duplicate key', {}, None)
            CHECKOUTS.add(sid)
            return [dict(corpo or {})]
        return []
    return _sb_falso(metodo, caminho, corpo)


A._sb_rest = _sb_com_checkouts
A.STRIPE_ENABLED = True

SESSAO = {'id': 'cs_test_1', 'payment_status': 'paid', 'client_reference_id': 'uc',
          'metadata': {'plan': 'starter', 'ciclo': 'mensal'},
          'customer': 'cus_1', 'subscription': 'sub_1'}

perfil('uc', credits=4, plan='free', renova_em=None)
check('primeira volta concede', A.aplicar_checkout(dict(SESSAO)) is True)
check('somou a cota ao que já tinha (4 + 50)', BANCO['uc']['credits'] == 54,
      BANCO['uc']['credits'])
check('e gravou a assinatura', BANCO['uc'].get('stripe_subscription_id') == 'sub_1',
      BANCO['uc'].get('stripe_subscription_id'))

check('recarregar a página não concede de novo',
      A.aplicar_checkout(dict(SESSAO)) is False)
A.aplicar_checkout(dict(SESSAO)); A.aplicar_checkout(dict(SESSAO))
check('e o saldo não se mexe por mais que recarreguem',
      BANCO['uc']['credits'] == 54, BANCO['uc']['credits'])

# O webhook chega pelo servidor e pode vir antes ou depois da volta do
# navegador. Quem chegar primeiro concede; o outro vê que já foi.
perfil('uc', credits=0, plan='free', renova_em=None)
CHECKOUTS.clear()
outra = dict(SESSAO, id='cs_test_2')
check('webhook primeiro: concede', A.aplicar_checkout(dict(outra)) is True)
check('navegador depois: não repete', A.aplicar_checkout(dict(outra)) is False)
check('uma cota só', BANCO['uc']['credits'] == 50, BANCO['uc']['credits'])

# Pagamento não confirmado não vira plano.
perfil('uc', credits=0, plan='free', renova_em=None)
nao_paga = dict(SESSAO, id='cs_test_3', payment_status='unpaid')
check('sessão não paga não concede nada', A.aplicar_checkout(nao_paga) is False)
check('e o saldo continua zero', BANCO['uc']['credits'] == 0, BANCO['uc']['credits'])

# Plano inventado na metadata não passa.
perfil('uc', credits=0, plan='free', renova_em=None)
falso = dict(SESSAO, id='cs_test_4', metadata={'plan': 'infinito', 'ciclo': 'mensal'})
check('plano que não existe é recusado', A.aplicar_checkout(falso) is False)
check('sem crédito nenhum', BANCO['uc']['credits'] == 0, BANCO['uc']['credits'])

# Se o registro falhar por outro motivo (tabela ausente, banco fora), quem
# pagou precisa receber. O log grita, mas o cliente não fica sem.
def _sb_sem_tabela(metodo, caminho, corpo=None):
    if caminho.startswith('checkouts_processados'):
        raise urllib.error.HTTPError(caminho, 404, 'no such table', {}, None)
    return _sb_falso(metodo, caminho, corpo)


A._sb_rest = _sb_sem_tabela
perfil('uc', credits=0, plan='free', renova_em=None)
check('banco de registro fora: concede assim mesmo',
      A.aplicar_checkout(dict(SESSAO, id='cs_test_5')) is True)
check('quem pagou recebeu', BANCO['uc']['credits'] == 50, BANCO['uc']['credits'])
A._sb_rest = _sb_com_checkouts

A.STRIPE_ENABLED = False
A._sb_rest = _sb_falso


print("\n[16] Conferir saldo não é cobrar")
perfil('uc', credits=10, renova_em=None)
podeok, saldo, err = A.tem_creditos('uc', 5)
check('tem saldo: deixa passar', podeok is True and err is None, (podeok, err))
check('e NÃO debitou nada', BANCO['uc']['credits'] == 10, BANCO['uc']['credits'])
podeok, saldo, err = A.tem_creditos('uc', 50)
check('sem saldo: barra antes de começar', err == 'sem_creditos', err)
check('e continua sem debitar', BANCO['uc']['credits'] == 10, BANCO['uc']['credits'])

print(f"\n{ok} passaram · {fail} falharam")
sys.exit(1 if fail else 0)
