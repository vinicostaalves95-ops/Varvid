"""Vídeos de exemplo para os testes.

Os testes precisam de uns takes de verdade (com áudio, vídeo e duração) para
exercitar o ffmpeg. Em vez de versionar arquivos binários no repositório, eles
são gerados na hora — ficam idênticos em qualquer máquina e não sujam o Git.

Chamado no início de cada teste que precisa de arquivos. Se já existirem, não
faz nada; se faltar ffmpeg, avisa e o teste que chamou decide o que fazer.
"""

import os
import subprocess

PASTA = os.environ.get('VARVID_TEST_MEDIA', '/tmp/vartest/e2e')

# Nomes escolhidos para o parser reconhecer os blocos: 2 hooks × 2 ctas = 4
# combinações, com um story fixo no meio.
TAKES = ['Hook1.mp4', 'Hook2.mp4', 'Story1.mp4', 'CTA1.mp4', 'CTA2.mp4']


def tem_ffmpeg():
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        return True
    except Exception:
        return False


def garantir_takes(duracao=2):
    """Cria os vídeos de exemplo se faltarem. Devolve a pasta.

    Levanta RuntimeError se não houver ffmpeg — melhor falhar dizendo o motivo
    do que o teste quebrar depois com 'arquivo não encontrado'.
    """
    os.makedirs(PASTA, exist_ok=True)
    faltando = [n for n in TAKES if not os.path.exists(os.path.join(PASTA, n))]
    if not faltando:
        return PASTA
    if not tem_ffmpeg():
        raise RuntimeError(
            'ffmpeg não encontrado — necessário para gerar os vídeos de teste. '
            'No macOS: brew install ffmpeg')
    for nome in faltando:
        destino = os.path.join(PASTA, nome)
        subprocess.run([
            'ffmpeg', '-y', '-loglevel', 'error',
            '-f', 'lavfi', '-i', 'testsrc=size=540x960:rate=30:duration=%d' % duracao,
            '-f', 'lavfi', '-i', 'sine=frequency=440:duration=%d' % duracao,
            '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-shortest',
            destino,
        ], check=True, capture_output=True)
    return PASTA


if __name__ == '__main__':
    print('vídeos de teste em:', garantir_takes())
    for n in sorted(os.listdir(PASTA)):
        print('  ', n, os.path.getsize(os.path.join(PASTA, n)), 'bytes')
