// Harness do login.html: roda o JS da tela de login em Node com um DOM falso e
// um Supabase de mentira, pra exercitar o que não dá pra ver olhando a tela.
//
// O teste que justifica este arquivo é o [3]. Quem volta do link de recuperação
// chega COM sessão válida. Se a ordem das checagens no boot() inverter algum
// dia, essa pessoa é jogada direto no app e nunca vê a tela de nova senha — o
// link vira "entrar sem senha" e quem esqueceu continua sem conseguir trocar.
// É um defeito silencioso: nada quebra na tela, só deixa de funcionar.

const fs = require('fs');
const vm = require('vm');
const path = require('path');

const html = fs.readFileSync(path.join(__dirname, 'login.html'), 'utf8');
const SRC = [...html.matchAll(/<script(?![^>]*\bsrc=)[^>]*>([\s\S]*?)<\/script>/g)]
  .map(m => m[1]).join('\n').replace(/\nboot\(\);?\s*$/, '\n');

function supabaseFalso(o) {
  o = o || {};
  return {
    createClient: () => ({
      auth: {
        onAuthStateChange(cb) { o.guardarCallback && o.guardarCallback(cb); },
        getSession: async () => ({ data: { session: o.session || null } }),
        signInWithPassword: async () => ({ error: o.erroLogin || null }),
        signUp: async (dados) => { (o.cadastros = o.cadastros || []).push(dados); return { data: { session: null }, error: null }; },
        signInWithOAuth: async () => ({ error: null }),
        resetPasswordForEmail: async (email, opts) => {
          (o.enviados = o.enviados || []).push({ email, opts });
          return { error: o.erroReset || null };
        },
        updateUser: async () => ({ error: o.erroUpdate || null }),
      },
    }),
  };
}

async function montar(c) {
  c = c || {};
  const els = {};
  const mk = id => ({
    id, style: {}, className: '', textContent: '', innerHTML: '', value: '',
    disabled: false, onclick: null,
    setAttribute() {}, addEventListener() {},
    classList: { add() {}, remove() {}, toggle() {} },
  });
  const pegar = id => (els[id] = els[id] || mk(id));

  // Espelha o HTML: estes dois nascem escondidos.
  pegar('googleBtn').style.display = 'none';
  pegar('orDivider').style.display = 'none';

  const box = {
    console,
    document: { getElementById: pegar },
    location: {
      hash: c.hash || '', search: c.search || '', pathname: '/login',
      origin: 'https://varvid.onrender.com', href: '',
    },
    setTimeout: (fn) => { c.rodarTimeout && fn(); },
    fetch: async () => ({
      json: async () => ({
        authEnabled: c.authEnabled !== false,
        url: 'https://projeto.supabase.co', anonKey: 'chave-publica',
        googleEnabled: !!c.googleEnabled,
      }),
    }),
    supabase: supabaseFalso(c.sb || {}),
  };
  box.window = box;
  vm.createContext(box);
  vm.runInContext(SRC, box);
  await box.boot();

  // Em que tela a pessoa está? Perguntamos pelo título que ela lê, não por uma
  // variável interna — se o estado mudar sem a tela mudar junto, é bug, e o
  // teste tem que enxergar isso.
  const TITULOS = {
    'Entrar na sua conta': 'login', 'Criar sua conta': 'signup',
    'Recuperar senha': 'reset', 'Criar uma senha nova': 'novaSenha',
  };
  return {
    els, box,
    visivel: id => pegar(id).style.display !== 'none',
    tela: () => TITULOS[pegar('title').textContent] || ('?' + pegar('title').textContent),
  };
}

// ── ─────────────────────────────────────────────────────────────────────────
let ok = 0, fail = 0;
const check = (n, c, x) => { c ? (ok++, console.log('  ✓ ' + n))
                               : (fail++, console.log('  ✗ ' + n + ' ' + (x || ''))); };

(async () => {

console.log('\n[1] Botão do Google — quem manda é o servidor');
{
  const a = await montar({ googleEnabled: false });
  check('desligado: botão não aparece', !a.visivel('googleBtn'));
  check('desligado: o "ou com e-mail" some junto', !a.visivel('orDivider'));

  const b = await montar({ googleEnabled: true });
  check('ligado: botão aparece', b.visivel('googleBtn'));
  check('ligado: divisória volta', b.visivel('orDivider'));
}

console.log('\n[2] Uma tela, quatro estados');
{
  const a = await montar({});
  check('abre no login', a.tela() === 'login', a.tela());
  check('login mostra "esqueci minha senha"', a.visivel('forgotRow'));

  a.box.irPara('reset');
  check('reset: pede só o e-mail', a.visivel('fieldEmail') && !a.visivel('fieldPassword'));
  check('reset: oferece o caminho de volta', a.visivel('backRow'));
  check('reset: some o "criar conta"', !a.visivel('swap'));

  a.box.irPara('novaSenha');
  check('nova senha: pede só a senha', !a.visivel('fieldEmail') && a.visivel('fieldPassword'));
  check('nova senha: rótulo muda', a.els.passwordLabel.textContent === 'Nova senha',
        a.els.passwordLabel.textContent);

  a.box.irPara('signup');
  check('signup não oferece "esqueci a senha"', !a.visivel('forgotRow'));
}

console.log('\n[3] Volta do link de recuperação — o teste que importa');
{
  const sessao = { access_token: 'tok' };

  const a = await montar({ hash: '#access_token=tok&type=recovery', sb: { session: sessao } });
  check('com sessão + link de recuperação, NÃO joga no app', a.box.location.href !== '/',
        'foi pra ' + a.box.location.href);
  check('mostra a tela de nova senha', a.tela() === 'novaSenha', a.tela());

  // O sinal próprio, colado no redirectTo: vale mesmo se o Supabase mudar o
  // formato do link.
  const b = await montar({ search: '?recuperar=1', sb: { session: sessao } });
  check('nosso ?recuperar=1 sozinho já basta', b.tela() === 'novaSenha', b.tela());

  // Controle: sem sinal nenhum, sessão válida tem que levar pro app.
  const c = await montar({ sb: { session: sessao } });
  check('sem link, sessão normal entra no app', c.box.location.href === '/', c.box.location.href);
}

console.log('\n[4] Link vencido — o caso mais comum de todos');
{
  const a = await montar({
    hash: '#error=access_denied&error_code=otp_expired' +
          '&error_description=Email+link+is+invalid+or+has+expired',
  });
  check('cai na tela de pedir outro link', a.tela() === 'reset', a.tela());
  check('explica em português', /expirou/i.test(a.els.msg.textContent), a.els.msg.textContent);
  check('não mostra o texto em inglês', !/invalid/i.test(a.els.msg.textContent));
}

console.log('\n[5] Erro técnico vira frase que a pessoa entende');
{
  const a = await montar({});
  const t = a.box.traduzir;
  check('senha errada', t('Invalid login credentials') === 'E-mail ou senha incorretos.');
  check('limite de e-mails', /Espere alguns minutos/.test(t('email rate limit exceeded')));
  check('sem internet', /conexão/.test(t('Failed to fetch')));
  check('erro desconhecido não vaza jargão',
        !/undefined|null|error/i.test(t('PGRST301: jwt malformed')), t('PGRST301: jwt malformed'));
}

console.log('\n[6] Pedido do link');
{
  const enviados = [];
  const a = await montar({ sb: { enviados } });
  a.box.irPara('reset');
  a.els.email.value = ' pessoa@email.com ';
  await a.box.doSubmit();

  check('manda o e-mail sem espaço sobrando', enviados[0] && enviados[0].email === 'pessoa@email.com',
        enviados[0] && enviados[0].email);
  check('volta pra ESTA tela, não pra raiz do app',
        enviados[0] && /\/login\?recuperar=1$/.test(enviados[0].opts.redirectTo),
        enviados[0] && enviados[0].opts.redirectTo);
  check('resposta não revela se o e-mail tem conta',
        /Se existir uma conta/.test(a.els.msg.textContent), a.els.msg.textContent);

  // Sem e-mail preenchido não chama o servidor à toa.
  const b = await montar({ sb: { enviados: [] } });
  b.box.irPara('reset');
  b.els.email.value = '';
  await b.box.doSubmit();
  check('campo vazio: avisa e não chama o servidor', /Preencha seu e-mail/.test(b.els.msg.textContent));
}

console.log('\n[7] Salvar a senha nova');
{
  const a = await montar({ hash: '#type=recovery', rodarTimeout: true, sb: { session: { t: 1 } } });
  a.els.password.value = '123';
  await a.box.doSubmit();
  check('senha curta é barrada antes de ir ao servidor',
        /pelo menos 6/.test(a.els.msg.textContent), a.els.msg.textContent);

  a.els.password.value = 'senhanova123';
  await a.box.doSubmit();
  check('senha válida salva e entra no app', a.box.location.href === '/', a.box.location.href);

  const b = await montar({
    hash: '#type=recovery', sb: { session: { t: 1 }, erroUpdate: { message: 'Token has expired or is invalid' } },
  });
  b.els.password.value = 'senhanova123';
  await b.box.doSubmit();
  check('link já usado devolve pra pedir outro', b.tela() === 'reset', b.tela());
}

console.log('\n[8] Cadastro: repetir o e-mail');
{
  const cad = [];
  const a = await montar({ sb: { cadastros: cad } });
  a.box.irPara('signup');
  check('campo de repetir e-mail aparece no cadastro', a.els.fieldEmail2.style.display === '', a.els.fieldEmail2.style.display);

  a.els.email.value = 'ana@gmail.com'; a.els.email2.value = 'ana@gmial.com'; a.els.password.value = 'senha123';
  await a.box.doSubmit();
  check('e-mails diferentes: barra e NÃO chama o servidor', cad.length === 0 && /não são iguais/.test(a.els.msg.textContent), a.els.msg.textContent);

  a.els.email2.value = '';
  await a.box.doSubmit();
  check('segundo campo vazio também barra', cad.length === 0);

  a.els.email2.value = '  ANA@gmail.com ';
  await a.box.doSubmit();
  check('iguais (ignorando espaço e maiúscula): cadastra', cad.length === 1 && cad[0].email === 'ana@gmail.com', JSON.stringify(cad));
  check('mensagem mostra para onde o link foi', /ana@gmail\.com/.test(a.els.msg.textContent), a.els.msg.textContent);

  a.box.irPara('login');
  check('some fora do cadastro e é limpo', a.els.fieldEmail2.style.display === 'none' && a.els.email2.value === '');
  a.box.irPara('reset');
  check('não aparece na recuperação de senha', a.els.fieldEmail2.style.display === 'none');
  check('colar é bloqueado no HTML', /id="email2"[^>]*onpaste="return false"/.test(html));
}

console.log('\n' + ok + ' passaram · ' + fail + ' falharam');
process.exit(fail ? 1 : 0);

})();
