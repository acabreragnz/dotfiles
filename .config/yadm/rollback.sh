#!/bin/bash
# Rollback del bootstrap a versión anterior

BACKUP_DIR="$HOME/.config/yadm"
LATEST_BACKUP=$(ls -t "$BACKUP_DIR"/bootstrap.backup-* 2>/dev/null | head -1)

if [ -n "$LATEST_BACKUP" ]; then
  echo "Restaurando desde: $LATEST_BACKUP"
  cp "$LATEST_BACKUP" "$BACKUP_DIR/bootstrap"
  echo "✓ Rollback completado"
  echo ""
  echo "Bootstrap restaurado a versión anterior."
  echo "Para verificar: head -10 ~/.config/yadm/bootstrap"
else
  echo "✗ No se encontró backup"
  echo "Backups disponibles en: $BACKUP_DIR"
  ls -la "$BACKUP_DIR"/bootstrap.backup-* 2>/dev/null || echo "  (ninguno)"
  exit 1
fi
