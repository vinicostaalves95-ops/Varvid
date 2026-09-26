"""Cobrança e bônus sob CONCORRÊNCIA — o mesmo evento chegando por dois caminhos.

Por que este arquivo existe: em produção, o fim de uma geração é anunciado por
dois lados ao mesmo tempo — o Modal (PUT em /output/<job>/meta/_done) e o
navegador, que consulta /status a cada 1,5 s. Os dois terminam em
cobrar_entregues(). Quando os dois chegam dentro da mesma janela, o teste de
`cobrado` acontece antes de qualquer um gravar a marca, e cada um cobra.

Os testes sequenciais de test_creditos.py NÃO enxergam isso: chamam uma função
depois da outra. Aqui as chamadas são simultâneas, e o banco de mentira tem
latência (como o Supabase tem) para o intervalo entre "ler" e "gravar" ser
grande o bastante para a corrida acontecer sempre, não uma vez em mil.

Sintomas que esta corrida produz, e que a planilha de QA registrou:
  · "os créditos estão sendo cobrados em dobro"
  · "quem indicou recebeu 10 em vez de 5" (o bônus de ativação, 5, pago duas vezes)
"""

import os
import sys
import time
import shutil
import random
import threading

os.environ['VARVID_DATA'] = '/tmp/vartest/conc'
os.environ['RENDER_BACKEND'] = 'local'
os.environ['VARVID_SWEEPER'] = 'off'
shutil.rmtree('/tmp/vartest/conc', ignore_errors=True)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import local_app as A                                   # noqa: E402

ok = fail = 0


def check(n, cond, extra=''):
    global ok, fail
    if cond:
        ok += 1
        print('  ✓ %s' % n)
    else:
        fail += 1
        print('  ✗ %s %s' % (n, extra))


# ── Supabase de mentira, COM latência ────────────────────────────────────────
# Cada chamada individual é atômica (como uma requisição ao Postgres), mas leva
# tempo. Ler-e-depois-gravar continua sendo duas chamadas, com uma fresta no meio.
BANCO = {}
_TRAVA_BANCO = threading.Lock()
LATENCIA = 0.02
# Cada gravação que mexe em `credits`, na ordem. É AQUI que se conta a cobrança:
# olhar só o saldo final engana, porque duas gravações concorrentes de valor
# absoluto se sobrescrevem (a última vence) e uma cobrança em dobro some do saldo
# — ela existe, mas o resultado parece certo. O evento não mente; o saldo sim.
GRAVACOES_CREDITO = []
_ALEATORIO = random.Random(7)


def _sb(metodo, caminho, corpo=None):
    # latência irregular, como a rede de verdade: com todas as threads dormindo o
    # mesmo tempo elas leem o mesmo saldo e o resultado sai igual por acaso
    time.sleep(LATENCIA * _ALEATORIO.uniform(0.3, 1.7))
    with _TRAVA_BANCO:
        if metodo == 'PATCH' and 'credits' in (corpo or {}) and 'id=eq.' in caminho:
            GRAVACOES_CREDITO.append((caminho.split('id=eq.')[1].split('&')[0],
                                      corpo['credits']))
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
            cod = caminho.split('referral_code=eq.')[1].split('&')[0]
            return [dict(p) for p in BANCO.values() if p.get('referral_code') == cod]
        if 'referred_by=eq.' in caminho:
            cod = caminho.split('referred_by=eq.')[1].split('&')[0]
            achados = [dict(p) for p in BANCO.values() if p.get('referred_by') == cod]
            if 'ref_ativou=is.true' in caminho:
                achados = [p for p in achados if p.get('ref_ativou')]
            return achados
        return []


A._sb_rest = _sb
A.CREDITS_ENABLED = True
A.STRIPE_ENABLED = False


def cenario(creditos=100, entregues=5, jid='cj'):
    """Um indicado (uc) com um job pronto, e o padrinho (up) que o indicou."""
    BANCO.clear()
    del GRAVACOES_CREDITO[:]
    BANCO['up'] = {'id': 'up', 'plan': 'free', 'credits': 0, 'referral_code': 'PADRINHO'}
    BANCO['uc'] = {'id': 'uc', 'plan': 'free', 'credits': creditos,
                   'referred_by': 'PADRINHO', 'ref_ativou': False, 'ref_pagou': False}
    A.save_job(jid, {'status': 'done', 'user_id': 'uc', 'completed': entregues,
                     'count_requested': entregues, 'files': [], 'progress': 100})
    return jid


def eventos(uid):
    """Quantas vezes o saldo de `uid` foi regravado desde o início do cenário."""
    return len([g for g in GRAVACOES_CREDITO if g[0] == uid])


def em_paralelo(alvos):
    """Dispara todos ao mesmo tempo (largam juntos, numa barreira)."""
    barreira = threading.Barrier(len(alvos))
    erros = []

    def roda(f):
        try:
            barreira.wait()
            f()
        except Exception as e:                            # pragma: no cover
            erros.append(e)

    ts = [threading.Thread(target=roda, args=(f,)) for f in alvos]
    for t in ts:
        t.start()
    for t in ts:
        t.join(30)
    return erros


print("\n[1] Dois caminhos anunciando o fim ao mesmo tempo")
# É o que /status faz: lê o job do disco e entrega a cobrar_entregues.
jid = cenario()
erros = em_paralelo([lambda: A.cobrar_entregues(jid, A.load_job(jid))
                     for _ in range(2)])
check('sem exceção nas threads', not erros, erros)
check('cobrou UMA vez (100 -> 95)', BANCO['uc']['credits'] == 95, BANCO['uc']['credits'])
check('UMA gravação de débito, não duas', eventos('uc') == 1, eventos('uc'))
check('quem indicou ganhou 5, não 10', BANCO['up']['credits'] == 5, BANCO['up']['credits'])
check('UM pagamento de bônus, não dois', eventos('up') == 1, eventos('up'))
check('job marcado com o valor cobrado', A.load_job(jid).get('cobrado_creditos') == 5,
      A.load_job(jid))

print("\n[2] Oito consultas simultâneas (navegador em várias abas + Modal)")
jid = cenario(entregues=3, jid='cj2')
erros = em_paralelo([lambda: A.cobrar_entregues(jid, A.load_job(jid))
                     for _ in range(8)])
check('cobrou UMA vez (100 -> 97)', BANCO['uc']['credits'] == 97, BANCO['uc']['credits'])
check('UMA gravação de débito entre 8 consultas', eventos('uc') == 1, eventos('uc'))
check('padrinho recebeu 5 uma vez só', BANCO['up']['credits'] == 5, BANCO['up']['credits'])
check('UM pagamento de bônus entre 8 consultas', eventos('up') == 1, eventos('up'))
check('marca de ativação gravada', BANCO['uc'].get('ref_ativou') is True)

print("\n[3] Um `_done` atrasado não pode apagar a marca de cobrança")
# O /status já cobrou e gravou `cobrado`. O aviso do Modal tinha lido o job ANTES
# disso e grava a cópia velha por cima: a marca some, e a próxima consulta cobra
# de novo. O caminho real passa pela rota, então o teste também.
A.R2_ENABLED = True
A.MODAL_ENABLED = False
A.MODAL_CALLBACK_SECRET = ''
cli = A.app.test_client()
jid = cenario(entregues=4, jid='cj3')
# o job ainda está "rendering" quando o Modal vai avisar o fim
j0 = A.load_job(jid)
j0['status'] = 'rendering'
A.save_job(jid, j0)


def aviso_modal():
    cli.put('/output/%s/meta/_done' % jid, json={'status': 'done',
                                                 'files': ['a.mp4', 'b.mp4', 'c.mp4', 'd.mp4']})


def consulta_navegador():
    for _ in range(4):
        cli.get('/status/%s' % jid)
        time.sleep(0.01)


erros = em_paralelo([aviso_modal, consulta_navegador, consulta_navegador])
for _ in range(3):                                        # consultas depois do fim
    cli.get('/status/%s' % jid)
check('sem exceção nas threads', not erros, erros)
check('cobrou os 4 entregues UMA vez (100 -> 96)', BANCO['uc']['credits'] == 96,
      BANCO['uc']['credits'])
check('quem indicou ganhou 5 uma vez', BANCO['up']['credits'] == 5, BANCO['up']['credits'])
check('UMA gravação de débito no caminho real (rotas)', eventos('uc') == 1, eventos('uc'))
check('UM pagamento de bônus no caminho real (rotas)', eventos('up') == 1, eventos('up'))
check('a marca de cobrança sobreviveu', A.load_job(jid).get('cobrado') is True,
      A.load_job(jid))

print("\n[4] Rodada nova continua sendo cobrança nova (a correção de 19/09 vale)")
jid = cenario(entregues=3, jid='cj4')
A.cobrar_entregues(jid, A.load_job(jid))
j = A.load_job(jid)
A.preparar_nova_rodada(j, 4, '', 3)
j['status'] = 'done'
j['completed'] = 4
A.save_job(jid, j)
em_paralelo([lambda: A.cobrar_entregues(jid, A.load_job(jid)) for _ in range(4)])
check('3 + 4 = 7 cobrados no total (100 -> 93)', BANCO['uc']['credits'] == 93,
      BANCO['uc']['credits'])
check('bônus de ativação não repete na 2ª rodada', BANCO['up']['credits'] == 5,
      BANCO['up']['credits'])
check('2 débitos no total (um por rodada)', eventos('uc') == 2, eventos('uc'))

print("\n[5] Saldo insuficiente sob concorrência não deixa negativo")
jid = cenario(creditos=2, entregues=5, jid='cj5')
em_paralelo([lambda: A.cobrar_entregues(jid, A.load_job(jid)) for _ in range(4)])
check('saldo nunca negativo', BANCO['uc']['credits'] >= 0, BANCO['uc']['credits'])
check('cobrou só o que havia (2 -> 0)', BANCO['uc']['credits'] == 0, BANCO['uc']['credits'])

print("\n[6] Gerar de novo fecha a conta da rodada anterior antes de abrir outra")
# A rodada terminou, o aviso do Modal ainda não chegou e a aba já foi fechada e
# reaberta: ninguém cobrou. Se o /generate apagasse as marcas assim, aquele vídeo
# sairia de graça.
A.AUTH_ENABLED = True
A.current_user_id = lambda: 'uc'
A.ensure_disk_space = lambda variacoes=0: (True, 99999)
A.run_job_local = lambda *a, **k: None
A.MODAL_ENABLED = False
jid = cenario(entregues=3, jid='cj6')
os.makedirs(os.path.join(A.job_dir(jid), 'takes'), exist_ok=True)
r = cli.post('/generate', json={'job_id': jid, 'count': 2})
check('/generate aceitou', r.status_code == 200, r.status_code)
check('a rodada anterior foi cobrada (100 -> 97)', BANCO['uc']['credits'] == 97,
      BANCO['uc']['credits'])
check('quem indicou ganhou o bônus da rodada anterior', BANCO['up']['credits'] == 5,
      BANCO['up']['credits'])
check('a rodada nova começou limpa', not A.load_job(jid).get('cobrado'),
      A.load_job(jid))

print("\n[7] A trava vale entre PROCESSOS (é o caso dos workers do gunicorn)")
import subprocess
import textwrap

contador = os.path.join(A.DATA_DIR, 'contador.txt')
open(contador, 'w').write('0')
script = textwrap.dedent("""
    import os, sys, time
    os.environ['VARVID_DATA'] = %r
    os.environ['RENDER_BACKEND'] = 'local'
    os.environ['VARVID_SWEEPER'] = 'off'
    sys.path.insert(0, %r)
    import local_app as A
    for _ in range(15):
        with A.job_lock('jproc') as ok:
            assert ok
            n = int(open(%r).read())
            time.sleep(0.005)              # a fresta entre ler e gravar
            open(%r, 'w').write(str(n + 1))
""") % (A.DATA_DIR, os.path.dirname(os.path.abspath(__file__)), contador, contador)
procs = [subprocess.Popen([sys.executable, '-c', script], stdout=subprocess.DEVNULL,
                          stderr=subprocess.PIPE) for _ in range(4)]
saidas = [p.communicate(timeout=60) for p in procs]
check('os 4 processos terminaram sem erro', all(p.returncode == 0 for p in procs),
      [x[1][-200:] for x in saidas])
check('60 incrementos, nenhum perdido (4 processos x 15)',
      open(contador).read() == '60', open(contador).read())

print("\n[8] Reentrância, espera estourada e limpeza")
with A.job_lock('jre') as a:
    with A.job_lock('jre') as b:
        check('a mesma thread reentra sem travar', a is True and b is True)
    with A.job_lock('jre') as c:
        check('e continua reentrando depois de sair de um nível', c is True)

segurou = threading.Event()
soltar = threading.Event()


def segura():
    with A.job_lock('jocupado'):
        segurou.set()
        soltar.wait(10)


t = threading.Thread(target=segura)
t.start()
segurou.wait(5)
t0 = time.time()
with A.job_lock('jocupado', espera=0.3) as obtida:
    check('espera estourada devolve False (não trava para sempre)', obtida is False)
check('e desiste em torno do tempo pedido', 0.25 < time.time() - t0 < 2.0,
      round(time.time() - t0, 2))
# quem não consegue a trava não cobra — a próxima consulta cobra
jid = cenario(entregues=3, jid='jocupado')
antes = BANCO['uc']['credits']
_antiga = A.JOB_LOCK_ESPERA
A.JOB_LOCK_ESPERA = 0.2
A.cobrar_entregues(jid, A.load_job(jid))
A.JOB_LOCK_ESPERA = _antiga
check('sem a trava, cobrar_entregues desiste em vez de cobrar às cegas',
      BANCO['uc']['credits'] == antes, BANCO['uc']['credits'])
soltar.set()
t.join(10)
A.cobrar_entregues(jid, A.load_job(jid))
check('com a trava livre, a consulta seguinte cobra (100 -> 97)',
      BANCO['uc']['credits'] == antes - 3, BANCO['uc']['credits'])

A._purge_job('jre')
check('_purge_job também remove o arquivo de trava',
      not os.path.exists(os.path.join(A.DATA_DIR, 'jre.lock')))

print("\n%d passaram · %d falharam" % (ok, fail))
sys.exit(1 if fail else 0)
