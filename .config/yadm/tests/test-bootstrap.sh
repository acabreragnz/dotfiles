#!/bin/bash
# Suite de testing para bootstrap

set -e

BOOTSTRAP="${1:-$HOME/.config/yadm/bootstrap.new}"
TESTS_PASSED=0
TESTS_FAILED=0

test_result() {
  if [ $? -eq 0 ]; then
    echo "✓ $1"
    TESTS_PASSED=$((TESTS_PASSED + 1))
  else
    echo "✗ $1"
    TESTS_FAILED=$((TESTS_FAILED + 1))
  fi
}

echo "=========================================="
echo "Bootstrap Testing Suite"
echo "Testing: $BOOTSTRAP"
echo "=========================================="
echo ""

# Test 1: Sintaxis válida
bash -n "$BOOTSTRAP"
test_result "Sintaxis válida"

# Test 2: set -e presente
grep -q "^set -e" "$BOOTSTRAP"
test_result "set -e presente"

# Test 3: set -o pipefail presente
grep -q "^set -o pipefail" "$BOOTSTRAP"
test_result "set -o pipefail presente"

# Test 4: NVM master branch
grep -q "nvm-sh/nvm/master" "$BOOTSTRAP"
test_result "NVM master branch"

# Test 5: Cursor URL dinámica
grep -q "cursor.com/api/download" "$BOOTSTRAP"
test_result "Cursor URL dinámica"

# Test 6: Función log
grep -q "^log()" "$BOOTSTRAP"
test_result "Función log presente"

# Test 7: apt update consolidado
count=$(grep -c "sudo apt update" "$BOOTSTRAP" || echo 0)
[ "$count" -le 3 ]
test_result "apt update consolidado ($count llamadas, max 3)"

# Test 8: check_dependencies
grep -q "check_dependencies()" "$BOOTSTRAP"
test_result "check_dependencies presente"

# Test 9: Trap cleanup
grep -q "trap.*cleanup" "$BOOTSTRAP"
test_result "trap cleanup"

# Test 10: chsh con manejo de errores
grep -q "if chsh" "$BOOTSTRAP"
test_result "chsh con error handling"

# Test 11: Arquitectura check
grep -q "dpkg --print-architecture" "$BOOTSTRAP"
test_result "Check de arquitectura"

# Test 12: Progress counters
grep -q "step()" "$BOOTSTRAP"
test_result "Progress counters (step)"

# Test 13: NVM verification
grep -q "command -v nvm" "$BOOTSTRAP"
test_result "Verificación NVM"

# Test 14: Headers organizacionales
section_count=$(grep -c "^# ====" "$BOOTSTRAP" || echo 0)
[ "$section_count" -ge 10 ]
test_result "Headers organizacionales ($section_count secciones)"

# Test 15: ensure_apt_updated function
grep -q "ensure_apt_updated()" "$BOOTSTRAP"
test_result "Función ensure_apt_updated"

# Test 16: cleanup function
grep -q "cleanup()" "$BOOTSTRAP"
test_result "Función cleanup"

# Test 17: Fingerprint auth section
grep -q "setup-fingerprint-auth.sh" "$BOOTSTRAP"
test_result "Sección autenticación biométrica"

# Test 18: TOTAL_STEPS correcto
grep -q "TOTAL_STEPS=14" "$BOOTSTRAP"
test_result "TOTAL_STEPS=14"

# Test 19: LOG_FILE definido
grep -q "LOG_FILE=" "$BOOTSTRAP"
test_result "LOG_FILE definido"

echo ""
echo "=========================================="
echo "Resultados: $TESTS_PASSED passed, $TESTS_FAILED failed"
echo "=========================================="

if [ $TESTS_FAILED -gt 0 ]; then
  exit 1
fi
