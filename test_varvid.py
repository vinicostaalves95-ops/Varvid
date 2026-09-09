import os, sys, json, time, shutil, threading
os.environ['VARVID_DATA']='/tmp/vartest/data'
os.environ['RENDER_BACKEND']='local'
os.environ['VARVID_SWEEPER']='off'          # controlamos a varredura no teste
os.environ['VARVID_JOB_TTL_HOURS']='1'
shutil.rmtree('/tmp/vartest/data', ignore_errors=True)
sys.path.insert(0,'/home/claude/Varvid')
import local_app as A

ok=fail=0
def check(name, cond, extra=''):
    global ok, fail
    if cond: ok+=1;  print(f"  ✓ {name}")
    else:    fail+=1; print(f"  ✗ {name} {extra}")

print("\n[1] save_job / load_job — ida e volta")
A.save_job('j1', {'status':'ready','user_id':'u1'})
check('grava e lê', (A.load_job('j1') or {}).get('status')=='ready')
check('não deixa .tmp para trás', not os.path.exists(os.path.join(A.DATA_DIR,'j1.json.tmp')))

print("\n[2] load_job com JSON corrompido (o bug de 06/09)")
p=os.path.join(A.DATA_DIR,'j2.json')
open(p,'w').close()                                  # arquivo VAZIO, como em produção
check('devolve None em vez de estourar', A.load_job('j2') is None)
check('leitura NAO apaga (quem remove e o sweeper)', os.path.exists(p))
A.sweep_old_jobs()                                   # sweeper recolhe o lixo
check('sweeper remove JSON de tamanho zero na hora', not os.path.exists(p))
open(p,'w').write('{"truncado":')                    # JSON pela metade
check('tolera JSON truncado', A.load_job('j2') is None)
os.remove(p)

print("\n[3] save_job é atômico sob concorrência (2 workers)")
A.save_job('j3', {'n':0})
erros=[]
def escritor(k):
    for i in range(150):
        try: A.save_job('j3', {'n':k*1000+i,'pad':'x'*400})
        except Exception as e: erros.append(e)
def leitor():
    for _ in range(400):
        try:
            d=A.load_job('j3')
            if d is not None and 'n' not in d: erros.append('parcial: %r' % d)
        except Exception as e: erros.append(e)
ts=[threading.Thread(target=escritor,args=(k,)) for k in (1,2)]+[threading.Thread(target=leitor) for _ in range(3)]
[t.start() for t in ts]; [t.join() for t in ts]
check('nenhuma leitura pegou estado parcial', not erros, erros[:3])

print("\n[4] TTL — só apaga o que passou do prazo, e nunca job ativo")
os.makedirs(os.path.join(A.DATA_DIR,'velho'), exist_ok=True)
A.save_job('velho', {'status':'done','user_id':'u1'})
A.save_job('novo',  {'status':'done','user_id':'u1'})
A.save_job('ativo', {'status':'rendering','user_id':'u1'})
antigo = time.time()-3*3600
for jid in ('velho','ativo'):
    os.utime(os.path.join(A.DATA_DIR,jid+'.json'), (antigo,antigo))
n=A.sweep_old_jobs()
check('apagou o job vencido', A.load_job('velho') is None)
check('apagou a pasta junto', not os.path.exists(os.path.join(A.DATA_DIR,'velho')))
check('preservou o job recente', A.load_job('novo') is not None)
check('preservou job em andamento mesmo vencido', A.load_job('ativo') is not None, '<- protegido por _is_job_active')

print("\n[5] lock entre processos")
check('primeiro adquire', A._acquire_sweep_lock() is True)
check('segundo é recusado', A._acquire_sweep_lock() is False)
A._release_sweep_lock()
check('libera depois', A._acquire_sweep_lock() is True)
A._release_sweep_lock()
os.close(os.open(A._SWEEP_LOCK, os.O_CREAT|os.O_WRONLY))
os.utime(A._SWEEP_LOCK,(time.time()-1200,time.time()-1200))
check('recupera lock órfão (worker morto)', A._acquire_sweep_lock() is True)
A._release_sweep_lock()
check('lock não é confundido com job', A.load_job('.sweep') is None)

print("\n[6] guarda de disco")
okd, free = A.ensure_disk_space()
check('passa com disco saudável', okd is True)
A.MIN_FREE_MB = free*10                              # exige mais do que existe
okd2, _ = A.ensure_disk_space()
check('recusa (sem crash) quando não há espaço', okd2 is False)
A.MIN_FREE_MB = 500

print("\n[7] fail-closed de segurança")
A.MODAL_CALLBACK_SECRET=''; A.MODAL_ENABLED=True
with A.app.test_request_context('/output/x/y.mp4'):
    check('callback do Modal bloqueado sem segredo', A._check_modal_token() is False)
A.MODAL_ENABLED=False
with A.app.test_request_context('/output/x/y.mp4'):
    check('modo local segue liberado', A._check_modal_token() is True)

c=A.app.test_client()
A.STRIPE_ENABLED=True; A.STRIPE_WEBHOOK_SECRET=''
r=c.post('/billing/webhook', json={'type':'invoice.paid','data':{'object':{'customer':'cus_x'}}})
check('webhook recusa evento não assinado', r.status_code==400, '(veio %s)' % r.status_code)

print("\n[8] endpoints devolvem JSON, nunca HTML")
A.STRIPE_ENABLED=False; A.AUTH_ENABLED=False; A.CREDITS_ENABLED=False
r=c.post('/analyze', data={})
check('/analyze sem arquivo -> JSON', r.headers.get('Content-Type','').startswith('application/json'), r.headers.get('Content-Type'))
r=c.get('/status/naoexiste')
check('/status inexistente -> JSON 200', r.status_code==200 and r.get_json().get('status')=='not_found')
p=os.path.join(A.DATA_DIR,'corrompido.json'); open(p,'w').close()
r=c.get('/status/corrompido')
check('/status com JSON vazio -> não é mais 500', r.status_code==200, '(veio %s)' % r.status_code)

print("\n" + "="*44)
print(f"  {ok} passaram · {fail} falharam")
print("="*44)
sys.exit(1 if fail else 0)
