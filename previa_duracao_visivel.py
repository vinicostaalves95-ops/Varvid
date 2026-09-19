"""Onde o contador de duração CABE na tela — e se ele aparece nos dois modos.

O contador funciona (previa_duracao.py prova isso). A pergunta aqui é outra:
quando ele aparece, a pessoa consegue vê-lo sem rolar a página?

Ele mora embaixo do botão GERAR, no fim da coluna da esquerda. Em tela de
1280x900 isso ainda cabe. Em notebook comum — onde sobram uns 700px de área
útil depois de abas, barra de endereço e dock — não cabe: o número é desenhado
fora do campo de visão, e o usuário jura que a funcionalidade não existe.

Uso:  python3 previa_duracao_visivel.py
"""

import os
import sys
import asyncio
import threading
import subprocess

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)

os.environ['VARVID_DATA'] = '/tmp/vartest/durvis'
os.environ['RENDER_BACKEND'] = 'local'
os.environ['VARVID_SWEEPER'] = 'off'

import local_app as A                               # noqa: E402

PORTA = 5202
CHROME = '/opt/pw-browsers/chromium-1194/chrome-linux/chrome'

# Telas reais, em área ÚTIL do navegador (já descontadas abas e barra de
# endereço) — não em resolução de monitor, que é o número que engana.
TELAS = [
    ('MacBook Air 13" ....', 1440, 700),
    ('notebook 1366x768 ..', 1366, 610),
    ('monitor 1080p ......', 1920, 880),
]


def takes(pasta, especificacoes):
    os.makedirs(pasta, exist_ok=True)
    feitos = []
    for nome, dur in especificacoes:
        destino = os.path.join(pasta, nome)
        if not os.path.exists(destino):
            subprocess.run([
                'ffmpeg', '-y', '-loglevel', 'error',
                '-f', 'lavfi', '-i',
                'testsrc=size=360x640:rate=24:duration=%d' % dur,
                '-c:v', 'libvpx', '-b:v', '300k', destino,
            ], check=True, capture_output=True)
        feitos.append(destino)
    return feitos


def main():
    A.AUTH_ENABLED = False
    A.CREDITS_ENABLED = False
    A.STRIPE_ENABLED = False
    A.get_duration = lambda caminho: 0.0      # é o que o Render devolve

    threading.Thread(
        target=lambda: A.app.run(port=PORTA, debug=False, use_reloader=False),
        daemon=True).start()
    import time
    time.sleep(2)
    sys.exit(asyncio.run(rodar()))


async def geometria(pag):
    """Onde a linha do contador está, e se está dentro da janela."""
    return await pag.evaluate("""() => {
      const el = document.getElementById('dur-line');
      const r  = el.getBoundingClientRect();
      const visivel = getComputedStyle(el).display !== 'none';
      return {visivel, topo: Math.round(r.top), fundo: Math.round(r.bottom),
              janela: window.innerHeight,
              texto: (el.innerText||'').replace(/\\n/g,' · ')};
    }""")


async def rodar():
    from playwright.async_api import async_playwright

    pasta = '/tmp/vartest/webm'
    remix = takes(pasta, [('Hook1.webm', 2), ('Hook2.webm', 3),
                          ('Story1.webm', 4), ('CTA1.webm', 5)])
    unico = takes(pasta, [('pronto.webm', 6)])

    falhas = []
    async with async_playwright() as p:
        nav = await p.chromium.launch(executable_path=CHROME)

        for rotulo, larg, alt in TELAS:
            pag = await nav.new_page(viewport={'width': larg, 'height': alt})
            await pag.goto('http://127.0.0.1:%d/' % PORTA)
            await pag.wait_for_function('typeof duracaoMontada === "function"')
            await pag.set_input_files('#file', remix)
            await pag.wait_for_function(
                "document.getElementById('dur-line').className.includes('show')",
                timeout=20000)
            g = await geometria(pag)
            cabe = g['fundo'] <= g['janela']
            print('  %s %s  linha em y=%d..%d · janela %dpx → %s'
                  % (rotulo, 'remix', g['topo'], g['fundo'], g['janela'],
                     'VISÍVEL' if cabe else 'FORA DA TELA (precisa rolar)'))
            if not cabe:
                falhas.append('%s (remix)' % rotulo.strip(' .'))
            await pag.close()

    # ── os dois modos, numa tela grande, só pra confirmar que ambos calculam ──
        pag = await nav.new_page(viewport={'width': 1440, 'height': 1000})
        await pag.goto('http://127.0.0.1:%d/' % PORTA)
        await pag.wait_for_function('typeof duracaoMontada === "function"')

        print('')
        await pag.set_input_files('#file', remix)
        await pag.wait_for_function(
            "document.getElementById('dur-line').className.includes('show')",
            timeout=20000)
        g = await geometria(pag)
        print('  remix de takes ..... %s' % (g['texto'] or '(nada)'))
        if not g['texto'].strip():
            falhas.append('remix não calculou')

        # modo único
        await pag.evaluate("setMode('single')")
        await pag.set_input_files('#file', unico)
        await pag.wait_for_function(
            "document.getElementById('dur-line').className.includes('show')",
            timeout=20000)
        g = await geometria(pag)
        print('  vídeo único ........ %s' % (g['texto'] or '(nada)'))
        if not g['texto'].strip():
            falhas.append('único não calculou')

        # estouro do limite: baixa o teto para 5s e sobe o vídeo de 6s
        await pag.evaluate("LIM.maxVideoSeconds = 5")
        await pag.evaluate("clearAll()")
        await pag.set_input_files('#file', unico)
        await pag.wait_for_function(
            "document.getElementById('dur-line').className.includes('over')",
            timeout=20000)
        g = await geometria(pag)
        bloqueou = await pag.evaluate("document.getElementById('go').disabled")
        print('  acima do limite .... %s → GERAR %s'
              % (g['texto'] or '(nada)', 'bloqueado' if bloqueou else 'LIBERADO (erro)'))
        if not bloqueou:
            falhas.append('não bloqueou acima do limite')

        # arquivo que o navegador não sabe ler → some sem avisar
        await pag.evaluate("clearAll()")
        ilegivel = '/tmp/vartest/webm/quebrado.webm'
        open(ilegivel, 'wb').write(b'nao sou um video' * 200)
        await pag.set_input_files('#file', [ilegivel])
        await pag.wait_for_timeout(9000)     # o lerDuracao desiste em 8s
        g = await geometria(pag)
        print('  codec ilegível ..... linha %s · texto: %s'
              % ('escondida' if not g['visivel'] else 'visível',
                 g['texto'] or '(nada)'))

        await nav.close()

    print('')
    if falhas:
        print('  RESULTADO: %s' % ' | '.join(falhas))
        return 1
    print('  RESULTADO: contador correto nos dois modos e visível em todas as telas ✓')
    return 0


main()
