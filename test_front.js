// Harness mínimo: roda o JS do app.html em Node com um DOM falso, pra exercitar
// a lógica de duração e a rede de segurança do onFiles.
const fs=require('fs');
const html=fs.readFileSync('/home/claude/Varvid/app.html','utf8');
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

  console.log('\\n'+'='.repeat(46));
  console.log('  '+ok+' passaram · '+fail+' falharam');
  console.log('='.repeat(46));
  process.exit(fail?1:0);
})();
`;
eval(appSrc + '\n' + testSrc);
