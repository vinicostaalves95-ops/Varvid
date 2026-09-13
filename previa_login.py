"""Fotografa a tela de login DE VERDADE, em cada um dos quatro estados.

Não é mockup: carrega o login.html como ele está, com um Supabase de mentira no
lugar da biblioteca real, e tira print de cada momento. Se o que você vê aqui
estiver errado, é o código que está errado — e é esse o objetivo.

Uso:  python3 previa_login.py
Sai em:  previa/*.png
"""

import os
import re
import asyncio

BASE = os.path.dirname(os.path.abspath(__file__))
SAIDA = os.path.join(BASE, 'previa')

# Substitui a biblioteca do Supabase por um dublê: nenhuma chamada de rede, e as
# respostas são as que interessam pra fotografar cada estado.
DUBLE = """
<script>
window.supabase = { createClient: function(){ return { auth: {
  onAuthStateChange: function(){},
  getSession: async function(){ return {data:{session:null}}; },
  signInWithPassword: async function(){ return {error:null}; },
  signUp: async function(){ return {data:{session:null},error:null}; },
  signInWithOAuth: async function(){ return {error:null}; },
  resetPasswordForEmail: async function(){ return {error:null}; },
  updateUser: async function(){ return {error:null}; },
}};}};
const _fetch = window.fetch;
window.fetch = async function(u, o){
  if(String(u).indexOf('auth-config') !== -1){
    return { json: async function(){ return {
      authEnabled:true, url:'https://exemplo.supabase.co', anonKey:'chave',
      googleEnabled: (location.hash.indexOf('comgoogle') !== -1),
      limits:{maxVideoSeconds:90,maxFileMB:100,maxUploadMB:200,retentionHours:48}
    };}};
  }
  return _fetch(u, o);
};
</script>
"""

CENAS = [
    ('1-entrar',        'login',     None,
     'Entrar — Google desligado (como vai pro ar)'),
    ('2-entrar-google',  'login',    None,
     'Entrar — com o Google ligado pela variável'),
    ('3-pedir-link',     'reset',    None,
     'Esqueci minha senha — pede só o e-mail'),
    ('4-link-enviado',   'reset',    ('ok',
     'Se existir uma conta com esse e-mail, o link está a caminho. '
     'Ele vale por 1 hora — confira também o spam.'),
     'Link enviado — resposta neutra, não revela quem é cliente'),
    ('5-nova-senha',     'novaSenha', None,
     'Voltou do e-mail — define a senha nova'),
    ('6-link-vencido',   'reset',    ('err', 'Esse link expirou. Peça um novo abaixo.'),
     'Link vencido — o caso mais comum, agora em português'),
    ('7-criar-conta',    'signup',   None,
     'Criar conta'),
]


async def main():
    from playwright.async_api import async_playwright

    os.makedirs(SAIDA, exist_ok=True)
    html = open(os.path.join(BASE, 'login.html'), encoding='utf-8').read()
    # Tira o <script src> do Supabase e põe o dublê no lugar.
    html = re.sub(r'<script src="https://cdn\.jsdelivr[^>]*></script>', DUBLE, html)
    alvo = os.path.join(SAIDA, '_previa.html')
    open(alvo, 'w', encoding='utf-8').write(html)

    async with async_playwright() as p:
        nav = await p.chromium.launch(executable_path='/opt/pw-browsers/chromium-1194/chrome-linux/chrome')
        for largura, altura, sufixo in ((1280, 820, ''), (430, 860, '-celular')):
            pag = await nav.new_page(viewport={'width': largura, 'height': altura},
                                     device_scale_factor=2)
            for nome, modo, msg, _titulo in CENAS:
                marca = '#comgoogle' if 'google' in nome else ''
                # about:blank no meio de propósito: trocar só o #hash é
                # navegação no mesmo documento, o boot() não roda de novo e a
                # cena sai igual à anterior — foi o que aconteceu na primeira
                # tentativa, com o botão do Google faltando na foto.
                await pag.goto('about:blank')
                await pag.goto('file://' + alvo + marca)
                await pag.wait_for_function('typeof irPara === "function"')
                await pag.wait_for_timeout(400)          # deixa a fonte carregar
                await pag.evaluate('irPara(%r)' % modo)
                if msg:
                    await pag.evaluate('showMsg(%r, %r)' % (msg[1], msg[0]))
                await pag.wait_for_timeout(120)
                await pag.screenshot(path=os.path.join(SAIDA, nome + sufixo + '.png'))
            await pag.close()
        await nav.close()

    os.remove(alvo)
    for f in sorted(os.listdir(SAIDA)):
        print(' ', f)


asyncio.run(main())
