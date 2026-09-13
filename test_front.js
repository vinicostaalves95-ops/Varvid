// Harness mínimo: roda o JS do app.html em Node com um DOM falso, pra exercitar
// a lógica de duração e a rede de segurança do onFiles.
const fs=require('fs');
const html=fs.readFileSync(require('path').join(__dirname,'app.html'),'utf8');
const appSrc=[...html.matchAll(/<script(?![^>]*\bsrc=)[^>]*>([\s\S]*?)<\/script>/g)]
  .map(m=>m[1]).join('\n').replace(/\nboot\(\);?\s*$/,'\n');

const els={}; const mk=id=>({id,style:{},className:'',textContent:'',innerHTML:'',
  classList:{toggle(){},add(){},remove(){}},addEventListener(){},removeAttribute(){},setAttribute(){},
  querySelectorAll(){return[]},value:'',disabled:false,onclick:null});
global.document={getElementById:id=>(els[id]=els[id]||mk(id)),
  createElement:()=>({style:{},appendChild(){},click(){},remove(){}}),
  querySelectorAll:()=>[], body:{appendChild(){},remove(){},classList:{add(){}}}, addEventListener(){}};
global.window={location:{pathname:'/',search:'',href:''},addEventListener(){}};
global.location=global.window.location;
global.localStorage={getItem:()=>null,setItem(){},removeItem(){}};
global.URL={createObjectURL:()=>'blob:x',revokeObjectURL(){}};
global.fetch=async()=>({ok:true,headers:{get:()=>'application/json'},json:async()=>({authEnabled:false})});
global.history={replaceState(){}};
global.URLSearchParams=class{get(){return null}};
process.on('unhandledRejection',()=>{});

const testSrc = `
let ok=0,fail=0;
const check=(n,c,x='')=>{ c?(ok++,console.log('  \\u2713 '+n)):(fail++,console.log('  \\u2717 '+n+' '+x)); };

console.log('\\n[1] Formatação de duração (o que a pessoa lê)');
check('45s', fmtDur(45)==='45s', fmtDur(45));
check('90s vira 1min30', fmtDur(90)==='1min30', fmtDur(90));
check('120s vira 2min', fmtDur(120)==='2min', fmtDur(120));
check('300s vira 5min', fmtDur(300)==='5min', fmtDur(300));

console.log('\\n[2] Duração do vídeo montado = 1 take por bloco, não a soma dos uploads');
const summary={ hook:[{duration:8},{duration:12}], story:[{duration:20}], cta:[{duration:10},{duration:6}] };
check('pior caso = 12+20+10 = 42s', duracaoMontada(summary)===42, duracaoMontada(summary));
check('somar todos os uploads daria 56s — número errado', 8+12+20+10+6===56);
check('sem medição devolve null (não bloqueia)', duracaoMontada({hook:[{duration:0}]})===null);

console.log('\\n[2b] Em produção quem mede é o NAVEGADOR (o Render não tem ffprobe)');
// O /analyze devolve duration:0 lá, porque o ffprobe não existe no Render de
// propósito. Antes disto o contador do Remix simplesmente não aparecia no ar —
// e aparecia na máquina do desenvolvedor, que é o pior lugar pra um bug morar.
DURACOES.clear();
DURACOES.set(chaveArq('Hook1.mp4'), 8);
DURACOES.set(chaveArq('Hook2.mp4'), 12);
DURACOES.set(chaveArq('Story1.mp4'), 20);
const semServidor={ hook:[{duration:0,files:['Hook1.mp4']},{duration:0,files:['Hook2.mp4']}],
                    story:[{duration:0,files:['Story1.mp4']}] };
check('servidor devolveu 0, o número ainda aparece', duracaoMontada(semServidor)===32,
      duracaoMontada(semServidor));

// O servidor renomeia ao salvar: "Hook 1.mp4" volta "Hook_1.mp4".
DURACOES.clear(); DURACOES.set(chaveArq('Hook 1.mp4'), 9);
check('nome renomeado pelo servidor ainda casa',
      duracaoMontada({hook:[{duration:0,files:['Hook_1.mp4']}]})===9);

// Bloco quebrado em partes (_pt1, _pt2) é UMA variante: soma as partes.
DURACOES.clear();
DURACOES.set(chaveArq('Hook1_pt1.mp4'), 5); DURACOES.set(chaveArq('Hook1_pt2.mp4'), 7);
check('partes da mesma variante somam',
      duracaoMontada({hook:[{duration:0,files:['Hook1_pt1.mp4','Hook1_pt2.mp4']}]})===12);

// Quando o servidor mediu (ambiente local), ele manda.
DURACOES.clear(); DURACOES.set(chaveArq('Hook1.mp4'), 99);
check('valor do servidor tem prioridade',
      duracaoMontada({hook:[{duration:8,files:['Hook1.mp4']}]})===8);

// Nem servidor nem navegador: continua sem bloquear ninguém.
DURACOES.clear();
check('as duas fontes falhando ainda devolve null',
      duracaoMontada({hook:[{duration:0,files:['Estranho.mov']}]})===null);
DURACOES.clear();

console.log('\\n[3] Limite de 1min30');
LIM.maxVideoSeconds=90;
check('52s passa', mostrarDuracao(52,'x')===true);
check('90s exato passa', mostrarDuracao(90,'x')===true);
check('91s é barrado', mostrarDuracao(91,'x')===false);
check('5min é barrado', mostrarDuracao(300,'x')===false);
check('null não bloqueia (codec ilegível)', mostrarDuracao(null,'x')===true);

console.log('\\n[4] REDE DE SEGURANÇA: erro inesperado vira mensagem, não silêncio');
const avisos=[];
toast=(t)=>avisos.push(t);
lerDuracao=()=>{ throw new Error('explodiu de proposito'); };
gerando=false; mode='single';
(async()=>{
  await onFiles([{name:'video.mp4', size:1024}]);
  check('a exceção não escapou em silêncio', avisos.length>0, 'nenhum aviso');
  check('mensagem em português e acionável',
        avisos.some(a=>/Não consegui ler seus arquivos/.test(a)), JSON.stringify(avisos));

  console.log('\\n[5] Limite de peso vira mensagem clara');
  avisos.length=0;
  lerDuracao=async()=>30;
  LIM.maxFileMB=100;
  await onFiles([{name:'enorme.mp4', size:150*1048576}]);
  check('arquivo de 150 MB é recusado com aviso',
        avisos.some(a=>/limite por arquivo/.test(a)), JSON.stringify(avisos));

  console.log('\\n[6] O Remix mede ANTES de enviar');
  // Não basta a função saber somar: ela precisa ser alimentada no caminho real.
  // Este teste prova a ligação — se alguém tirar a medição do _onFiles, o
  // contador some em produção de novo e nenhum outro teste perceberia.
  DURACOES.clear();
  let medidosAoEnviar=null;
  analyze=async()=>{ medidosAoEnviar=DURACOES.size; };
  lerDuracao=async(f)=>({'Hook1.mp4':8,'CTA1.mp4':4}[f.name] ?? null);
  gerando=false; mode='remix'; LIM.maxFileMB=100; LIM.maxUploadMB=200;
  await onFiles([{name:'Hook1.mp4',size:1024},{name:'CTA1.mp4',size:1024}]);
  check('os 2 takes foram medidos antes do /analyze', medidosAoEnviar===2, medidosAoEnviar);
  check('e a medição sobreviveu pro cálculo', DURACOES.get(chaveArq('Hook1.mp4'))===8);

  console.log('\\n[7] Modal de planos: o preço é o do Stripe');
  PLANS_DATA={ currentPlan:'free', temAnual:true, plans:[
    {key:'starter',label:'Starter',credits:50,ciclos:{
      mensal:{price_id:'m1',preco:{valor:3900,moeda:'brl',texto:'R$ 39'}},
      anual:{price_id:'a1',preco:{valor:39000,moeda:'brl',texto:'R$ 390'}}}},
    {key:'pro',label:'Pro',credits:150,ciclos:{
      mensal:{price_id:'m2',preco:{valor:6900,moeda:'brl',texto:'R$ 69'}}}},
    {key:'studio',label:'Studio',credits:400,ciclos:{
      mensal:{price_id:'m3',preco:null}}}
  ]};
  setCiclo('mensal');
  let html=els.planGrid.innerHTML;
  check('mostra R$ 39 no mensal', /R\\$ 39</.test(html), html.slice(0,120));
  check('mostra os 50 vídeos', /<b>50<\\/b> vídeos por mês/.test(html));
  check('sem preço legível, nada é inventado',
        /preço no checkout/.test(html) && !/R\\$ 117/.test(html));

  setCiclo('anual');
  html=els.planGrid.innerHTML;
  check('anual mostra R$ 390', /R\\$ 390</.test(html));
  check('anual mostra o equivalente mensal (R$ 390/12 = R$ 32,50)',
        /por ano · R\\$ 32,50\\/mês/.test(html), html.slice(0,260));
  check('e não repete "vídeos por mês" duas vezes no mesmo cartão',
        (html.match(/vídeos por mês/g)||[]).length===3, (html.match(/vídeos por mês/g)||[]).length);
  check('plano sem anual fica indisponível, não some',
        /Pro/.test(html) && /Indisponível/.test(html));
  check('e o botão dele está desabilitado', /disabled onclick="subscribe\\('pro'\\)"/.test(html));

  PLANS_DATA.currentPlan='pro'; setCiclo('mensal');
  html=els.planGrid.innerHTML;
  check('plano atual não é vendido de novo', /Plano atual/.test(html));

  console.log('\\n[8] Aviso de saldo: o anual precisa saber muito antes');
  avisoDeSaldo({creditsEnabled:true, acabando:false, credits:900, ciclo:'anual'});
  check('saldo confortável não incomoda ninguém',
        !/show/.test(els['saldo-aviso'].className), els['saldo-aviso'].className);

  const em10meses=new Date(Date.now()+300*864e5).toISOString();
  avisoDeSaldo({creditsEnabled:true, acabando:true, credits:40, ciclo:'anual', renovaEm:em10meses});
  let av=els['saldo-aviso'].innerHTML;
  check('anual mostra o saldo', /40 vídeo\\(s\\) restantes/.test(av), av);
  check('e diz que a recarga automática demora',
        /próxima recarga automática só vem em/i.test(av), av);
  check('com data em português, não ISO', !/\\d{4}-\\d{2}-\\d{2}/.test(av), av);

  const amanha=new Date(Date.now()+864e5).toISOString();
  avisoDeSaldo({creditsEnabled:true, acabando:true, credits:5, ciclo:'mensal', renovaEm:amanha});
  av=els['saldo-aviso'].innerHTML;
  check('mensal diz quando renova, sem drama', /Renova em amanhã/.test(av), av);
  check('e não fala em recarga automática distante',
        !/só vem em/.test(av), av);

  check('data vira "13 de outubro"', /^\\d+ de [a-zç]+/.test(dataCurta('2026-10-13')), dataCurta('2026-10-13'));
  check('data ilegível não quebra a tela', dataCurta('nada disso')===null);
  check('sem data, também não quebra', dataCurta(null)===null);

  console.log('\\n'+'='.repeat(46));
  console.log('  '+ok+' passaram · '+fail+' falharam');
  console.log('='.repeat(46));
  process.exit(fail?1:0);
})();
`;
eval(appSrc + '\n' + testSrc);
