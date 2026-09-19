"""Member get member — quem ganha, quanto, e quantas vezes.

Este arquivo existe porque indicação é crédito saindo de graça, e crédito de
graça é onde fraude mora. As três perguntas que ele responde:

  · o bônus sai UMA vez por indicado, por etapa?
  · dá pra se auto-indicar, ou trocar de padrinho depois?
  · o teto segura mesmo?

O desenho testado aqui: o indicado ganha na hora de entrar; quem indicou ganha
uma parte quando o indicado GERA pela primeira vez (cadastro é grátis, gerar
não é) e o resto quando ele ASSINA.
"""

import os
import sys
import shutil

os.environ['VARVID_DATA'] = '/tmp/vartest/ref'
os.environ['RENDER_BACKEND'] = 'local'
os.environ['VARVID_SWEEPER'] = 'off'
shutil.rmtree('/tmp/vartest/ref', ignore_errors=True)
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


# ── Supabase de mentira ──────────────────────────────────────────────────────
BANCO = {}
QUEBRADO = {'valor': False}


def _sb(metodo, caminho, corpo=None):
    if QUEBRADO['valor']:
        raise RuntimeError('banco fora do ar (de propósito)')
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


def novo(uid, creditos=10, plan='free'):
    """Cria um perfil já com o código gravado, como o app faz no 1º acesso."""
    BANCO[uid] = {'id': uid, 'plan': plan, 'credits': creditos, 'ciclo': None,
                  'referral_code': A.codigo_de_indicacao(uid),
                  'referred_by': None, 'ref_ativou': False, 'ref_pagou': False}
    return BANCO[uid]


def saldo(uid):
    return int(BANCO[uid]['credits'])


print('\n[1] O código é do usuário e não muda')
c1 = A.codigo_de_indicacao('ana')
check('mesmo id, mesmo código', c1 == A.codigo_de_indicacao('ana'), c1)
check('ids diferentes, códigos diferentes', c1 != A.codigo_de_indicacao('bia'))
check('não dá pra ler o id dentro dele', 'ANA' not in c1 and 'ana' not in c1, c1)

novo('ana')
BANCO['ana']['referral_code'] = None
check('garantir_codigo grava quando falta',
      A.garantir_codigo('ana', BANCO['ana']) == c1 and BANCO['ana']['referral_code'] == c1,
      BANCO['ana'])


print('\n[2] Entrar por indicação')
BANCO.clear()
novo('ana'); novo('bia', creditos=10)
feito, motivo = A.registrar_indicacao('bia', A.codigo_de_indicacao('ana'))
check('vinculou', feito and BANCO['bia']['referred_by'] == c1, (feito, motivo))
check('o indicado ganhou os 10 na hora', saldo('bia') == 20, saldo('bia'))
check('quem indicou ainda não ganhou nada', saldo('ana') == 10, saldo('ana'))

feito, motivo = A.registrar_indicacao('bia', A.codigo_de_indicacao('ana'))
check('não vincula duas vezes', not feito and motivo == 'ja_indicado', motivo)
check('e não paga o bônus de novo', saldo('bia') == 20, saldo('bia'))

novo('caio')
feito, motivo = A.registrar_indicacao('caio', A.codigo_de_indicacao('caio'))
check('auto-indicação é recusada', not feito and motivo == 'auto_indicacao', motivo)
check('e não credita nada', saldo('caio') == 10, saldo('caio'))

feito, motivo = A.registrar_indicacao('caio', 'NAOEXISTE')
check('código inexistente é recusado', not feito and motivo == 'codigo_invalido', motivo)

feito, motivo = A.registrar_indicacao('caio', A.codigo_de_indicacao('ana'))
check('minúsculo também casa', feito and BANCO['caio']['referred_by'] == c1, motivo)
A.registrar_indicacao('caio', A.codigo_de_indicacao('bia'))
check('não troca de padrinho depois', BANCO['caio']['referred_by'] == c1,
      BANCO['caio']['referred_by'])


print('\n[3] O bônus de ativação (o indicado GEROU)')
BANCO.clear()
novo('ana'); novo('bia')
A.registrar_indicacao('bia', c1)
A.resolver_indicacao('bia', 'ativacao')
check('quem indicou ganhou 5', saldo('ana') == 15, saldo('ana'))
A.resolver_indicacao('bia', 'ativacao')
A.resolver_indicacao('bia', 'ativacao')
check('e só uma vez, por mais que chamem', saldo('ana') == 15, saldo('ana'))

novo('sozinho')
A.resolver_indicacao('sozinho', 'ativacao')
check('quem entrou sem padrinho não gera bônus nenhum',
      saldo('sozinho') == 10, saldo('sozinho'))


print('\n[4] O bônus grande (o indicado ASSINOU)')
A.resolver_indicacao('bia', 'pago')
check('quem indicou ganhou mais 15', saldo('ana') == 30, saldo('ana'))
A.resolver_indicacao('bia', 'pago')
check('e só uma vez', saldo('ana') == 30, saldo('ana'))

# Quem paga antes de gerar não pode deixar o padrinho sem a primeira parte.
BANCO.clear()
novo('ana'); novo('duda')
A.registrar_indicacao('duda', c1)
A.resolver_indicacao('duda', 'pago')
check('assinar sem ter gerado paga as duas partes (5+15)', saldo('ana') == 30,
      saldo('ana'))
A.resolver_indicacao('duda', 'ativacao')
check('e depois a ativação não paga de novo', saldo('ana') == 30, saldo('ana'))


print('\n[5] O teto')
BANCO.clear()
novo('ana')
for i in range(A.REF_TETO):
    novo('ind%d' % i)
    A.registrar_indicacao('ind%d' % i, c1)
    A.resolver_indicacao('ind%d' % i, 'ativacao')
check('os %d primeiros pagaram' % A.REF_TETO,
      saldo('ana') == 10 + A.REF_TETO * A.REF_BONUS_ATIVACAO, saldo('ana'))

novo('extra')
A.registrar_indicacao('extra', c1)
check('o indicado além do teto ainda ganha o dele', saldo('extra') == 20,
      saldo('extra'))
antes = saldo('ana')
A.resolver_indicacao('extra', 'ativacao')
check('mas quem indicou não recebe passado o teto', saldo('ana') == antes,
      saldo('ana'))
A.resolver_indicacao('extra', 'pago')
check('nem quando esse indicado assina', saldo('ana') == antes, saldo('ana'))

# Quem JÁ contou continua valendo: o teto tranca entradas novas, não congela
# quem já está dentro.
antes = saldo('ana')
A.resolver_indicacao('ind0', 'pago')
check('indicado de dentro do teto ainda rende o bônus de assinatura',
      saldo('ana') == antes + A.REF_BONUS_PAGO, saldo('ana'))


print('\n[6] Banco fora do ar não vira crédito')
BANCO.clear()
novo('ana'); novo('bia')
A.registrar_indicacao('bia', c1)
antes = saldo('ana')
QUEBRADO['valor'] = True
A.resolver_indicacao('bia', 'ativacao')          # não pode explodir
QUEBRADO['valor'] = False
check('erro no banco não paga nem quebra', saldo('ana') == antes, saldo('ana'))
check('e a indicação segue pendente, não perdida',
      not BANCO['bia'].get('ref_ativou'), BANCO['bia'])
A.resolver_indicacao('bia', 'ativacao')
check('quando o banco volta, paga normal', saldo('ana') == antes + 5, saldo('ana'))


print('\n[7] O resumo que a tela mostra')
BANCO.clear()
novo('ana')
for i, etapas in enumerate([('ativacao', 'pago'), ('ativacao',), ()]):
    novo('p%d' % i)
    A.registrar_indicacao('p%d' % i, c1)
    for e in etapas:
        A.resolver_indicacao('p%d' % i, e)
r = A.resumo_indicacoes('ana', BANCO['ana'])
check('3 entraram', r['entraram'] == 3, r)
check('2 geraram', r['ativaram'] == 2, r)
check('1 assinou', r['pagaram'] == 1, r)
check('o código vai junto', r['codigo'] == c1, r)
check('e os valores do programa também',
      r['bonusIndicado'] == 10 and r['bonusAtivacao'] == 5 and r['bonusPago'] == 15, r)

print('\n%d passaram · %d falharam' % (ok, fail))
sys.exit(1 if fail else 0)
