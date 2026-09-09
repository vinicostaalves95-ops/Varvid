import os, sys, json, time, shutil
os.environ['VARVID_DATA']='/tmp/vartest/bloq'
os.environ['RENDER_BACKEND']='local'
os.environ['VARVID_SWEEPER']='off'
shutil.rmtree('/tmp/vartest/bloq', ignore_errors=True)
sys.path.insert(0,'/home/claude/Varvid')
import local_app as A
A.AUTH_ENABLED=False; A.CREDITS_ENABLED=False; A.STRIPE_ENABLED=False
c=A.app.test_client()
D='/tmp/vartest/e2e'
ok=fail=0
def check(n,cond,extra=''):
    global ok,fail
    if cond: ok+=1; print(f"  ✓ {n}")
    else: fail+=1; print(f"  ✗ {n} {extra}")
def novo(jid, status, idade_min=0, uid='local'):
    A.save_job(jid, {'status':status,'user_id':uid,'created_at':time.time()-idade_min*60,
                     'files':[],'completed':0,'count_requested':5})
    os.makedirs(A.job_dir(jid), exist_ok=True)

print("\n[1] Bloqueia nova geração enquanto uma roda")
novo('rodando','rendering')
files=[(open(os.path.join(D,f),'rb'), f) for f in sorted(os.listdir(D)) if f.endswith('.mp4')]
r=c.post('/analyze', data={'files':files}, content_type='multipart/form-data')
check('/analyze recusa com 409', r.status_code==409, r.status_code)
check('erro nomeado', (r.get_json() or {}).get('error')=='geracao_em_andamento', r.get_json())
check('devolve o job que está rodando', (r.get_json() or {}).get('job_id')=='rodando')
check('NÃO apagou o job em andamento', A.load_job('rodando') is not None)

print("\n[2] O mesmo vale pro modo vídeo único")
f=[(open(os.path.join(D,'Hook1.mp4'),'rb'),'Hook1.mp4')]
r=c.post('/single/generate', data={'files':f,'count':'2'}, content_type='multipart/form-data')
check('/single/generate recusa com 409', r.status_code==409, r.status_code)

print("\n[3] Job encerrado NÃO bloqueia (e é limpo)")
A.save_job('rodando', {'status':'done','user_id':'local','created_at':time.time()})
files=[(open(os.path.join(D,f),'rb'), f) for f in sorted(os.listdir(D)) if f.endswith('.mp4')]
r=c.post('/analyze', data={'files':files}, content_type='multipart/form-data')
check('/analyze passa', r.status_code==200, r.status_code)
check('job encerrado foi limpo', A.load_job('rodando') is None)
novo_id=r.get_json().get('job_id')

print("\n[4] ARMADILHA: job travado não pode prender o usuário pra sempre")
A._purge_job(novo_id)
novo('travado','queued', idade_min=120)     # 2h preso em queued
check('job travado não conta como rodando', not A._job_is_running(A.load_job('travado')))
files=[(open(os.path.join(D,f),'rb'), f) for f in sorted(os.listdir(D)) if f.endswith('.mp4')]
r=c.post('/analyze', data={'files':files}, content_type='multipart/form-data')
check('usuário consegue gerar de novo', r.status_code==200, r.status_code)
check('o travado foi removido', A.load_job('travado') is None)

print("\n[5] Job recente ainda rodando continua bloqueando")
A._purge_job(r.get_json().get('job_id'))
novo('recente','queued', idade_min=5)
check('5 min conta como rodando', A._job_is_running(A.load_job('recente')))
files=[(open(os.path.join(D,f),'rb'), f) for f in sorted(os.listdir(D)) if f.endswith('.mp4')]
r=c.post('/analyze', data={'files':files}, content_type='multipart/form-data')
check('bloqueia', r.status_code==409, r.status_code)

print("\n[6] 'Limpar' é a válvula de escape — funciona mesmo com job rodando")
r=c.post('/admin/clear')
check('/admin/clear 200', r.status_code==200)
check('apagou até o job em andamento', A.load_job('recente') is None)
files=[(open(os.path.join(D,f),'rb'), f) for f in sorted(os.listdir(D)) if f.endswith('.mp4')]
r=c.post('/analyze', data={'files':files}, content_type='multipart/form-data')
check('e libera nova geração', r.status_code==200, r.status_code)

print("\n[7] Isolamento: job de OUTRO usuário nunca bloqueia")
A._purge_job(r.get_json().get('job_id'))
novo('doutro','rendering', uid='outro-usuario')
files=[(open(os.path.join(D,f),'rb'), f) for f in sorted(os.listdir(D)) if f.endswith('.mp4')]
r=c.post('/analyze', data={'files':files}, content_type='multipart/form-data')
check('não bloqueia por job alheio', r.status_code==200, r.status_code)
check('e não apaga o job alheio', A.load_job('doutro') is not None)

print("\n[8] TTL usa a mesma regra (job travado não escapa da limpeza)")
os.utime(os.path.join(A.DATA_DIR,'doutro.json'), (time.time()-99*3600,)*2)
A.save_job('doutro', {'status':'queued','user_id':'outro-usuario','created_at':time.time()-99*3600})
os.utime(os.path.join(A.DATA_DIR,'doutro.json'), (time.time()-99*3600,)*2)
A.sweep_old_jobs()
check('sweeper remove job travado e antigo', A.load_job('doutro') is None)

print("\n" + "="*46); print(f"  {ok} passaram · {fail} falharam"); print("="*46)
sys.exit(1 if fail else 0)
