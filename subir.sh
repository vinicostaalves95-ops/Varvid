#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
#  VarVid — publica tudo de uma vez
#
#  Uso:   ./subir.sh "mensagem do commit"
#
#  Faz, nesta ordem:
#    1. roda os testes (para na primeira falha)
#    2. publica a função no Modal, se modal_app.py mudou
#    3. commita e envia pro GitHub
#    4. mostra o que conferir no Render
#
#  O único passo que continua manual é o Deploy no Render — ele não tem
#  comando de linha, é clique no painel.
# ─────────────────────────────────────────────────────────────────────────────

set -e
cd "$(dirname "$0")"

MSG="${1:-}"
if [ -z "$MSG" ]; then
  echo "❌ Faltou a mensagem do commit."
  echo "   Exemplo: ./subir.sh \"feat: videos no R2\""
  exit 1
fi

echo "═══════════════════════════════════════════════════"
echo "  VarVid · publicando"
echo "═══════════════════════════════════════════════════"

# ── 0. integridade da entrega ───────────────────────────────────────────────
# Arquivos já rastreados pelo git voltaram sozinhos à versão anterior cinco
# vezes nesta pasta. Commitar sem perceber publica código velho achando que é o
# novo — foi o que quase subiu o Modal sem as credenciais do R2. Confere antes.
if [ -f "conferir.sh" ] && [ -f ".entregue.sha" ]; then
  echo ""
  if ! bash conferir.sh; then
    echo ""
    echo "❌ Nada foi publicado."
    exit 1
  fi
fi

# ── venv ────────────────────────────────────────────────────────────────────
if [ -d ".venv" ]; then
  source .venv/bin/activate
  echo "✓ ambiente virtual ativado"
fi

# ── 1. testes ───────────────────────────────────────────────────────────────
# Se faltar alguma biblioteca de teste, avisa e segue: melhor publicar sem teste
# do que travar o deploy por causa de dependência de desenvolvimento.
echo ""
echo "── testes ─────────────────────────────────────────"
FALHOU=0
for t in test_segredos.py test_varvid.py test_bloqueio.py test_limites.py test_auth.py test_planos.py test_creditos.py test_indicacoes.py test_concorrencia.py test_saude.py test_e2e.py test_r2.py; do
  [ -f "$t" ] || continue
  printf "  %-20s " "$t"
  if SAIDA=$(python3 "$t" 2>&1); then
    echo "$SAIDA" | grep -E "passaram" | tail -1 | tr -d '\n'; echo ""
  else
    if echo "$SAIDA" | grep -qE "ModuleNotFoundError|ffmpeg não encontrado"; then
      echo "pulado (falta dependência de teste)"
    else
      echo "❌ FALHOU"
      echo "$SAIDA" | tail -15
      FALHOU=1
    fi
  fi
done
if command -v node >/dev/null 2>&1; then
  for t in test_front.js test_login.js; do
    [ -f "$t" ] || continue
    printf "  %-20s " "$t"
    if SAIDA=$(node "$t" 2>&1); then
      echo "$SAIDA" | grep -E "passaram" | tail -1 | tr -d '\n'; echo ""
    else
      echo "❌ FALHOU"
      echo "$SAIDA" | tail -15
      FALHOU=1
    fi
  done
else
  echo "  (node não encontrado — testes de tela pulados)"
fi

if [ "$FALHOU" = "1" ]; then
  echo ""
  echo "❌ Teste falhou — nada foi publicado."
  echo "   Corrija antes de subir, ou me mande a saída acima."
  exit 1
fi

# ── 2. Modal ────────────────────────────────────────────────────────────────
# Só republica se modal_app.py mudou: o build da imagem leva minutos e não faz
# sentido repetir quando a mudança foi só no app web.
echo ""
echo "── Modal ──────────────────────────────────────────"
# Comparar com o git era errado: depois de commitar, o arquivo "não mudou" e o
# deploy do Modal era pulado — foi assim que o Modal ficou com código velho
# enquanto o Render já esperava o formato novo. Agora guardamos a impressão
# digital do que foi realmente publicado.
MARCA=".modal-publicado"
HASH_ATUAL=$(shasum modal_app.py | awk '{print $1}')
HASH_PUBLICADO=$(cat "$MARCA" 2>/dev/null || echo "")

if [ "$HASH_ATUAL" = "$HASH_PUBLICADO" ]; then
  echo "  modal_app.py já publicado nesta versão — nada a fazer"
elif ! command -v modal >/dev/null 2>&1; then
  echo "🔴 PARE: o modal_app.py mudou mas o comando 'modal' não existe aqui."
  echo "   Publicar só o app web deixaria os dois lados incompatíveis"
  echo "   (o Modal mandaria o vídeo pro lugar errado e o usuário veria zero)."
  echo ""
  echo "   Ative o ambiente e rode:"
  echo "     source .venv/bin/activate && modal deploy modal_app.py"
  exit 1
else
  echo "  modal_app.py mudou — publicando (pode demorar alguns minutos)"
  modal deploy modal_app.py
  echo "$HASH_ATUAL" > "$MARCA"
  echo "✓ Modal atualizado"
fi

# ── 3. GitHub ───────────────────────────────────────────────────────────────
echo ""
echo "── GitHub ─────────────────────────────────────────"
if [ -z "$(git status --porcelain)" ]; then
  echo "  nada novo para commitar"
else
  git add -A
  echo "  arquivos no commit:"
  git diff --cached --name-only | sed 's/^/    /'
  # Trava de segurança: o repositório é público.
  if git diff --cached --name-only | grep -qE "supabase_config\.json|\.env$|\.pem$|\.pfx$"; then
    echo ""
    echo "🔴 BLOQUEADO: há arquivo de segredo no commit. Nada foi enviado."
    git reset >/dev/null
    exit 1
  fi
  git commit -m "$MSG"
fi

# O push vive FORA do if de propósito. Antes ele morava dentro, e por isso um
# commit já feito mas ainda não enviado nunca subia: sem arquivo modificado, o
# script dizia "nada novo para commitar" e pulava o push junto. A tela então
# mandava fazer o Deploy no Render — que republicava a MESMA versão, e tudo
# parecia ter funcionado.
PENDENTES=$(git rev-list --count @{u}..HEAD 2>/dev/null || echo "0")
if [ "$PENDENTES" = "0" ]; then
  echo "  nada a enviar — o GitHub já está em dia"
else
  echo "  enviando $PENDENTES commit(s) ao GitHub"
  git push
  echo "✓ enviado ao GitHub"
fi

# ── 4. o que falta ──────────────────────────────────────────────────────────
echo ""
echo "═══════════════════════════════════════════════════"
echo "  FALTA VOCÊ (no navegador):"
echo ""
echo "  1. Render → Varvid → Manual Deploy → Deploy latest commit"
echo ""
echo "  2. No log da subida, confira estas duas linhas:"
echo "       [BOOT] TTL=24.0h · varredura ..."
echo "       [BOOT] vídeos em: R2 · bucket varvid ..."
echo ""
echo "     Se disser 'disco local (R2 não configurado)',"
echo "     alguma variável não chegou ao Render."
echo "═══════════════════════════════════════════════════"
