import os, sys, time, shutil, json
os.environ['VARVID_DATA']='/tmp/vartest/lim'
os.environ['RENDER_BACKEND']='local'; os.environ['VARVID_SWEEPER']='off'
shutil.rmtree('/tmp/vartest/lim', ignore_errors=True)
sys.path.insert(0,'/home/claude/Varvid')
import local_app as A
A.AUTH_ENABLED=False; A.CREDITS_ENABLED=False; A.STRIPE_ENABLED=False
c=A.app.test_client(); D='/tmp/vartest/e2e'
ok=fail=0
def check(n,cond,extra=''):
    global ok,fail
    if cond: ok+=1; print(f"  ✓ {n}")
    else: fail+=1; print(f"  ✗ {n} {extra}")

print("\n[1] Limites publicados pro front")
d=c.get('/auth-config.json').get_json()
lim=d.get('limits') or {}
check('/auth-config.json expõe os limites', lim.get('maxVideoSeconds')==90, lim)
check('limite por arquivo', lim.get('maxFileMB')==100)
check('limite do envio', lim.get('maxUploadMB')==200)
check('MAX_CONTENT_LENGTH = 200 MB', A.app.config['MAX_CONTENT_LENGTH']==200*1024*1024,
      A.app.config['MAX_CONTENT_LENGTH'])

print("\n[2] Envio acima do limite responde JSON, não HTML")
grande=b'x'*(201*1024*1024)
r=c.post('/analyze', data={'files':(__import__('io').BytesIO(grande),'grande.mp4')},
         content_type='multipart/form-data')
check('413 (não 500)', r.status_code==413, r.status_code)
check('Content-Type é JSON', r.headers.get('Content-Type','').startswith('application/json'),
      r.headers.get('Content-Type'))
check('erro nomeado', (r.get_json() or {}).get('error')=='arquivo_grande_demais', r.get_json())
del grande

print("\n[3] CENÁRIO DO SÓCIO: saída maior que o disco")
# 5 min x 5 variações ≈ 675 MB. A guarda antiga só olhava a entrada.
A.MIN_FREE_MB=150; A.EST_MB_POR_VARIACAO=45
livre=A.free_space_mb()
okd,_=A.ensure_disk_space(variacoes=0)
check('sem contar a saída, passaria', okd is True)
A.EST_MB_POR_VARIACAO=livre/3           # 3 variações já estouram
okd2,_=A.ensure_disk_space(variacoes=5)
check('contando a saída, recusa antes de começar', okd2 is False)
A.EST_MB_POR_VARIACAO=45

print("\n[4] /generate reserva espaço ANTES de cobrar crédito")
import io
files=[(open(os.path.join(D,f),'rb'), f) for f in sorted(os.listdir(D)) if f.endswith('.mp4')]
r=c.post('/analyze', data={'files':files}, content_type='multipart/form-data')
job=r.get_json()['job_id']
A.EST_MB_POR_VARIACAO=A.free_space_mb()   # 1 variação já não cabe
cobrados=[]
_orig=A.charge_credits
A.charge_credits=lambda uid,n: (cobrados.append(n), (True,99,None))[1]
A.CREDITS_ENABLED=True
r=c.post('/generate', json={'job_id':job,'count':5})
check('recusa com 507', r.status_code==507, r.status_code)
check('NÃO cobrou crédito por algo que não vai existir', cobrados==[], cobrados)
A.charge_credits=_orig; A.CREDITS_ENABLED=False; A.EST_MB_POR_VARIACAO=45

print("\n[5] Com espaço, segue normal")
r=c.post('/generate', json={'job_id':job,'count':2})
check('/generate 200', r.status_code==200, r.status_code)
for _ in range(120):
    st=c.get('/status/'+job).get_json()
    if st.get('status') in ('done','error'): break
    time.sleep(0.5)
check('gerou os 2 vídeos', st.get('status')=='done' and st.get('completed')==2,
      '%s/%s' % (st.get('status'), st.get('completed')))

print("\n[6] Limpar destrava mesmo com job preso e ZERO vídeos")
A.save_job('preso', {'status':'rendering','user_id':'local','created_at':time.time(),
                     'files':[],'completed':0})
os.makedirs(A.job_dir('preso'), exist_ok=True)
files=[(open(os.path.join(D,f),'rb'), f) for f in sorted(os.listdir(D)) if f.endswith('.mp4')]
r=c.post('/analyze', data={'files':files}, content_type='multipart/form-data')
check('bloqueado (como aconteceu com ele)', r.status_code==409, r.status_code)
r=c.post('/admin/clear')
check('/admin/clear responde ok', r.status_code==200 and r.get_json().get('ok') is True)
check('job preso removido', A.load_job('preso') is None)
files=[(open(os.path.join(D,f),'rb'), f) for f in sorted(os.listdir(D)) if f.endswith('.mp4')]
r=c.post('/analyze', data={'files':files}, content_type='multipart/form-data')
check('destravou de verdade', r.status_code==200, r.status_code)

print("\n" + "="*48); print(f"  {ok} passaram · {fail} falharam"); print("="*48)
sys.exit(1 if fail else 0)
