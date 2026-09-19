# Converte cada artboard .dc.html numa página HTML que abre sozinha no navegador,
# para consulta e para servir de referência na hora de implementar.
import re, os, glob

TITULOS = {
 'NoiteLogin': 'N01 · Login', 'NoiteInicio': 'N02 · Início', 'NoiteRemixVazio': 'N03 · Remix antes', 'NoiteRemixCheio': 'N04 · Remix com os takes', 'NoiteUnico': 'N05 · Vídeo único', 'NoiteGerando': 'N06 · Gerando', 'NoiteResultados': 'N07 · Resultados', 'NoiteSemCreditos': 'N08 · Créditos esgotados', 'NoitePlanos': 'N09 · Pop-up de planos', 'NoiteLegal': 'N10 · Pop-up legal', 'NoiteComoFunciona': 'N11 · Como funciona', 'NoiteRoteiro': 'N12 · Roteiro pronto',
 'ConsoleLogin': '01 · Login', 'ConsoleHome': '02 · Início', 'Main': '03 · Remix antes dos arquivos',
 'ConsoleUnico': '05 · Vídeo único', 'ConsoleGerando': '06 · Gerando',
 'ConsoleResultados': '07 · Resultados', 'ConsolePlanos': '09 · Pop-up de planos',
 'ConsoleLegal': '10 · Pop-up legal',
 'ConsoleRemixCheio': '04 · Remix com os takes', 'ConsoleSemCreditos': '08 · Créditos esgotados',
 'ConsoleMetodo': '11 · Como funciona', 'ConsolePrompt': '12 · Roteiro pronto',
 'MarcaConsole': 'Marca · Console', 'MarcaOficio': 'Marca · Ofício (arquivo)',
 'MarcaSinal': 'Marca · Sinal (arquivo)',
 'OficioStudio': 'Arquivo · Ofício Studio', 'OficioLogin': 'Arquivo · Ofício Login',
 'OficioPlanos': 'Arquivo · Ofício Planos', 'SinalStudio': 'Arquivo · Sinal Studio',
 'SinalLogin': 'Arquivo · Sinal Login', 'SinalPlanos': 'Arquivo · Sinal Planos',
}
ARQUIVO = {
 'NoiteLogin': 'noite-01-login', 'NoiteInicio': 'noite-02-inicio', 'NoiteRemixVazio': 'noite-03-remix-antes', 'NoiteRemixCheio': 'noite-04-remix-com-takes', 'NoiteUnico': 'noite-05-video-unico', 'NoiteGerando': 'noite-06-gerando', 'NoiteResultados': 'noite-07-resultados', 'NoiteSemCreditos': 'noite-08-creditos-esgotados', 'NoitePlanos': 'noite-09-popup-planos', 'NoiteLegal': 'noite-10-popup-legal', 'NoiteComoFunciona': 'noite-11-como-funciona', 'NoiteRoteiro': 'noite-12-roteiro-pronto',
 'ConsoleLogin': '01-login', 'ConsoleHome': '02-inicio', 'Main': '03-remix-antes-dos-arquivos',
 'ConsoleUnico': '05-video-unico', 'ConsoleGerando': '06-gerando',
 'ConsoleResultados': '07-resultados', 'ConsolePlanos': '09-popup-planos',
 'ConsoleLegal': '10-popup-legal', 'ConsoleRemixCheio': '04-remix-com-takes',
 'ConsoleSemCreditos': '08-creditos-esgotados', 'ConsoleMetodo': '11-como-funciona',
 'ConsolePrompt': '12-roteiro-pronto', 'MarcaConsole': 'marca-console',
 'MarcaOficio': 'arquivo-marca-oficio', 'MarcaSinal': 'arquivo-marca-sinal',
 'OficioStudio': 'arquivo-oficio-studio', 'OficioLogin': 'arquivo-oficio-login',
 'OficioPlanos': 'arquivo-oficio-planos', 'SinalStudio': 'arquivo-sinal-studio',
 'SinalLogin': 'arquivo-sinal-login', 'SinalPlanos': 'arquivo-sinal-planos',
}

MOLDE = """<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>varvid — %(titulo)s</title>
<link rel="icon" href="../favicon.svg">
%(fontes)s<style>
  html, body { margin: 0; background: #DDE1E6; }
  body { min-height: 100vh; display: flex; align-items: center; justify-content: center; padding: 28px; box-sizing: border-box; }
  .moldura { box-shadow: 0 18px 50px rgba(16, 19, 24, 0.18); border-radius: 10px; overflow: hidden; }
%(estilo)s</style>
</head>
<body>
<div class="moldura">
%(corpo)s
</div>
</body>
</html>
"""


def exportar(destino='/mnt/user-data/outputs/design/telas'):
    os.makedirs(destino, exist_ok=True)
    for caminho in sorted(glob.glob('*.dc.html')):
        stem = caminho[:-len('.dc.html')]
        s = open(caminho, encoding='utf-8').read()
        fontes = '\n'.join(re.findall(r'<link rel="stylesheet"[^>]*>', s)) + '\n'
        m = re.search(r'<helmet>.*?<style>(.*?)</style>.*?</helmet>(.*?)</x-dc>', s, re.S)
        estilo, corpo = m.group(1), m.group(2)
        estilo = '\n'.join('  ' + l.strip() for l in estilo.strip().split('\n')
                           if l.strip().startswith('a ')) + '\n'
        open(f'{destino}/{ARQUIVO[stem]}.html', 'w', encoding='utf-8').write(
            MOLDE % dict(titulo=TITULOS[stem], fontes=fontes, estilo=estilo, corpo=corpo.strip()))
    print('telas exportadas:', len(glob.glob(destino + '/*.html')))


if __name__ == '__main__':
    exportar()
