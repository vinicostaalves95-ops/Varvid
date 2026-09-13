"""Prova que o contador de duração aparece SEM o ffprobe — ou seja, em produção.

Este bug só existia no ar: na máquina do desenvolvedor o ffprobe está instalado,
o servidor media certo e o contador aparecia. No Render não existe ffprobe (de
propósito — lá é só o coordenador), a medição voltava 0 e o número sumia.

Então aqui o servidor sobe com a medição do servidor FORÇADA a zero, que é
exatamente o que o Render devolve. Se o contador aparecer assim, aparece lá.

Uso:  python3 previa_duracao.py
"""

import os
import sys
import asyncio
import threading

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)

os.environ['VARVID_DATA'] = '/tmp/vartest/dur'
os.environ['RENDER_BACKEND'] = 'local'
os.environ['VARVID_SWEEPER'] = 'off'

from test_fixtures import garantir_takes            # noqa: E402
import local_app as A                               # noqa: E402

PORTA = 5199


def takes_legiveis(pasta):
    """Gera os takes em WebM/VP8.

    O Chromium deste ambiente não vem com H.264 — `canPlayType('avc1…')`
    devolve vazio. Não é defeito do VarVid: Chrome, Safari e Edge de verdade
    leem MP4 e MOV sem drama, que é o que sai de qualquer celular. Mas aqui,
    com MP4, o teste mediria a falta de codec em vez de medir o código.
    Em VP8 o navegador lê, e o que queremos provar — servidor mudo, navegador
    medindo, contador na tela — fica exercitado do mesmo jeito.
    """
    import subprocess
    nomes = ['Hook1.webm', 'Hook2.webm', 'Story1.webm', 'CTA1.webm', 'CTA2.webm']
    saida = os.path.join(pasta, 'webm')
    os.makedirs(saida, exist_ok=True)
    feitos = []
    for i, nome in enumerate(nomes):
        destino = os.path.join(saida, nome)
        if not os.path.exists(destino):
            dur = 2 + i          # durações diferentes: o pior caso tem que ser visível
            subprocess.run([
                'ffmpeg', '-y', '-loglevel', 'error',
                '-f', 'lavfi', '-i', 'testsrc=size=360x640:rate=24:duration=%d' % dur,
                '-c:v', 'libvpx', '-b:v', '300k', destino,
            ], check=True, capture_output=True)
        feitos.append(destino)
    return feitos


def main():
    pasta = garantir_takes()
    A.AUTH_ENABLED = False
    A.CREDITS_ENABLED = False
    A.STRIPE_ENABLED = False

    # ── O CORAÇÃO DESTE TESTE ────────────────────────────────────────────────
    # É isto que o Render faz hoje: sem ffprobe, get_duration devolve 0.0.
    A.get_duration = lambda caminho: 0.0

    servidor = threading.Thread(
        target=lambda: A.app.run(port=PORTA, debug=False, use_reloader=False),
        daemon=True)
    servidor.start()

    import time
    time.sleep(2)

    asyncio.run(olhar(pasta))


async def olhar(pasta):
    from playwright.async_api import async_playwright

    takes = takes_legiveis(pasta)

    async with async_playwright() as p:
        nav = await p.chromium.launch(
            executable_path='/opt/pw-browsers/chromium-1194/chrome-linux/chrome')
        pag = await nav.new_page(viewport={'width': 1280, 'height': 900},
                                 device_scale_factor=2)
        erros = []
        pag.on('console', lambda m: erros.append(m.text) if m.type == 'error' else None)

        await pag.goto('http://127.0.0.1:%d/' % PORTA)
        await pag.wait_for_function('typeof duracaoMontada === "function"')

        await pag.set_input_files('#file', takes)
        # Espera o /analyze responder e a linha de duração se decidir.
        await pag.wait_for_function(
            "document.getElementById('dur-line').className.indexOf('show') !== -1",
            timeout=20000)
        await pag.wait_for_timeout(300)

        texto = (await pag.inner_text('#dur-line')).replace('\n', ' · ')
        medido = await pag.evaluate('DURACOES.size')
        doServidor = await pag.evaluate(
            "(()=>{try{return Object.values(window.__ultimoSummary||{}).length}catch(e){return -1}})()")

        os.makedirs(os.path.join(BASE, 'previa'), exist_ok=True)
        destino = os.path.join(BASE, 'previa', 'duracao-sem-ffprobe.png')
        await pag.screenshot(path=destino)

        print('')
        print('  servidor mediu ..... 0.0s (forçado, como no Render)')
        print('  navegador mediu .... %d take(s)' % medido)
        print('  na tela ............ %s' % (texto or '(nada)'))
        print('  foto ............... %s' % destino)
        if erros:
            print('  erros no console ... %s' % erros[:3])
        print('')
        ok = bool(texto.strip()) and medido == 5
        print('  RESULTADO: %s' % ('contador aparece sem ffprobe ✓' if ok
                                   else 'FALHOU — o contador não apareceu'))
        await nav.close()
        sys.exit(0 if ok else 1)


main()
