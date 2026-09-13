#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
#  VarVid — confere se os arquivos entregues continuam íntegros
#
#  Uso:   bash conferir.sh
#
#  POR QUE ISTO EXISTE
#  Cinco vezes nesta pasta um arquivo gravado voltou sozinho para a versão
#  anterior — sempre arquivos que o git já rastreia; os novos nunca se perderam.
#  Uma dessas reversões quase publicou o Modal sem as credenciais do R2, cujo
#  sintoma seria download quebrado sem causa aparente.
#
#  O problema não é a reversão em si: é ela ser SILENCIOSA. Você commita achando
#  que subiu a correção, e subiu a versão velha.
#
#  Este script compara os arquivos com as impressões digitais gravadas em
#  .entregue.sha no momento da entrega. Se algum não bater, ele diz qual.
# ─────────────────────────────────────────────────────────────────────────────

cd "$(dirname "$0")"
MANIFESTO=".entregue.sha"

if [ ! -f "$MANIFESTO" ]; then
  echo "ℹ️  Não há entrega registrada ($MANIFESTO não existe)."
  echo "   Nada a conferir — siga normalmente."
  exit 0
fi

echo "── conferindo os arquivos entregues ───────────────"
PROBLEMAS=0
TOTAL=0

while read -r hash_esperado arquivo; do
  [ -z "$arquivo" ] && continue
  TOTAL=$((TOTAL + 1))
  if [ ! -f "$arquivo" ]; then
    printf "  ✗ %-22s SUMIU\n" "$arquivo"
    PROBLEMAS=$((PROBLEMAS + 1))
    continue
  fi
  hash_atual=$(shasum "$arquivo" | awk '{print $1}')
  if [ "$hash_atual" = "$hash_esperado" ]; then
    printf "  ✓ %-22s ok\n" "$arquivo"
  else
    printf "  ✗ %-22s DIFERENTE do que foi entregue\n" "$arquivo"
    PROBLEMAS=$((PROBLEMAS + 1))
  fi
done < "$MANIFESTO"

echo ""
if [ "$PROBLEMAS" = "0" ]; then
  echo "✓ os $TOTAL arquivos estão íntegros — pode commitar"
  exit 0
fi

echo "🔴 $PROBLEMAS de $TOTAL arquivo(s) não batem com o que foi entregue."
echo ""
echo "   Provavelmente voltaram para a versão anterior. NÃO commite —"
echo "   você subiria código velho achando que subiu a correção."
echo ""
echo "   Me avise quais arquivos falharam que eu reenvio."
exit 1
