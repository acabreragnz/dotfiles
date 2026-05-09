# CLAUDE.md

Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.

---

# Datos Personales

Datos completos en: `~/personal/obsidian/second-brain/3 - Resources/Personal/Datos personales.md`

Leer ese archivo **antes de responder** cualquier pregunta que requiera datos de identidad, domicilio, contacto, vehículo, salud, talles o empresa unipersonal — sin esperar que el usuario lo pida explícitamente.

# Scripts personales

- **Ubicación:** `~/scripts/` — todos los scripts utilitarios propios van ahí (e.g. `pixelize.py`, `video_capture.py`).
- Siempre trackear con yadm: `yadm add scripts/<archivo>` → `yadm commit` → `yadm push`.
- **Preservar metadata de fecha original:** siempre que se edite o procese cualquier archivo multimedia (imágenes, videos, audios), restaurar el mtime original después de escribir el output — ya sea en scripts o en comandos ad-hoc. En Python: `mtime = os.stat(src).st_mtime` antes de procesar → `os.utime(dst, (mtime, mtime))` después de guardar. Con `touch`: `touch -r original destino`.
- **NUNCA modificar archivos multimedia in-place:** siempre generar un archivo de salida nuevo (ej: `archivo_out.mp4`, `archivo_cropped.png`). Nunca sobreescribir el original. El usuario decide qué hacer con el output.
- **Verificar scripts antes de cerrar:** siempre que cree o modifique un script (Python, bash, Nautilus wrapper, etc.), ejecutarlo con un input real y validar el output antes de reportar que funciona. **Why:** entregar "✓ funciona" sin haberlo corrido rompe la confianza — ya pasó con `timestamp` + GIF y con `video_label.py` generando `.mp4` en vez de `.gif`. **How to apply:** Python CLI → correr con archivo de prueba y chequear con `ls`/`file`/`ffprobe`; bash wrapper zenity → `bash -n` + probar el camino no-interactivo invocando el script Python con los args esperados; si algún camino no se puede testear (ej: GUI sin display), decirlo explícitamente, no inventar el "funciona".

# Scripts zsh interactivos (funciones, no utilities)

- **Ubicación canónica:** `~/.zsh/<nombre>.zsh` — funciones zsh sourceables (e.g. `ccwt.zsh`). NO van en `~/.oh-my-zsh/custom/` porque oh-my-zsh es un repo git propio y yadm no puede trackear archivos adentro (los trata como submódulo y silenciosamente los ignora, incluso con `-f`).
- **Auto-load por oh-my-zsh:** crear symlink `~/.oh-my-zsh/custom/<nombre>.zsh -> ~/.zsh/<nombre>.zsh`. Así oh-my-zsh los carga automático sin tocar `.zshrc`, y el archivo canónico vive afuera y es trackeable.
- **Trackear con yadm:** `yadm add .zsh/<archivo>.zsh` → commit → push. NO trackear el symlink (`~/.oh-my-zsh/custom/...`) — solo el canónico en `~/.zsh/`.
- **Diferencia con `~/scripts/`:** `~/scripts/` es para utilities ejecutables (Python, bash standalone) que se invocan como comandos. `~/.zsh/` es para funciones zsh que se cargan en el shell interactivo (definen funciones tipo `ccwt`, `cci`, etc.).
- **PATH defensivo en funciones que llaman binarios del sistema:** si la función usa `command awk`, `command rm`, etc., agregar al inicio `local PATH="/usr/bin:/bin:$PATH"`. **Why:** sesiones heredadas de `cc` pueden tener un PATH sin `/usr/bin`, rompiendo `command not found` mid-función. **How to apply:** sólo en funciones que ejecutan utilities del sistema; no necesario para funciones que sólo llaman a builtins zsh.

# Herramientas y Preferencias Técnicas

- Preferir `jq` para parsear JSON en comandos `curl` simples. Usar `python3` solo si la lógica es compleja y `jq` se vuelve ilegible.
- **Búsquedas estructurales → primera acción es `/ast-grep`, nunca `rg`/`grep`.** Si la query menciona cualquiera de estos, no hay debate: JSX con prop X, callers de `foo()`, imports de Y, métodos que llaman a Z, decorators, tipos que extienden Y, props específicas, spread vs literal. Reservá `rg` ÚNICAMENTE para texto plano (logs, paths, strings literales en docs/JSON); `grep` sólo si `rg` no está. Si la primera regla ast-grep no matchea, depurá con `ast-grep run --debug-query=cst` o ajustá `kind`/`has`/`stopBy` — **NO** caigas a `rg --multiline | awk | grep` (ensucia el contexto con basura multi-line y garantiza falsos positivos). Limitación: ast-grep no ve dentro de spread props (`{...obj}`), para eso tracear la fuente del spread a mano. Para la sintaxis de reglas, invocar el skill `/ast-grep`. **Why:** auditando call sites de `<Form.Checkbox justifyContent=…>` me fui directo a `rg` con post-filter de `awk`/`grep`, output ilegible, falsos positivos por multi-line; la regla canónica ya estaba escrita y la ignoré por costumbre. **How to apply:** antes de tipear `rg`/`grep`, parar y preguntar: "¿lo que busco depende de cómo se parsea el código?". Si sí → `/ast-grep`. Sin excepciones, sin "rapidito con grep".
- **OSRM para tiempos de viaje:** usar `router.project-osrm.org` (gratis, sin API key) para calcular distancias y tiempos. Sin tráfico real → aplicar offset según franja horaria (ver `.claude/task-description-template.md` del vault). Formato: `curl -s "http://router.project-osrm.org/route/v1/driving/LON1,LAT1;LON2,LAT2?overview=false"`
- **jq — sintaxis correcta para filtrar campos:** usar siempre `{id: .id, name: .name}`, NO el shorthand `{id, name}` (falla en shell).
- **jq — Todoist API v1:** los listados devuelven `{"results": [...]}`, no array plano. Iterar con `.results[]`, no `.[]`.
- Cuando el usuario diga "usá Chrome" o similar, priorizar siempre `mcp__chrome-devtools__*` por defecto.
- **Chrome DevTools MCP — pageId:** flag `--experimental-page-id-routing` activo, todos los tools page-scoped aceptan `pageId`. **Flujo siempre, incluso en single-agent / single-tab:** (1) abrir tab propia con `new_page` (nunca reusar una existente — no sabés de quién es); (2) `list_pages` y parsear el `N` de la línea de tu tab (`N: URL [selected]`) — ese es tu `pageId`; (3) pasar `pageId: N` en TODOS los tool calls siguientes; (4) cada agente es dueño exclusivo de su tab. **Why:** sin `pageId` los tools caen al "selected page" global del server y se pisan con subagentes paralelos o con tabs que abra el usuario. Reusar tabs ajenas pisa el trabajo de otro agente o del usuario. **How to apply:** sin excepciones — primer paso de cualquier tarea browser es `new_page` + `list_pages` para fijar tu pageId.
- **Chrome DevTools MCP — Screencast:** usar `screencast_start` / `screencast_stop` en tareas de debugging, flujos de automatización largos (3+ pasos), o verificación QA. No es necesario para checks rápidos puntuales.
- **Notificaciones del sistema:** siempre que el usuario pida "notificame", "mandame un alerta" o similar, usar `pw-play /usr/share/sounds/freedesktop/stereo/message.oga 2>/dev/null && notify-send "título" "mensaje"`. `paplay` no está disponible en este sistema.
- **Búsqueda web:** priorizar siempre `mcp__exa__web_search_exa` sobre `WebSearch`. Usar WebSearch solo si Exa no está disponible.
- **Impresora:** Brother DCP-165C configurada via CUPS. Imprimir: `lp -d DCP165C "/path/to/archivo.pdf"`. Verificar estado: `lpstat -p`. **Siempre leer el PDF antes de imprimir** — puede ser el archivo equivocado o tener restricciones (ej: firma electrónica que pierde validez al imprimir).
- **Imágenes descargadas — NO leer sin verificar:** nunca usar la herramienta Read sobre un archivo `.png` (u otra imagen) descargado por Claude sin verificar primero que realmente es una imagen (`file <path>`). Hay un bug de Claude Code que causa loop infinito al intentar leer un archivo que no es imagen real.
- **Capturas / evidencia de tickets — guardarlas en el directorio del ticket, no en `/tmp`:** todas las capturas (screenshots de QA, evidencia para PRs/Slack/diseño) van a la carpeta del ticket en curso (ej: `docs/tickets/<TICKET-ID>/` del repo activo). **Why:** las capturas que terminan en `/tmp` se pierden cuando se reinicia, no se versionan, y no quedan asociadas al contexto del ticket; ya pasó que tuve que recapturar porque las dejé en `/tmp` y desaparecieron entre sesiones. **How to apply:** `/tmp` solo para capturas descartables / probes intermedios que sé que no van a uso firme. Si la captura va a Jordan, a un PR, a Slack, o a la PR description → al directorio del ticket directamente desde el primer save.
- **Template de descripciones de tareas Todoist:** todo skill o flujo que cree o edite tareas debe seguir `.claude/task-description-template.md` del vault Obsidian (`~/personal/obsidian/second-brain/.claude/task-description-template.md`). Leer ese archivo antes de escribir cualquier descripción.
- **Cloudflare Quick Tunnel para dev servers:** cuando el usuario pida exponer un `localhost:PORT` (Vite, Storybook, Next dev, etc.), usar siempre `cloudflared tunnel --url http://localhost:PORT --http-host-header localhost:PORT`. El flag `--http-host-header` es **obligatorio** porque Vite/Storybook bloquean hosts no listados en `allowedHosts` y devuelven `403 Invalid host` sin él. Correr en background, esperar ~8s y extraer la URL con `grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com'` del output.
- **Comandos con `sudo` (bloqueados por hook):** cuando necesito que el usuario corra uno o más comandos con `sudo`, si es **un solo comando corto** pegarlo inline en el chat; si son **varios comandos o un flujo** (ej: agregar repo + `apt update` + `apt install`), generar un script en `/tmp/<nombre>.sh` con `set -euo pipefail` y pedirle al usuario `! bash /tmp/<nombre>.sh`. Mismo patrón que `/tmp/gws-login.sh` para re-auth de gws. **Why:** el hook `pre-tool-guard.sh` bloquea cualquier `sudo` que yo ejecute — el `!` prefix en el prompt corre el comando en la sesión y la salida me vuelve directo, sin que el usuario tenga que pegar output.

## Apps de uso frecuente

- **MoneyKeeper**: app de trackeo de gastos personales. Acceso via API web (`moneykeeperapp.misa.vn`) con el skill `money-keeper` — search/list/create/delete funcionan. Para labels GTD: usar `💻 digital` (ya no `📱 telefono`).

## Todoist — Tareas recurrentes

- **Antes de mover cualquier tarea**, verificar si es recurrente: `GET /api/v1/tasks/{id}` → `.due.is_recurring`.
- **`due_date` y `due_string` con fecha sola rompen la recurrencia** — no usarlos en tareas recurrentes.
- **Único método seguro: Sync API `item_update`** con el objeto `due` completo:
  ```json
  {"type": "item_update", "uuid": "...", "args": {"id": "TASK_ID", "due": {"date": "YYYY-MM-DD", "string": "every 3 weeks", "is_recurring": true}}}
  ```
  El campo `string` debe ser el patrón original (sin fecha), y `is_recurring: true` explícito.

## Todoist — Terminología

- 🚨 **SIEMPRE SIEMPRE SIEMPRE:** cuando el usuario dice **"calendar"**, **"mi calendar"**, **"el calendar"**, **"evento del calendar"** o cualquier variante, se refiere **EXCLUSIVAMENTE** al proyecto **Calendar [GTD]** de Todoist (`6RP7pGXfqqwHM9hp`). **NUNCA** a Google Calendar, **NUNCA** invocar `gws-calendar-*` skills ante esta palabra. Si necesita Google Calendar lo va a decir explícito ("Google Calendar", "gcal"). Ante la duda → Todoist, no preguntar.

## Google Workspace CLI (`gws`)

- Usar para acceder a Google Drive, Sheets, Gmail, Calendar y demás servicios de Google Workspace.
- **Referencia completa con ejemplos y gotchas:** skill `/gws-workspace` (sintaxis, subcomandos y reglas de `--params`/`--json` están ahí y en los skills oficiales `gws-*`).
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
- **Siempre `mode: "bypassPermissions"`**: pasar este mode en todos los lanzamientos de agentes para que tengan acceso a Read/Bash/Write sin bloqueos. **Why:** sin él los subagentes fallan silenciosamente al intentar leer archivos, lo que es peor que no lanzarlos. **How to apply:** sin excepciones — es el default correcto para todos los Agent tool calls.

# Estilo de Interacción

- **Siempre dar recomendación al hacer preguntas:** cuando le preguntás algo al usuario (especialmente en brainstorming u opciones), incluir tu punto de vista antes de que lo pida. No esperar a que diga "qué recomendás".
- **Proponer opciones con ejemplos concretos:** cuando presentás alternativas, mostrar cómo se vería cada una en la práctica — no solo describirlas en abstracto.
- **Cuando el usuario comparte algo que aprendió, educar proactivamente:** explicar el "por qué" detrás del concepto, implicaciones, contexto técnico — no solo transcribirlo o capturarlo. **Why:** el usuario lo señaló explícitamente: "no me educaste un choto". **How to apply:** ante cualquier aprendizaje compartido, profundizar en los mecanismos subyacentes antes de ofrecer capturarlo.

# Obsidian

- **Vault:** `/home/tcabrera/personal/obsidian/second-brain/`
- **Inbox:** `0 - Inbox/` — carpeta de procesamiento GTD
- **TIL captures acumulados:** `0 - Inbox/til-captures.md`
- **TILs escritos:** `Work/TIL/` — archivos individuales `YYYY-MM-DD-tema.md`

# Búsqueda en Sesiones Anteriores

- Cuando el usuario mencione algo de una sesión anterior ("ayer te pedí...", "antes hablamos de...", "recordás cuando..."), buscar en memex **inmediatamente** — sin pedir contexto extra primero.
- Flujo: `memex index --source <project-path>` → `memex search "query"` → leer sesión relevante.
- Solo preguntar al usuario si la búsqueda exhaustiva en memex no devuelve resultados.

# Standard AGENTS.md / `.agents/`

- **AGENTS.md es canónico, CLAUDE.md siempre symlink** (mismo patrón para `.agents/skills/` ↔ `.claude/skills/`). Aplica a proyectos nuevos, `/init`, skills nuevos, y cualquier edit a un CLAUDE.md/skill que todavía sea archivo real (migrar antes de editar). En el contenido nunca mencionar "CLAUDE.md" — usar "AGENTS.md". Detalle operativo (snippets bash, casos límite, reglas de contenido): `~/.claude/agents-standard.md` — leer ese archivo antes de crear/migrar instrucciones o skills.

# Memoria y Preferencias

- Cuando el usuario pida recordar algo, SIEMPRE preguntar primero dónde guardarlo:
  - **MEMORY.md del proyecto** (memory/) — contexto específico del proyecto actual
  - **AGENTS.md global** (`~/AGENTS.md`, symlinkeado desde `~/.claude/CLAUDE.md`) — instrucciones permanentes para todas las sesiones
- **Cuando el usuario dice "memory" (o "memoria") se refiere a `AGENTS.md`**, NO al directorio `memory/` ni a `MEMORY.md`. Ante la duda, preguntar global (`~/AGENTS.md`) vs. proyecto (`AGENTS.md` del repo).
- NUNCA guardar directamente sin consultar al usuario
- **Inline por defecto, archivo aparte solo si amerita — en cualquier destino:** cuando se guarda una regla/memoria/instrucción, va como bullet inline en el archivo destino elegido (sea `~/AGENTS.md`, `MEMORY.md` del proyecto, `AGENTS.md` del proyecto, o cualquier otro índice). Crear un archivo `.md` externo (y linkearlo desde el índice) solo si la entrada tiene suficiente detalle como para no caber en una o dos líneas: troubleshooting multi-paso, tablas de referencia, snippets de código, ejemplos extensos. Una regla corta con su "why" y "how to apply" siempre va inline, nunca en archivo aparte.

# Skills de Claude Code

- **Antes de crear o actualizar cualquier skill**, invocar el skill `/skill-guide` — contiene todas las best practices y convenciones de diseño.
- **Nombres de skills: siempre verbo accionable** — `automation-charge-oca`, no `automation-oca-splitwise`. El usuario tiene que corregirlo si se olvida.
- **Skills puros vs. orchestrators:** la lógica de negocio específica de una automatización (detección de condiciones, cálculos derivados, decisiones condicionales) va en el skill `automation-*` orchestrator, NO en el sub-skill puro. Los sub-skills (ej: `scotiabank`, `splitwise`) solo exponen operaciones atómicas reutilizables.
- **`~/.claude/skills/<name>/` son symlinks a nivel DIRECTORIO a `~/.agents/skills/<name>/`** — es decir, el directorio entero del skill es el symlink, no el `SKILL.md` adentro. Por eso `readlink ~/.claude/skills/<name>/SKILL.md` devuelve vacío (el archivo en sí no es symlink) pero `readlink ~/.claude/skills/<name>` sí muestra el target. **Why:** ya pasó — asumí que `.claude/.../SKILL.md` y `.agents/.../SKILL.md` eran archivos independientes basándome en `diff … && echo SAME` (que solo prueba contenido idéntico, no estructura). Hice `rm ~/.claude/skills/daily/SKILL.md && ln -s ~/.agents/skills/daily/SKILL.md ~/.claude/skills/daily/SKILL.md` "para migrar a symlink", pero como el directorio padre ya era symlink, `rm` borró el canónico real y `ln -s` creó un **self-symlink** (`/home/.../.agents/.../SKILL.md -> /home/.../.agents/.../SKILL.md`) que rompió todo con `ELOOP`. **How to apply:** (1) editar cualquiera de los dos paths funciona — es el mismo archivo físico; (2) NUNCA `rm` + `ln -s` entre estos dos árboles — el dir padre ya es symlink, te vas a borrar el canónico y crear un loop; (3) antes de asumir estructura, `ls -la ~/.claude/skills/<name>` (no el SKILL.md, el directorio) para ver el symlink; (4) si ves un self-symlink `X -> X`, borrar y `Write` directo en `~/.agents/skills/<name>/SKILL.md` (el path canónico).

# Skills — Fases Conversacionales

- **Cuando un skill tenga una fase conversacional explícita antes de ejecutar, respetar ese contrato:** hacer solo la pregunta indicada y esperar. No lanzar agentes, no escribir borradores, no "adelantar" trabajo. Avanzar un paso a la vez, igual que `/brainstorming`. **Why:** el default de "hacer" override el flujo del skill — ya pasó con `/write-til`, donde lancé un agente de research y empecé a redactar antes de terminar el diálogo. **How to apply:** si el skill devuelve una pregunta sin haber terminado la fase de entendimiento, la única acción válida es esperar la respuesta del usuario antes de ejecutar cualquier herramienta.

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

# Git

- **Restaurar un archivo a versión de master: `git restore --source=origin/master -- <file>`** — nunca `git checkout`, que está bloqueado por el hook de permisos (se interpreta como branch switching). **How to apply:** cualquier vez que haya que revertir un archivo puntual a master, usar este comando.
- **Antes de resolver cualquier conflicto de rebase/merge**, revisar el PR activo del usuario (`gh api repos/.../pulls/<n>/files`) para entender qué cambios hizo. Comparar ambas versiones (HEAD = master, incoming = commit del usuario) y explicar el análisis antes de actuar. Nunca tomar una porción automáticamente sin ese paso previo.
- **Resolución de conflictos — siempre de a un archivo a la vez con la Edit tool.** Nada de scripts bulk (sed/awk/python/loops) aunque los archivos sigan el mismo patrón. **Why:** el usuario quiere ver con sus propios ojos qué queda en cada archivo antes de stagear. **How to apply:** grep/status está bien para inspeccionar, pero cada resolución va con Edit individual mostrando el `old_string` completo del bloque `<<<<<<<...=======...>>>>>>>` y el `new_string` resultante.

# Pull Requests

- **Antes de editar el body de cualquier PR**, siempre leer el contenido actual completo primero (e.g. `gh pr view --json body -q .body`). Hacer edits quirúrgicos — nunca reescribir secciones que no cambiaron, nunca pisar imágenes ni contenido que el usuario agregó.
- **Después de cada `git push`**, si hay un PR abierto en esa branch, mostrar el link del PR al usuario (`gh pr view --json url -q .url`).

# Sistemas externos — autorización explícita

- **NUNCA crear, modificar, comentar, asignar, etiquetar, ni cambiar de estado nada en sistemas externos sin autorización explícita y específica del usuario.** Aplica a: Linear (issues, comentarios, proyectos, status), GitHub (PRs, issues, reviews, comentarios), Slack, Todoist, Google Workspace, cualquier MCP de un servicio externo. **Why:** una acción en un sistema externo es visible para terceros (compañeros, stakeholders) y suele ser difícil de revertir limpiamente; el daño reputacional y de coordinación es alto. Ya pasó: creé ENG-4743 sin pedir permiso después de proponer un plan en el que mencionaba "crear ticket follow-up" — el usuario interpretó el plan como discusión, no como autorización. **How to apply:** un plan o propuesta NO es autorización; "OK al plan" tampoco lo es para acciones externas a menos que el usuario haya aceptado explícitamente esa acción puntual. Antes de cada acción externa, parar y pedir luz verde puntual ("¿creo el ticket?", "¿comento el PR?"). Si la duda es si una acción cuenta como "externa", asumí que sí.

# Dotfiles

- Siempre que modifique un dotfile trackeado por yadm, ejecutar el flujo completo: `yadm add`, `yadm commit` y `yadm push`.

# Shell — Claude CLI

- **`cc` es función en `~/.zshrc`**, no alias (así expande dentro de otras funciones zsh). Derivados (`ccp`, `ccc`, etc.) son aliases encima de `cc`.
- **Lanzar Claude desde scripts/funciones siempre con `cc`**, nunca `claude` raw. Aplica a `ccwt`, `cci` y cualquier helper nuevo.
- **Worktrees abren sesión nueva** — `ccwt` entra con `cc` sin `--continue`.

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