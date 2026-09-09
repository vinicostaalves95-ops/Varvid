import os, sys, time, json, shutil
os.environ['VARVID_DATA']='/tmp/vartest/e2edata'
os.environ['RENDER_BACKEND']='local'
os.environ['VARVID_SWEEPER']='off'
shutil.rmtree('/tmp/vartest/e2edata', ignore_errors=True)
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

print("\n[E2E] fluxo REMIX completo (upload -> analyze -> generate -> download)")
files=[(open(os.path.join(D,f),'rb'), f) for f in sorted(os.listdir(D)) if f.endswith('.mp4')]
r=c.post('/analyze', data={'files':files}, content_type='multipart/form-data')
check('/analyze 200 JSON', r.status_code==200 and r.is_json, r.status_code)
d=r.get_json(); job=d.get('job_id')
check('detectou os blocos', set(d.get('blocks_found',[]))=={'hook','story','cta'}, d.get('blocks_found'))
check('calculou combinações (2 hooks x 2 ctas = 4)', d.get('max_combinations')==4, d.get('max_combinations'))

r=c.post('/generate', json={'job_id':job,'count':3,'headline_text':'','headline_duration':3})
check('/generate 200', r.status_code==200 and r.get_json().get('ok'), r.status_code)

for _ in range(120):
    st=c.get('/status/'+job).get_json()
    if st.get('status') in ('done','error'): break
    time.sleep(0.5)
check('job concluiu', st.get('status')=='done', st.get('status'))
check('gerou os 3 vídeos', st.get('completed')==3, st.get('completed'))

if st.get('files'):
    r=c.get('/download/%s/%s' % (job, st['files'][0]))
    check('download devolve o mp4', r.status_code==200 and len(r.data)>1000, '%s / %sB' % (r.status_code, len(r.data)))
    outs=[os.path.getsize(os.path.join(A.job_dir(job),'output',f)) for f in st['files']]
    check('variações têm tamanhos distintos (fingerprint)', len(set(outs))>1, outs)

print("\n[E2E] fluxo VÍDEO ÚNICO")
f=[(open(os.path.join(D,'Hook1.mp4'),'rb'),'Hook1.mp4')]
r=c.post('/single/generate', data={'files':f,'count':'2','headline_text':'','headline_duration':'3'},
         content_type='multipart/form-data')
check('/single/generate 200', r.status_code==200, r.status_code)
job2=r.get_json().get('job_id')
for _ in range(120):
    st2=c.get('/status/'+job2).get_json()
    if st2.get('status') in ('done','error'): break
    time.sleep(0.5)
check('single concluiu com 2 vídeos', st2.get('status')=='done' and st2.get('completed')==2,
      '%s/%s' % (st2.get('status'), st2.get('completed')))

print("\n[E2E] /admin/clear (o botão novo do front)")
r=c.post('/admin/clear')
check('/admin/clear 200', r.status_code==200)
check('apagou os arquivos do usuário', c.get('/status/'+job).get_json().get('status')=='not_found')

print("\n[E2E] nenhum .tmp/.part vazado no diretório de dados")
sobras=[f for f in os.listdir(A.DATA_DIR) if f.endswith(('.tmp','.part'))]
check('diretório limpo', not sobras, sobras)

print("\n" + "="*44); print(f"  {ok} passaram · {fail} falharam"); print("="*44)
sys.exit(1 if fail else 0)
