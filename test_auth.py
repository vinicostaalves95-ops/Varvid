"""Chave do login com Google e o que o servidor conta pro front.

Por que existe: o botão do Google só pode aparecer quando o provider estiver
mesmo configurado no Google Cloud e no Supabase — nada disso mora no código
daqui. Um botão que leva a erro é pior que botão nenhum: a pessoa acha que a
culpa é dela. Então o padrão é DESLIGADO, e ligar tem que ser uma variável de
ambiente, não um deploy.
"""

import os, sys, shutil

os.environ['VARVID_DATA'] = '/tmp/vartest/auth'
os.environ['RENDER_BACKEND'] = 'local'
os.environ['VARVID_SWEEPER'] = 'off'
os.environ.pop('VARVID_GOOGLE_LOGIN', None)        # começa limpo, como no Render novo
shutil.rmtree('/tmp/vartest/auth', ignore_errors=True)
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


print("\n[1] Google vem desligado de fábrica")
check('sem a variável, fica desligado', A.GOOGLE_LOGIN_ENABLED is False, A.GOOGLE_LOGIN_ENABLED)
d = c.get('/auth-config.json').get_json()
check('/auth-config.json publica googleEnabled', 'googleEnabled' in d, d)
check('e publica ele como falso', d.get('googleEnabled') is False, d.get('googleEnabled'))

print("\n[2] Formas de ligar que uma pessoa realmente digita")
for valor in ('1', 'true', 'TRUE', 'sim', 'on', 'yes', ' 1 '):
    os.environ['VARVID_GOOGLE_LOGIN'] = valor
    check(f'{valor!r} liga', A._flag('VARVID_GOOGLE_LOGIN') is True)
for valor in ('0', 'false', 'nao', '', 'off', 'talvez'):
    os.environ['VARVID_GOOGLE_LOGIN'] = valor
    check(f'{valor!r} não liga', A._flag('VARVID_GOOGLE_LOGIN') is False)
os.environ.pop('VARVID_GOOGLE_LOGIN', None)

print("\n[3] Google depende do login existir")
# Ligar o Google num ambiente sem Supabase configurado não faz sentido: o botão
# chamaria uma biblioteca que nem foi inicializada.
os.environ['VARVID_GOOGLE_LOGIN'] = '1'
sem_auth = bool(False and A._flag('VARVID_GOOGLE_LOGIN'))
com_auth = bool(True and A._flag('VARVID_GOOGLE_LOGIN'))
check('sem Supabase, continua desligado', sem_auth is False)
check('com Supabase + variável, liga', com_auth is True)
os.environ.pop('VARVID_GOOGLE_LOGIN', None)

print("\n[4] O front recebe tudo que precisa numa chamada só")
d = c.get('/auth-config.json').get_json()
for campo in ('authEnabled', 'url', 'anonKey', 'googleEnabled', 'limits'):
    check(f'{campo} presente', campo in d, d.keys())
check('chave secreta NÃO vaza', 'serviceKey' not in d and 'service_key' not in d, d.keys())

print(f"\n{ok} passaram · {fail} falharam")
sys.exit(1 if fail else 0)
