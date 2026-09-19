"""Roda o VarVid com o LAYOUT ESCURO, sem trocar nada na pasta.

  python3 previa_escuro.py          → http://localhost:5001
  python3 previa_escuro.py 5050     → outra porta, se a 5001 estiver ocupada

O app lê `app.html` e `login.html` de BASE_DIR. Em vez de copiar os arquivos
escuros por cima — que deixaria a pasta num estado que ninguém lembra depois —
este script monta uma pasta temporária com eles dentro e aponta o BASE_DIR pra
lá, só enquanto roda. Os arquivos de produção não são tocados.

O resto é o app de verdade: mesmo servidor, mesmo Supabase, mesmos créditos.
Se você tem `supabase_config.json` na pasta, o login funciona igual ao do ar.
"""

import os
import sys
import shutil
import tempfile

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)

PORTA = int(sys.argv[1]) if len(sys.argv) > 1 else 5001

ESCURO = os.path.join(BASE, 'design', 'versao-escura')
PARES = [('app-escuro.html', 'app.html'),
         ('login-escuro.html', 'login.html')]

faltando = [o for o, _ in PARES if not os.path.exists(os.path.join(ESCURO, o))]
if faltando:
    print('Não achei em design/versao-escura/: %s' % ', '.join(faltando))
    sys.exit(1)

# Jobs do preview em pasta própria: não mistura com o que você já tem local.
os.environ.setdefault('VARVID_DATA', os.path.join(BASE, 'data', 'varvid-escuro'))

import local_app as A                                  # noqa: E402

pasta = tempfile.mkdtemp(prefix='varvid-escuro-')
for origem, destino in PARES:
    shutil.copy(os.path.join(ESCURO, origem), os.path.join(pasta, destino))
# /termos, /privacidade, /como-funciona, /roteiro — páginas que não mudam
# com o tema, mas que precisam existir na pasta pro preview servi-las.
for extra in ('legal.html', 'ui.html', 'como_funciona.html', 'roteiro.html'):
    caminho = os.path.join(BASE, extra)
    if os.path.exists(caminho):
        shutil.copy(caminho, os.path.join(pasta, extra))

# Só as telas mudam de lugar. O supabase_config.json já foi lido no import,
# com o BASE_DIR de verdade — então login e créditos seguem os mesmos.
A.BASE_DIR = pasta

print('')
print('  ╭────────────────────────────────────────────────╮')
print('  │  VarVid · LAYOUT ESCURO (preview)              │')
print('  ╰────────────────────────────────────────────────╯')
print('')
print('     abra:  http://localhost:%d' % PORTA)
print('')
print('     login ...... %s' % ('Supabase (igual ao do ar)' if A.AUTH_ENABLED
                                else 'desligado (sem supabase_config.json)'))
print('     créditos ... %s' % ('ligados' if A.CREDITS_ENABLED else 'desligados'))
print('     render ..... %s' % A.RENDER_BACKEND)
print('     telas de ... %s' % pasta)
print('')
print('     app.html e login.html da pasta do projeto: INTOCADOS')
print('     Ctrl+C para parar.')
print('')

try:
    A.app.run(port=PORTA, debug=False, use_reloader=False)
except OSError as e:
    if getattr(e, 'errno', None) in (48, 98):          # address already in use
        print('')
        print('  A porta %d já está ocupada.' % PORTA)
        if PORTA in (5000, 5001):
            print('')
            print('  No macOS essas duas portas costumam ser do "Receptor AirPlay".')
            print('  Ou desligue em Ajustes do Sistema → Geral → AirDrop e Handoff,')
            print('  ou rode em outra porta:')
            print('')
            print('      python3 previa_escuro.py 5050')
        print('')
        sys.exit(1)
    raise
finally:
    shutil.rmtree(pasta, ignore_errors=True)
