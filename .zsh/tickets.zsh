# Pipeline registro de gastos — funciones del shell
# Ver ~/personal/registro-gastos/AGENTS.md

# Dashboard TUI — abre la app textual
tickets() {
  local PATH="/usr/bin:/bin:$PATH"
  /home/tcabrera/personal/registro-gastos/.venv/bin/python \
    /home/tcabrera/personal/registro-gastos/scripts/dashboard.py "$@"
}

# Forzar una corrida del timer ahora (debug)
tickets-process-now() {
  systemctl --user start tickets-process.service
  journalctl --user -u tickets-process.service -n 30 --no-pager
}

# Renovar JWT vía chrome-devtools (interactivo) — ver scripts/refresh-token.py
tickets-refresh-token() {
  /usr/bin/python3 /home/tcabrera/personal/registro-gastos/scripts/refresh-token.py
}

# Estado rápido del pipeline
tickets-status() {
  echo "=== timer ==="
  systemctl --user list-timers tickets-process.timer --no-pager
  echo
  echo "=== última corrida ==="
  journalctl --user -u tickets-process.service -n 8 --no-pager
  echo
  echo "=== DB ==="
  command sqlite3 /home/tcabrera/personal/registro-gastos/data/queue.db \
    "SELECT status, COUNT(*) FROM tickets GROUP BY status"
}
