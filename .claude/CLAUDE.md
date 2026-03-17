# Datos Personales

- **Ubicación**: Ciudad de la Costa, Uruguay (usar para clima, distancias, servicios locales, etc.)
- **Pareja**: Flor
- **Mascotas**: 2 perros — Auri y More
- **Situación laboral**: Empleado en relación de dependencia, pero factura como empresa (solo a esa empresa)
- **Horario laboral**: Flexible, tronco común 10:00–18:00. Almuerzo después de las 13:15.
- **Rubro**: Tecnología / software
- **Deporte**: Gym + running (hace carreras). Running: martes y jueves de 19:00 a 21:00 (clase grupal), y domingo (fondo largo, hora variable). Gym: lunes, miércoles y viernes o sábado (3 días por semana).
- **Profe de gym**: Facundo. La planilla de seguimiento está en Google Drive, se llama **"ANTHONY CABRERA"** (ID: `1IqUoa_xdi15ZV5k-mV4HUNWB2JG7YDj96RoSTzOyYSU`), compartida por él. Los pesos que Facu ve y controla están ahí.
- **Profe de running**: Mirco.
- **Vehículo**: BYD Seagull Surf (único auto)
- **Bancos**: BROU (principal) + Itaú (importante también)
- **Mutual**: COSEM
- **Fecha de nacimiento**: 19/12/1991
- **Hijos**: No

# Herramientas y Preferencias Técnicas

- Preferir `jq` para parsear JSON en comandos `curl` simples. Usar `python3` solo si la lógica es compleja y `jq` se vuelve ilegible.
- **jq — sintaxis correcta para filtrar campos:** usar siempre `{id: .id, name: .name}`, NO el shorthand `{id, name}` (falla en shell).
- **jq — Todoist API v1:** los listados devuelven `{"results": [...]}`, no array plano. Iterar con `.results[]`, no `.[]`.
- Cuando el usuario diga "usá Chrome" o similar, priorizar siempre `mcp__chrome-devtools__*` por defecto.
- **Sonido en notificaciones:** usar `pw-play /usr/share/sounds/freedesktop/stereo/message.oga 2>/dev/null` antes de `notify-send`. `paplay` no está disponible en este sistema.
- **Búsqueda web:** priorizar siempre `mcp__exa__web_search_exa` sobre `WebSearch`. Usar WebSearch solo si Exa no está disponible.

## Apps de uso frecuente

- **MoneyKeeper**: app de trackeo de gastos personales. Se usa principalmente en mobile, aunque tiene web con funcionalidades parciales (en desarrollo). Para labels GTD: usar `📱 telefono`, no `💻 digital`.

## Todoist — Terminología

- Cuando el usuario dice **"mi calendar"** o **"el calendar"**, se refiere al proyecto **Calendar [GTD]** de Todoist (`6RP7pGXfqqwHM9hp`), NO a Google Calendar.

## Google Workspace CLI (`gws`)

- Instalado en `/home/tcabrera/.asdf/shims/gws` (v0.4.4)
- Usar para acceder a Google Drive, Sheets, Gmail, Calendar y demás servicios de Google Workspace.
- **Referencia completa con ejemplos y gotchas:** skill `/gws-workspace`
- **Regla clave:** todos los parámetros van en `--params` como JSON. No existen flags individuales (`--folder-id`, `--spreadsheet-id`, etc.).
- **Buscar info antes de preguntar:** cuando haya datos disponibles en Gmail, Drive u otros servicios Google (montos, fechas, detalles de pedidos), buscarlos con `gws` en lugar de pedirle al usuario. Solo preguntar si la búsqueda no da resultados.

# Estilo de Interacción

- **Siempre dar recomendación al hacer preguntas:** cuando le preguntás algo al usuario (especialmente en brainstorming u opciones), incluir tu punto de vista antes de que lo pida. No esperar a que diga "qué recomendás".
- **Proponer opciones con ejemplos concretos:** cuando presentás alternativas, mostrar cómo se vería cada una en la práctica — no solo describirlas en abstracto.

# Obsidian

- **Vault:** `/home/tcabrera/personal/obsidian/second-brain/`
- **Inbox:** `0 - Inbox/` — carpeta de procesamiento GTD
- **TIL captures acumulados:** `0 - Inbox/til-captures.md`
- **TILs escritos:** `Work/TIL/` — archivos individuales `YYYY-MM-DD-tema.md`

# Memoria y Preferencias

- Cuando el usuario pida recordar algo, SIEMPRE preguntar primero dónde guardarlo:
  - **MEMORY.md del proyecto** (memory/) — contexto específico del proyecto actual
  - **CLAUDE.md global** (~/.claude/CLAUDE.md) — instrucciones permanentes para todas las sesiones
- NUNCA guardar directamente sin consultar al usuario

# Skills de Claude Code

- **Antes de crear o actualizar cualquier skill**, invocar el skill `/skill-guide` — contiene todas las best practices y convenciones de diseño.
- **Nombres de skills: siempre verbo accionable** — `automation-charge-oca`, no `automation-oca-splitwise`. El usuario tiene que corregirlo si se olvida.

# Información y Documentación

- Siempre que tengas que instalar herramientas nuevas en el sistema operativo usa context7 mcp, en caso de no encontrar info, busca info actualizada en la web.

- **SIEMPRE busca información actualizada en la web** cuando:
  - Instalas herramientas o paquetes nuevos
  - Buscas URLs de descarga o instalación
  - Necesitas confirmar versiones o compatibilidad
  - El usuario te pide explícitamente "busca en la web"
  - No estás 100% seguro de la información

- **NUNCA inventes o asumas** información técnica sin verificar primero.
- Usa WebSearch para obtener información de 2026, no de tu conocimiento de 2025.

# Pull Requests

- **Antes de editar el body de cualquier PR**, siempre leer el contenido actual completo primero (e.g. `gh pr view --json body -q .body`). Hacer edits quirúrgicos — nunca reescribir secciones que no cambiaron, nunca pisar imágenes ni contenido que el usuario agregó.

# Dotfiles

- Siempre que modifique un dotfile trackeado por yadm, ejecutar el flujo completo: `yadm add`, `yadm commit` y `yadm push`.

# Teléfono (Samsung Galaxy S24+)

- Cuando el usuario dice "usa mi teléfono" o similar, conectar via agent-device WiFi:
  1. `adb connect 192.168.1.19:40545` (verificar con `adb devices` primero)
  2. `agent-device open --platform android --serial 192.168.1.19:40545`
  3. Usar `--serial 192.168.1.19:40545` en todos los comandos
- IP/puerto pueden cambiar al reiniciar wireless debugging — si falla, pedir nuevos datos
- Usar `--json` con `screenshot` para obtener el path del archivo
- Siempre `agent-device close` antes de abrir sesión con serial diferente

# Mejora Proactiva de Skills

Durante la ejecución de un skill, si ocurre un error, bloqueo o comportamiento no cubierto:
- **No interrumpir el flujo** — anotar internamente el problema y continuar.
- Al finalizar el objetivo principal → reportar los errores encontrados y proponer actualizaciones a los skills afectados.
- Esperar aprobación del usuario antes de editar cualquier skill.

Al finalizar **todas las tareas pendientes** de una interacción que involucró un skill, si ocurrió:
- Un "no happy path" (error, bloqueo, reintento inesperado)
- Una corrección o queja del usuario
- Un comportamiento nuevo no cubierto por el skill

→ Proponer al usuario las mejoras identificadas (qué skill actualizar y por qué) antes de cerrar.
→ Si confirma → aplicar los cambios inmediatamente.
→ Actualizar el skill más específico afectado. Destino: sección `## Troubleshooting` (crearla si no existe).