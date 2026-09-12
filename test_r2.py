import os, sys, time, json, shutil, threading
import boto3
from moto.server import ThreadedMotoServer

# Sobe um S3 falso e aponta o app pra ele — o caminho do R2 é exercitado de
# verdade (assinatura, upload, listagem, expiração do link), sem tocar produção.
srv = ThreadedMotoServer(port=5599, verbose=False); srv.start()
ENDPOINT='http://127.0.0.1:5599'
os.environ.update({
    'VARVID_DATA':'/tmp/vartest/r2', 'RENDER_BACKEND':'local', 'VARVID_SWEEPER':'off',
    'R2_ENDPOINT':ENDPOINT, 'R2_ACCESS_KEY_ID':'test', 'R2_SECRET_ACCESS_KEY':'test',
    'R2_BUCKET':'varvid', 'R2_URL_TTL_SECONDS':'900', 'VARVID_RETENCAO_HORAS':'48',
})
shutil.rmtree('/tmp/vartest/r2', ignore_errors=True)
# o simulador é mais rígido que o R2 quanto a região; só na criação usamos us-east-1
boto3.client('s3', endpoint_url=ENDPOINT, aws_access_key_id='test',
             aws_secret_access_key='test', region_name='us-east-1').create_bucket(Bucket='varvid')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import local_app as A
A.AUTH_ENABLED=False; A.CREDITS_ENABLED=False; A.STRIPE_ENABLED=False
c=A.app.test_client()
ok=fail=0
def check(n,cond,extra=''):
    global ok,fail
    if cond: ok+=1; print(f"  ✓ {n}")
    else: fail+=1; print(f"  ✗ {n} {extra}")

print("\n[1] R2 ligado pela configuração de ambiente")
check('R2_ENABLED', A.R2_ENABLED is True)
check('chave usa o job como prefixo', A.r2_key('abc','variation_01.mp4')=='abc/variation_01.mp4')
d=c.get('/auth-config.json').get_json()
check('retenção publicada pro front', (d.get('limits') or {}).get('retentionHours')==48)

print("\n[2] Modal grava no bucket e avisa o progresso")
job='job123'
A.save_job(job, {'status':'rendering','user_id':'local','count_requested':3,
                 'files':[],'completed':0,'created_at':time.time()})
cli=A.r2()
for i in (1,2,3):
    nome='variation_%02d.mp4'%i
    cli.put_object(Bucket='varvid', Key=f'{job}/{nome}', Body=b'video-bytes-'+str(i).encode())
    r=c.put(f'/output/{job}/meta/progress.json', json=({'files':['variation_%02d.mp4'%k for k in range(1,i+1)]}))
    check(f'aviso de progresso {i}/3 aceito', r.status_code==200, r.status_code)
st=c.get('/status/'+job).get_json()
check('status reflete 3 prontos', st.get('completed')==3, st.get('completed'))
check('barra andou sem o vídeo passar pelo servidor', 0 < st.get('progress',0) <= 95, st.get('progress'))

print("\n[3] Download devolve LINK, não o arquivo")
r=c.get(f'/download/{job}/variation_01.mp4')
check('resposta é JSON', r.headers.get('Content-Type','').startswith('application/json'))
url=(r.get_json() or {}).get('url','')
check('veio uma URL assinada', url.startswith(ENDPOINT) and 'Signature' in url or 'X-Amz-Signature' in url, url[:80])
check('link aponta pro objeto certo', f'{job}/variation_01.mp4' in url, url[:120])
check('link força o nome do arquivo', 'attachment' in url or 'response-content-disposition' in url.lower())
import urllib.request
try:
    with urllib.request.urlopen(url, timeout=10) as resp:
        conteudo=resp.read()
    check('o link BAIXA o vídeo de verdade', conteudo==b'video-bytes-1', conteudo[:30])
except Exception as e:
    check('o link BAIXA o vídeo de verdade', False, e)

print("\n[4] Não vaza arquivo de outro job nem inexistente")
r=c.get(f'/download/{job}/variation_99.mp4')
check('arquivo fora da lista do job é 404', r.status_code==404, r.status_code)

print("\n[5] Disco não reserva mais espaço para a saída")
antes=A.ensure_disk_space(variacoes=0)[1]
A.MIN_FREE_MB=1
okd,_=A.ensure_disk_space(variacoes=30)   # 30 variações, e ainda assim passa
check('30 variações não exigem espaço local', okd is True)

print("\n[6] Limpar apaga do bucket, não espera as 48h")
antes=len(cli.list_objects_v2(Bucket='varvid', Prefix=job+'/').get('Contents',[]))
check('3 objetos no bucket antes', antes==3, antes)
r=c.post('/admin/clear')
check('/admin/clear ok', r.status_code==200)
depois=cli.list_objects_v2(Bucket='varvid', Prefix=job+'/').get('Contents',[])
check('bucket esvaziado', len(depois)==0, depois)

print("\n[7] _done traz a lista final (rede contra aviso perdido)")
A.save_job('j2', {'status':'rendering','user_id':'local','count_requested':2,'files':[],'completed':0})
c.put('/output/j2/meta/_done.json', json={'status':'done','files':['variation_01.mp4','variation_02.mp4']})
st=c.get('/status/j2').get_json()
check('estado final correto mesmo sem progresso parcial',
      st.get('status')=='done' and st.get('completed')==2, st)

srv.stop()
print("\n"+"="*46); print(f"  {ok} passaram · {fail} falharam"); print("="*46)
sys.exit(1 if fail else 0)
