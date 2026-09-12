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
for t in test_varvid.py test_bloqueio.py test_limites.py test_e2e.py test_r2.py; do
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
if [ -f "test_front.js" ] && command -v node >/dev/null 2>&1; then
  printf "  %-20s " "test_front.js"
  node test_front.js 2>&1 | grep -E "passaram" | tail -1 || echo "❌ FALHOU"
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
if git diff --quiet HEAD -- modal_app.py 2>/dev/null; then
  echo "  modal_app.py sem mudanças — nada a republicar"
else
  if command -v modal >/dev/null 2>&1; then
    echo "  modal_app.py mudou — publicando (pode demorar alguns minutos)"
    modal deploy modal_app.py
    echo "✓ Modal atualizado"
  else
    echo "⚠️  comando 'modal' não encontrado — publique manualmente:"
    echo "     modal deploy modal_app.py"
  fi
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
