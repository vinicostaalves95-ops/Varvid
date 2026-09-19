#!/usr/bin/env bash
# Sobe os mockups em http://localhost:5002 e abre no navegador.
# Uso:  bash ~/Projetos/varvid/design/ver.sh        (ou passe outra porta: ver.sh 5003)
#
# Roda em paralelo ao app: a 5001 continua sendo o local_app.py, esta é só HTML estático.
# Para parar: Ctrl+C.

set -e
cd "$(dirname "$0")"

PORTA="${1:-5002}"

# Se a porta já estiver ocupada, anda para a próxima livre em vez de falhar.
while lsof -i ":$PORTA" -sTCP:LISTEN -t >/dev/null 2>&1; do
  echo "porta $PORTA ocupada, tentando $((PORTA + 1))…"
  PORTA=$((PORTA + 1))
done

echo ""
echo "  varvid · design"
echo "  ───────────────────────────────────────────"
echo "  índice ......... http://localhost:$PORTA/"
echo "  canvas ......... http://localhost:$PORTA/varvid-identidade-visual.html"
echo ""
echo "  o app continua na 5001, sem conflito"
echo "  Ctrl+C para parar"
echo ""

# Abre o navegador assim que o servidor responder.
( sleep 1; open "http://localhost:$PORTA/" 2>/dev/null || true ) &

python3 -m http.server "$PORTA" --bind 127.0.0.1
