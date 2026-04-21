# Datos Personales

- **Ubicación**: Ciudad de la Costa, Uruguay — coordenadas casa: -34.840030, -55.971159 (zona Lagomar/Solymar). Usar para clima, distancias, servicios locales, Google Maps, etc.
- **Pareja**: Flor (guardada como "Amor" en WhatsApp)
- **Mascotas**: 2 perros — Auri y More
- **Situación laboral**: Empleado en relación de dependencia, pero factura como empresa (solo a esa empresa)
- **Horario laboral**: Flexible, tronco común 10:00–18:00. Almuerzo después de las 13:15.
- **Rubro**: Tecnología / software
- **Deporte**: Gym + running (hace carreras). Running: martes y jueves de 19:00 a 21:00 (clase grupal), y domingo (fondo largo, hora variable). Gym: lunes, miércoles y viernes a las 21:00; sábado de mañana (horario variable). 3 días por semana.
- **Profe de gym**: Facundo. La planilla de seguimiento está en Google Drive, se llama **"ANTHONY CABRERA"** (ID: `1IqUoa_xdi15ZV5k-mV4HUNWB2JG7YDj96RoSTzOyYSU`), compartida por él. Los pesos que Facu ve y controla están ahí.
- **Profe de running**: Mirco.
- **Vehículo**: BYD Seagull Surf (único auto)
- **Bancos**: BROU (principal) + Itaú (importante también)
- **Mutual**: COSEM
- **Fecha de nacimiento**: 19/12/1991
- **Hijos**: No

# Scripts personales

- **Ubicación:** `~/scripts/` — todos los scripts utilitarios propios van ahí (e.g. `pixelize.py`, `video_capture.py`).
- Siempre trackear con yadm: `yadm add scripts/<archivo>` → `yadm commit` → `yadm push`.
- **Preservar metadata de fecha original:** siempre que se edite o procese cualquier archivo multimedia (imágenes, videos, audios), restaurar el mtime original después de escribir el output — ya sea en scripts o en comandos ad-hoc. En Python: `mtime = os.stat(src).st_mtime` antes de procesar → `os.utime(dst, (mtime, mtime))` después de guardar. Con `touch`: `touch -r original destino`.
- **NUNCA modificar archivos multimedia in-place:** siempre generar un archivo de salida nuevo (ej: `archivo_out.mp4`, `archivo_cropped.png`). Nunca sobreescribir el original. El usuario decide qué hacer con el output.

# Herramientas y Preferencias Técnicas

- Preferir `jq` para parsear JSON en comandos `curl` simples. Usar `python3` solo si la lógica es compleja y `jq` se vuelve ilegible.
- **OSRM para tiempos de viaje:** usar `router.project-osrm.org` (gratis, sin API key) para calcular distancias y tiempos. Sin tráfico real → aplicar offset según franja horaria (ver `.claude/task-description-template.md` del vault). Formato: `curl -s "http://router.project-osrm.org/route/v1/driving/LON1,LAT1;LON2,LAT2?overview=false"`
- **jq — sintaxis correcta para filtrar campos:** usar siempre `{id: .id, name: .name}`, NO el shorthand `{id, name}` (falla en shell).
- **jq — Todoist API v1:** los listados devuelven `{"results": [...]}`, no array plano. Iterar con `.results[]`, no `.[]`.
- Cuando el usuario diga "usá Chrome" o similar, priorizar siempre `mcp__chrome-devtools__*` por defecto.
- **Notificaciones del sistema:** siempre que el usuario pida "notificame", "mandame un alerta" o similar, usar `pw-play /usr/share/sounds/freedesktop/stereo/message.oga 2>/dev/null && notify-send "título" "mensaje"`. `paplay` no está disponible en este sistema.
- **Búsqueda web:** priorizar siempre `mcp__exa__web_search_exa` sobre `WebSearch`. Usar WebSearch solo si Exa no está disponible.
- **Impresora:** Brother DCP-165C configurada via CUPS. Imprimir: `lp -d DCP165C "/path/to/archivo.pdf"`. Verificar estado: `lpstat -p`. **Siempre leer el PDF antes de imprimir** — puede ser el archivo equivocado o tener restricciones (ej: firma electrónica que pierde validez al imprimir).
- **Imágenes descargadas — NO leer sin verificar:** nunca usar la herramienta Read sobre un archivo `.png` (u otra imagen) descargado por Claude sin verificar primero que realmente es una imagen (`file <path>`). Hay un bug de Claude Code que causa loop infinito al intentar leer un archivo que no es imagen real.
- **Template de descripciones de tareas Todoist:** todo skill o flujo que cree o edite tareas debe seguir `.claude/task-description-template.md` del vault Obsidian (`~/personal/obsidian/second-brain/.claude/task-description-template.md`). Leer ese archivo antes de escribir cualquier descripción.
- **Cloudflare Quick Tunnel para dev servers:** cuando el usuario pida exponer un `localhost:PORT` (Vite, Storybook, Next dev, etc.), usar siempre `cloudflared tunnel --url http://localhost:PORT --http-host-header localhost:PORT`. El flag `--http-host-header` es **obligatorio** porque Vite/Storybook bloquean hosts no listados en `allowedHosts` y devuelven `403 Invalid host` sin él. Correr en background, esperar ~8s y extraer la URL con `grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com'` del output.

## Apps de uso frecuente

- **MoneyKeeper**: app de trackeo de gastos personales. Se usa principalmente en mobile, aunque tiene web con funcionalidades parciales (en desarrollo). Para labels GTD: usar `📱 telefono`, no `💻 digital`.

## Todoist — Tareas recurrentes

- **Antes de mover cualquier tarea**, verificar si es recurrente: `GET /api/v1/tasks/{id}` → `.due.is_recurring`.
- **`due_date` y `due_string` con fecha sola rompen la recurrencia** — no usarlos en tareas recurrentes.
- **Único método seguro: Sync API `item_update`** con el objeto `due` completo:
  ```json
  {"type": "item_update", "uuid": "...", "args": {"id": "TASK_ID", "due": {"date": "YYYY-MM-DD", "string": "every 3 weeks", "is_recurring": true}}}
  ```
  El campo `string` debe ser el patrón original (sin fecha), y `is_recurring: true` explícito.

## Todoist — Terminología

- Cuando el usuario dice **"mi calendar"** o **"el calendar"**, se refiere al proyecto **Calendar [GTD]** de Todoist (`6RP7pGXfqqwHM9hp`), NO a Google Calendar.

## Google Workspace CLI (`gws`)

- Instalado en `/home/tcabrera/.asdf/shims/gws` (v0.4.4)
- Usar para acceder a Google Drive, Sheets, Gmail, Calendar y demás servicios de Google Workspace.
- **Referencia completa con ejemplos y gotchas:** skill `/gws-workspace`
- **Regla clave:** `--params` = query parameters (URL), `--json` = request body. Metadata como `name`, `mimeType`, `parents` van en `--json`. IDs de recurso (`fileId`, `spreadsheetId`) van en `--params`. No existen flags individuales.
- **Buscar info antes de preguntar:** cuando haya datos disponibles en Gmail, Drive u otros servicios Google (montos, fechas, detalles de pedidos), buscarlos con `gws` en lugar de pedirle al usuario. Solo preguntar si la búsqueda no da resultados.
- **Siempre informar destino al mover/subir archivos:** después de cualquier operación que mueva o suba un archivo a Drive, indicar explícitamente la ruta completa donde quedó (ej: `📁 Inversiones > República Ganadera`).
- **Shortcuts en Drive para carpetas de viaje/proyecto:** no mover archivos de su carpeta canónica (Auto, Documentos de Identidad, Mascotas, etc.). Usar `mimeType: application/vnd.google-apps.shortcut` + `shortcutDetails.targetId` para crear accesos directos. La carpeta del viaje/proyecto solo tiene docs propios + shortcuts a los de referencia.
- **Re-auth (token revocado):** generar `/tmp/gws-login.sh` con `gws auth login --account acabreragnz@gmail.com --scopes "..."` (ver scopes completos en skill `gws-workspace`) y pedir al usuario `! bash /tmp/gws-login.sh`. Nunca pegar el comando directo — los scopes se parten en el chat.

# Zenity / Diálogos GUI

- **Altura de diálogos siempre calculada por cantidad de opciones** — no hardcodear valores chicos, y NUNCA debe aparecer scroll para listas cortas. Regla (valores generosos — zenity es avaro con el espacio real):
  - `--list` / `--radiolist` / `--checklist`: `altura = 280 + (N_opciones * 70)` px
  - `--forms`: `altura = 180 + (N_campos * 48)` px (los forms son más compactos que las listas)
  - Mínimo absoluto 320 px; sumar ~80 si hay texto descriptivo largo arriba.
  - Si dudás entre dos valores, elegí el más alto — diálogos apretados son peor UX que uno con aire extra.
  - Regla de oro: si para 3 opciones el diálogo muestra scroll, la altura está mal.

# Subagentes

- **Background por defecto**: correr subagentes con `run_in_background: true` salvo que el resultado sea bloqueante para el siguiente paso. Nunca dejar al usuario sin respuesta.
- **Ser proactivo**: usar subagentes para tareas pesadas (exploración, reviews, análisis) — ahorra tokens en el contexto principal y permite prompts especializados.
- **Paralelizar**: si hay tareas independientes, lanzar múltiples subagentes en un solo mensaje.
- **Ante la duda, preguntar**: si no es claro si foreground o background, preguntarle al usuario.

# Estilo de Interacción

- **Siempre dar recomendación al hacer preguntas:** cuando le preguntás algo al usuario (especialmente en brainstorming u opciones), incluir tu punto de vista antes de que lo pida. No esperar a que diga "qué recomendás".
- **Proponer opciones con ejemplos concretos:** cuando presentás alternativas, mostrar cómo se vería cada una en la práctica — no solo describirlas en abstracto.

# Obsidian

- **Vault:** `/home/tcabrera/personal/obsidian/second-brain/`
- **Inbox:** `0 - Inbox/` — carpeta de procesamiento GTD
- **TIL captures acumulados:** `0 - Inbox/til-captures.md`
- **TILs escritos:** `Work/TIL/` — archivos individuales `YYYY-MM-DD-tema.md`

# Búsqueda en Sesiones Anteriores

- Cuando el usuario mencione algo de una sesión anterior ("ayer te pedí...", "antes hablamos de...", "recordás cuando..."), buscar en memex **inmediatamente** — sin pedir contexto extra primero.
- Flujo: `memex index --source <project-path>` → `memex search "query"` → leer sesión relevante.
- Solo preguntar al usuario si la búsqueda exhaustiva en memex no devuelve resultados.

# Memoria y Preferencias

- Cuando el usuario pida recordar algo, SIEMPRE preguntar primero dónde guardarlo:
  - **MEMORY.md del proyecto** (memory/) — contexto específico del proyecto actual
  - **CLAUDE.md global** (~/.claude/CLAUDE.md) — instrucciones permanentes para todas las sesiones
- NUNCA guardar directamente sin consultar al usuario
- **Inline por defecto, archivo aparte solo si amerita — en cualquier destino:** cuando se guarda una regla/memoria/instrucción, va como bullet inline en el archivo destino elegido (sea `~/.claude/CLAUDE.md`, `MEMORY.md` del proyecto, `CLAUDE.md`/`AGENTS.md` del proyecto, o cualquier otro índice). Crear un archivo `.md` externo (y linkearlo desde el índice) solo si la entrada tiene suficiente detalle como para no caber en una o dos líneas: troubleshooting multi-paso, tablas de referencia, snippets de código, ejemplos extensos. Una regla corta con su "why" y "how to apply" siempre va inline, nunca en archivo aparte.

# Skills de Claude Code

- **Antes de crear o actualizar cualquier skill**, invocar el skill `/skill-guide` — contiene todas las best practices y convenciones de diseño.
- **Nombres de skills: siempre verbo accionable** — `automation-charge-oca`, no `automation-oca-splitwise`. El usuario tiene que corregirlo si se olvida.
- **Skills puros vs. orchestrators:** la lógica de negocio específica de una automatización (detección de condiciones, cálculos derivados, decisiones condicionales) va en el skill `automation-*` orchestrator, NO en el sub-skill puro. Los sub-skills (ej: `scotiabank`, `splitwise`) solo exponen operaciones atómicas reutilizables.

# Información y Documentación

- Siempre que tengas que instalar herramientas nuevas en el sistema operativo usa context7 mcp, en caso de no encontrar info, busca info actualizada en la web.

- **SIEMPRE busca información actualizada en la web** cuando:
  - Instalas herramientas o paquetes nuevos
  - Buscas URLs de descarga o instalación
  - Necesitas confirmar versiones o compatibilidad
  - No conocés la sintaxis exacta de una CLI, API o herramienta (buscar la documentación **antes** del primer intento, no ir a prueba y error)
  - El usuario te pide explícitamente "busca en la web"
  - No estás 100% seguro de la información

- **NUNCA inventes o asumas** información técnica sin verificar primero.
- Usa WebSearch para obtener información de 2026, no de tu conocimiento de 2025.

# Git — Resolución de Conflictos

- **Antes de resolver cualquier conflicto de rebase/merge**, revisar el PR activo del usuario (`gh api repos/.../pulls/<n>/files`) para entender qué cambios hizo. Comparar ambas versiones (HEAD = master, incoming = commit del usuario) y explicar el análisis antes de actuar. Nunca tomar una porción automáticamente sin ese paso previo.

# Pull Requests

- **Antes de editar el body de cualquier PR**, siempre leer el contenido actual completo primero (e.g. `gh pr view --json body -q .body`). Hacer edits quirúrgicos — nunca reescribir secciones que no cambiaron, nunca pisar imágenes ni contenido que el usuario agregó.
- **Después de cada `git push`**, si hay un PR abierto en esa branch, mostrar el link del PR al usuario (`gh pr view --json url -q .url`).

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