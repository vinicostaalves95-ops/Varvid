"""Nenhuma credencial pode ir para o repositório — e este teste impede, sozinho.

Por que este arquivo existe: o repositório do VarVid é PÚBLICO. Em 25/09 uma
varredura encontrou o par de credenciais do Modal escrito em server.py como valor
padrão de variável de ambiente, e a nota de 14/09 já dizia que elas estavam em
62 dos 93 commits desde maio. Ninguém "esqueceu de olhar": era o tipo de coisa que
só aparece quando alguém decide procurar. Depender disso é o problema.

Aqui a procura é automática. Roda em toda publicação (subir.sh, primeiro da lista)
e reprova se achar:

  · chaves do Stripe (sk_/rk_ e whsec_), do Supabase (sb_secret_ e JWT com role
    service_role) e do Modal (ak-/as-), chaves AWS e blocos de chave privada;
  · atribuição de valor longo a nomes como SECRET/TOKEN/PASSWORD/API_KEY, inclusive
    como valor padrão de os.environ.get/setdefault (o caso do server.py);
  · .gitignore sem supabase_config.json e .env, ou esses arquivos já rastreados
    pelo git (rastrear depois de ignorar não desfaz nada: o arquivo continua lá).

A chave PÚBLICA do Supabase (anon, sb_publishable_) é feita para ir no navegador e
não é reprovada. Nenhum valor é impresso: só arquivo, linha, tipo e 4 caracteres.

Linha que precisa mesmo conter um valor de mentira (fixture de teste) pode ter o
comentário  `# segredo-ok: motivo`  no fim.

Uso:
  python3 test_segredos.py                 varre o projeto (é o que o subir.sh roda)
  python3 test_segredos.py --historico     varre TODO o histórico do git (só o que
                                           foi ADICIONADO em algum commit) e conta
                                           quantas credenciais distintas vazaram
  python3 test_segredos.py --raiz PASTA    varre outra pasta
"""

import os
import re
import sys
import json
import base64
import hashlib
import subprocess

RAIZ = os.path.dirname(os.path.abspath(__file__))
if '--raiz' in sys.argv:
    RAIZ = os.path.abspath(sys.argv[sys.argv.index('--raiz') + 1])

IGNORAR_DIRS = {'.git', '.venv', 'venv', '__pycache__', 'node_modules', 'data',
                'previa', '.pytest_cache'}
IGNORAR_ARQ = {'supabase_config.json', '.env', '.entregue.sha', '.modal-publicado',
               '.DS_Store'}
EXT_BINARIA = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.ico', '.mp4', '.mov',
               '.webm', '.mp3', '.wav', '.woff', '.woff2', '.ttf', '.otf', '.pdf',
               '.zip', '.gz', '.pyc'}
TAMANHO_MAX = 8 * 1024 * 1024

# (nome, regex). Cada regex tem UM grupo: o valor que se mascara.
REGRAS = [
    ('Stripe secret key', re.compile(r'\b((?:sk|rk)_(?:live|test)_[A-Za-z0-9]{16,})')),
    ('Stripe webhook secret', re.compile(r'\b(whsec_[A-Za-z0-9]{16,})')),
    ('Supabase secret key', re.compile(r'\b(sb_secret_[A-Za-z0-9_-]{16,})')),
    ('Modal token id', re.compile(r'\b(ak-[A-Za-z0-9]{16,})')),
    ('Modal token secret', re.compile(r'\b(as-[A-Za-z0-9]{16,})')),
    ('AWS access key', re.compile(r'\b(AKIA[0-9A-Z]{16})\b')),
    ('chave privada', re.compile(r'(-----BEGIN [A-Z ]*PRIVATE KEY-----)')),
    ('valor padrão de variável secreta',
     re.compile(r'''os\.environ\.(?:get|setdefault)\(\s*['"][A-Za-z0-9_]*'''
                r'''(?:SECRET|TOKEN|PASSWORD|PASSWD|API_?KEY|ACCESS_?KEY|SERVICE_?KEY)'''
                r'''[A-Za-z0-9_]*['"]\s*,\s*['"]([^'"\s]{12,})['"]''', re.I)),
    ('atribuição de valor secreto',
     re.compile(r'''(?:secret|token|password|passwd|api_?key|access_?key|service_?key)'''
                r'''[A-Za-z0-9_]*['"]?\s*[:=]\s*['"]([A-Za-z0-9_\-+/=.]{20,})['"]''', re.I)),
]
JWT = re.compile(r'\b(eyJ[A-Za-z0-9_-]{10,}\.(eyJ[A-Za-z0-9_-]{10,})\.[A-Za-z0-9_-]{10,})')
MARCADORES_DE_MENTIRA = ('xxx', 'example', 'exemplo', 'seu_', 'sua_', 'your', 'change',
                         'troque', 'placeholder', 'sample', 'dummy', 'fake', '...',
                         '***', '<', '{{', '${', 'process.env', 'os.environ')
LIBERADO = re.compile(r'#\s*segredo-ok')


def mascarar(valor):
    return valor[:4] + '…(%d caracteres)' % len(valor)


def eh_de_mentira(valor):
    v = valor.lower()
    if any(m in v for m in MARCADORES_DE_MENTIRA):
        return True
    return len(set(valor)) <= 3                      # 'aaaaaaaa…', '00000000…'


def papel_do_jwt(carga_b64):
    """O campo `role` dentro de um JWT do Supabase (anon | service_role)."""
    try:
        bruto = base64.urlsafe_b64decode(carga_b64 + '=' * (-len(carga_b64) % 4))
        return json.loads(bruto).get('role')
    except Exception:
        return None


def achados_na_linha(linha):
    """[(tipo, valor)] — o que na linha parece credencial de verdade."""
    if LIBERADO.search(linha):
        return []
    achou = []
    for nome, rx in REGRAS:
        for m in rx.finditer(linha):
            valor = m.group(1)
            if eh_de_mentira(valor):                  # 'sk_live_xxxx…', 'seu_token_aqui'
                continue
            achou.append((nome, valor))
    for m in JWT.finditer(linha):
        papel = papel_do_jwt(m.group(2))
        if papel == 'anon':
            continue                                  # pública por desenho
        achou.append(('JWT do Supabase com role=%s' % (papel or 'desconhecido'), m.group(1)))
    # uma linha pode casar duas regras com o mesmo valor: conta uma vez
    vistos, unicos = set(), []
    for nome, valor in achou:
        if valor not in vistos:
            vistos.add(valor)
            unicos.append((nome, valor))
    return unicos


# ── que arquivos varrer ──────────────────────────────────────────────────────

def _git(*args):
    try:
        return subprocess.run(['git', '-C', RAIZ] + list(args), capture_output=True,
                              text=True, timeout=120)
    except Exception:
        return None


def em_repositorio_git():
    r = _git('rev-parse', '--is-inside-work-tree')
    return bool(r and r.returncode == 0 and r.stdout.strip() == 'true')


def arquivos_a_varrer():
    """Com git: exatamente o que o git publicaria (respeita o .gitignore).
    Sem git: caminha pela pasta pulando o que o .gitignore do projeto ignora."""
    if em_repositorio_git():
        r = _git('ls-files', '--cached', '--others', '--exclude-standard', '-z')
        nomes = [n for n in (r.stdout.split('\0') if r else []) if n]
        caminhos = [os.path.join(RAIZ, n) for n in nomes]
        modo = 'git'
    else:
        caminhos = []
        for pasta, dirs, arqs in os.walk(RAIZ):
            dirs[:] = [d for d in dirs if d not in IGNORAR_DIRS]
            for a in arqs:
                if a not in IGNORAR_ARQ:
                    caminhos.append(os.path.join(pasta, a))
        modo = 'pasta'
    saida = []
    for c in caminhos:
        if not os.path.isfile(c) or os.path.splitext(c)[1].lower() in EXT_BINARIA:
            continue
        try:
            if os.path.getsize(c) > TAMANHO_MAX:
                continue
        except OSError:
            continue
        saida.append(c)
    return sorted(saida), modo


def varrer_arquivos():
    arquivos, modo = arquivos_a_varrer()
    achados = []
    for c in arquivos:
        try:
            with open(c, encoding='utf-8', errors='ignore') as f:
                for n, linha in enumerate(f, 1):
                    for tipo, valor in achados_na_linha(linha):
                        achados.append((os.path.relpath(c, RAIZ), n, tipo, valor))
        except OSError:
            pass
    return achados, len(arquivos), modo


# ── histórico do git ─────────────────────────────────────────────────────────

def varrer_historico():
    """Só linhas ADICIONADAS em algum commit — é o que ficou público."""
    p = subprocess.Popen(['git', '-C', RAIZ, 'log', '--all', '-p', '--no-color',
                          '--no-ext-diff', '--format=commit %H'],
                         stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                         text=True, errors='ignore')
    commit = arquivo = None
    n_commits = 0
    por_valor = {}                       # hash do valor -> {tipo, arquivos, commits}
    for linha in p.stdout:
        if linha.startswith('commit '):
            commit = linha.split()[1][:8]
            n_commits += 1
        elif linha.startswith('+++ b/'):
            arquivo = linha[6:].strip()
        elif linha.startswith('+') and not linha.startswith('+++'):
            if len(linha) > 4000:                    # linha minificada gigante
                continue
            for tipo, valor in achados_na_linha(linha[1:]):
                h = hashlib.sha256(valor.encode()).hexdigest()[:10]
                d = por_valor.setdefault(h, {'tipo': tipo, 'mascara': mascarar(valor),
                                             'arquivos': set(), 'commits': set()})
                d['arquivos'].add(arquivo)
                d['commits'].add(commit)
    p.wait()
    return n_commits, por_valor


def modo_historico():
    if not em_repositorio_git():
        print('Esta pasta não é um repositório git. Rode dentro de ~/Projetos/varvid.')
        return 2
    n, achados = varrer_historico()
    print('Histórico varrido: %d commits.' % n)
    if not achados:
        print('✓ nenhuma credencial encontrada nas linhas adicionadas.')
        return 0
    print('❌ %d credencial(is) DISTINTA(S) apareceram no histórico:\n' % len(achados))
    for h, d in sorted(achados.items(), key=lambda kv: -len(kv[1]['commits'])):
        print('  · %-38s %s' % (d['tipo'], d['mascara']))
        print('      em %d commit(s), arquivo(s): %s' % (len(d['commits']),
                                                         ', '.join(sorted(d['arquivos']))))
    print('\nApagar do código NÃO remove do histórico. O que resolve é REVOGAR cada')
    print('credencial acima e criar uma nova (Modal: API Tokens; Stripe: Developers →')
    print('API keys → Roll key; Supabase: Settings → API). Reescrever o histórico é')
    print('opcional e só faz sentido depois de revogar.')
    return 1


# ── o teste ──────────────────────────────────────────────────────────────────

ok = fail = 0


def check(n, cond, extra=''):
    global ok, fail
    if cond:
        ok += 1
        print('  ✓ %s' % n)
    else:
        fail += 1
        print('  ✗ %s %s' % (n, extra))


def principal():
    print('\n[1] O detector funciona (senão "nenhum achado" não vale nada)')
    # Os exemplos são montados por partes para este arquivo não se reprovar sozinho.
    falsa = lambda *p: ''.join(p)
    casos = [
        ('Stripe secret key', 'k = "' + falsa('sk_', 'live_', 'A1b2C3d4E5f6G7h8I9j0K1l2') + '"'),
        ('Stripe secret key', 'k = "' + falsa('rk_', 'test_', 'A1b2C3d4E5f6G7h8I9j0K1l2') + '"'),
        ('Stripe webhook secret', falsa('wh', 'sec_', 'A1b2C3d4E5f6G7h8I9j0K1l2m3')),
        ('Supabase secret key', falsa('sb_', 'secret_', 'A1b2C3d4E5f6G7h8I9j0')),
        ('Modal token id', falsa('a', 'k-', 'A1b2C3d4E5f6G7h8I9j0K1')),
        ('Modal token secret', falsa('a', 's-', 'A1b2C3d4E5f6G7h8I9j0K1')),
        ('AWS access key', falsa('AK', 'IA', 'ABCDEFGHIJKLMNOP')),
        ('chave privada', falsa('-----BEGIN RSA ', 'PRIVATE KEY-----')),
        ('valor padrão de variável secreta',
         "os.environ.setdefault('MODAL_TOKEN_SECRET', '" + falsa('tok', 'en-real-de-verdade-9f8e7d') + "')"),
        ('atribuição de valor secreto',
         'R2_SECRET_ACCESS_KEY = "' + falsa('9f8e7d6c5b4a', '39281706f5e4d3c2b1a0') + '"'),
    ]
    for esperado, linha in casos:
        tipos = [t for t, _ in achados_na_linha(linha)]
        check('detecta: %s' % esperado, esperado in tipos, tipos)

    def jwt(role):
        cab = base64.urlsafe_b64encode(b'{"alg":"HS256","typ":"JWT"}').decode().rstrip('=')
        car = base64.urlsafe_b64encode(json.dumps({'role': role, 'iss': 'supabase'}).encode()).decode().rstrip('=')
        return cab + '.' + car + '.' + 'assinaturaassinatura123'

    check('JWT service_role é reprovado',
          any('service_role' in t for t, _ in achados_na_linha('KEY="' + jwt('service_role') + '"')))
    check('JWT anon (chave pública do navegador) NÃO é reprovado',
          not achados_na_linha('KEY="' + jwt('anon') + '"'))

    print('\n[2] O detector não grita à toa')
    check('placeholder de exemplo passa',
          not achados_na_linha('STRIPE_KEY = "' + falsa('sk_', 'live_', 'x' * 24) + '"')
          and not achados_na_linha("os.environ.get('MODAL_TOKEN_ID', 'seu_token_aqui_1234')"))
    check('leitura de variável de ambiente sem valor padrão passa',
          not achados_na_linha("os.environ.get('MODAL_TOKEN_ID')")
          and not achados_na_linha("SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET', '')"))
    check('a marca # segredo-ok libera a linha',
          not achados_na_linha('k = "' + falsa('sk_', 'test_', 'A1b2C3d4E5f6G7h8I9j0K1l2')
                               + '"  # segredo-ok: fixture'))
    check('texto comum e CSS não disparam',
          not achados_na_linha('.task-list-item{color:#fff} // as-is, ak-47 is a rifle')
          and not achados_na_linha('token = request.args.get("token", "")'))

    print('\n[3] O relatório nunca imprime o segredo')
    valor = falsa('sk_', 'live_', 'A1b2C3d4E5f6G7h8I9j0K1l2')
    check('máscara não contém o valor', valor not in mascarar(valor) and len(mascarar(valor)) < len(valor) + 20,
          mascarar(valor))

    print('\n[4] O projeto de verdade')
    achados, n, modo = varrer_arquivos()
    print('     (%d arquivos varridos, modo: %s)' % (n, modo))
    check('há arquivos varridos (a varredura não ficou cega)', n >= 5, n)
    for arq, lin, tipo, val in achados:
        print('     ! %s:%d  %s  %s' % (arq, lin, tipo, mascarar(val)))
    check('nenhuma credencial nos arquivos do projeto', not achados,
          '%d achado(s) — acima' % len(achados))

    print('\n[5] O que protege o arquivo de chaves')
    gi = os.path.join(RAIZ, '.gitignore')
    conteudo = open(gi).read().split() if os.path.exists(gi) else []
    check('.gitignore existe e ignora supabase_config.json', 'supabase_config.json' in conteudo)
    check('.gitignore ignora .env', '.env' in conteudo)
    if em_repositorio_git():
        for nome in ('supabase_config.json', '.env'):
            r = _git('ls-files', '--', nome)
            check('%s NÃO está rastreado pelo git' % nome, r is not None and r.stdout.strip() == '',
                  'rastreado: git rm --cached %s' % nome)
    else:
        print('     (sem git nesta pasta: a checagem de "rastreado" roda só na máquina do Vinícius)')

    print('\n%d passaram · %d falharam' % (ok, fail))
    return 1 if fail else 0


if __name__ == '__main__':
    sys.exit(modo_historico() if '--historico' in sys.argv else principal())
