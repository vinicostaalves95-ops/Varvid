"""/saude — o que um monitor de disponibilidade enxerga.

Por que este arquivo existe: o Supabase do plano gratuito pausa por inatividade e
o Render pode ficar sem disco. Nos dois casos o usuário vê o app quebrado antes de
o operador saber. /saude é o que um monitor externo consulta — e uma rota de
saúde que responde 200 quando algo está errado é pior que não ter, porque dá
segurança falsa. Aqui se testa o contrário: o que acontece quando as coisas dão
errado, quão rápido isso é dito, e o que NÃO vaza.
"""

import os
import sys
import time
import shutil
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

os.environ['VARVID_DATA'] = '/tmp/vartest/saude'
os.environ['RENDER_BACKEND'] = 'local'
os.environ['VARVID_SWEEPER'] = 'off'
shutil.rmtree('/tmp/vartest/saude', ignore_errors=True)
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


cli = A.app.test_client()
CHAMADAS = []


def zera_cache():
    A._SAUDE_CACHE['resultado'] = None
    A._SAUDE_CACHE['quando'] = 0.0


print("\n[1] Tudo bem: 200")
A.AUTH_ENABLED = True
def _ping_que_conta(prazo=None):
    CHAMADAS.append(1)
    return True


A._sb_ping = _ping_que_conta
A.free_space_mb = lambda: 5000
zera_cache()
r = cli.get('/saude')
check('responde 200', r.status_code == 200, r.status_code)
check('status ok, banco ok, disco ok',
      r.get_json() == {'status': 'ok', 'banco': 'ok', 'disco': 'ok'}, r.get_json())
check('não deixa o navegador guardar a resposta',
      r.headers.get('Cache-Control') == 'no-store', r.headers.get('Cache-Control'))

print("\n[2] Banco fora do ar (Supabase pausado): 503, e sem vazar o erro")
def _banco_caiu(prazo=None):
    raise RuntimeError('HTTP 540 project paused — chave sb_secret_ABC123')

A._sb_ping = _banco_caiu
zera_cache()
r = cli.get('/saude')
check('responde 503', r.status_code == 503, r.status_code)
check('diz que o banco falhou', r.get_json().get('banco') == 'falha', r.get_json())
check('status degradado', r.get_json().get('status') == 'degradado', r.get_json())
check('a mensagem técnica NÃO vai na resposta pública',
      'paused' not in r.get_data(as_text=True) and 'sb_secret' not in r.get_data(as_text=True),
      r.get_data(as_text=True))

print("\n[3] Disco quase cheio: 503")
A._sb_ping = _ping_que_conta
A.free_space_mb = lambda: 40
zera_cache()
r = cli.get('/saude')
check('responde 503', r.status_code == 503, r.status_code)
check('diz que o disco está baixo', r.get_json().get('disco') == 'baixo', r.get_json())
check('não revela quantos MB sobram', '40' not in r.get_data(as_text=True),
      r.get_data(as_text=True))
A.free_space_mb = lambda: 5000

print("\n[4] Rota pública: não pede login e aceita HEAD")
A.AUTH_ENABLED = True
zera_cache()
check('sem cookie nem cabeçalho de login: 200', cli.get('/saude').status_code == 200)
zera_cache()
check('HEAD (usado por alguns monitores) também: 200', cli.head('/saude').status_code == 200)

print("\n[5] Cache: o banco não pode ser martelado por quem chama a rota")
del CHAMADAS[:]
zera_cache()
for _ in range(20):
    cli.get('/saude')
check('20 chamadas seguidas = 1 consulta ao banco', len(CHAMADAS) == 1, len(CHAMADAS))
A._SAUDE_CACHE['quando'] -= A.SAUDE_CACHE_SEG + 1        # o tempo passou
cli.get('/saude')
check('passado o prazo, consulta de novo', len(CHAMADAS) == 2, len(CHAMADAS))

print("\n[6] Modo local (sem banco): não consulta nada")
A.AUTH_ENABLED = False
del CHAMADAS[:]
zera_cache()
r = cli.get('/saude')
check('200', r.status_code == 200, r.status_code)
check('banco marcado como desligado', r.get_json().get('banco') == 'desligado', r.get_json())
check('nenhuma consulta feita', len(CHAMADAS) == 0, len(CHAMADAS))
A.AUTH_ENABLED = True

print("\n[7] O _sb_ping de verdade, contra um servidor de mentira")
# Aqui NÃO se troca o _sb_ping: o que importa é ele mesmo — uma tentativa só,
# prazo curto, e erro quando o banco responde mal.
PINGS = []
MODO = {'valor': 200, 'atraso': 0}


class Falso(BaseHTTPRequestHandler):
    def do_GET(self):
        PINGS.append(self.path)
        time.sleep(MODO['atraso'])
        try:
            self.send_response(MODO['valor'])
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(b'[]')
        except (BrokenPipeError, ConnectionResetError):
            pass                       # o cliente desistiu — é o que o teste provoca

    def log_message(self, *a):
        pass


srv = HTTPServer(('127.0.0.1', 0), Falso)
threading.Thread(target=srv.serve_forever, daemon=True).start()

# recarrega só a função original a partir do arquivo, já que a substituímos acima
ns = {}
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'local_app.py')).read()
ini = src.index('def _sb_ping(')
fim = src.index('def verificar_saude(')
exec('import urllib.request\n' + src[ini:fim], {
    'urllib': __import__('urllib'), 'SUPABASE_SERVICE_KEY': 'k', 'SUPABASE_ANON_KEY': 'a',
    'SUPABASE_URL': 'http://127.0.0.1:%d' % srv.server_port, 'SAUDE_PRAZO_BANCO': 1.0}, ns)
ping_real = ns['_sb_ping']

check('banco respondendo 200: passa', ping_real() is True)
check('consulta a tabela profiles, pedindo uma linha só',
      PINGS and 'profiles' in PINGS[0] and 'limit=1' in PINGS[0], PINGS)

MODO['valor'] = 540                                      # o que um projeto pausado devolve
del PINGS[:]
try:
    ping_real()
    levantou = False
except Exception:
    levantou = True
check('resposta de erro do banco levanta exceção', levantou)
check('e tenta UMA vez só (nada de retentativa que atrase o alarme)', len(PINGS) == 1, len(PINGS))

MODO['valor'] = 200
MODO['atraso'] = 3                                       # banco pendurado
del PINGS[:]
t0 = time.time()
try:
    ping_real()
    levantou = False
except Exception:
    levantou = True
dt = time.time() - t0
check('banco pendurado: desiste no prazo (1 s no teste)', levantou and dt < 2.5, round(dt, 2))
srv.shutdown()

print("\n%d passaram · %d falharam" % (ok, fail))
sys.exit(1 if fail else 0)
