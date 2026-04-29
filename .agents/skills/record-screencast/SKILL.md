---
name: record-screencast
description: Use when the user asks to record, screencast, or capture a browser interaction as a video — for QA evidence, bug reproductions, demos, or any time the user wants to *see* a browser flow play back. Trigger ANY time the user combines a browser action (click, navigate, interact) with words like "video", "screencast", "grabá", "grabámelo", "mostrámelo", "muestramelo", "filmá", "capturá", "registra". Concrete triggers: "hacé click en X y mostrámelo en video", "muestramelo en video", "grabá el flujo", "grabá los clicks", "registra mis clicks", "hacé un video de X", "screencast con clicks visibles", "capturá lo que clickeo", "filmá la interacción", "quiero verlo en video", "armame un video de X". If the user asks for a browser action AND mentions video/screencast/grabar/mostrar-en-video in the same request, use this skill — do NOT use chrome-devtools MCP tools directly.
argument-hint: 'URL inicial (o descripción del flujo)'
---

## Context

- Trim utility: `~/scripts/trim-screencast.py`
- Overlay JS: `references/click-overlay.js`
- Requiere flags MCP `--experimental-page-id-routing` y `--experimentalScreencast` (ya activos en `~/.claude.json`).

## Task

Grabar un screencast de Chrome via MCP con anillos rojos en cada click y entregar el video con tiempos muertos recortados.

Argumento: 

### Step 1 — Claim de tab propia

`new_page(url, background:true)` → `list_pages` → parsear el `N` de la línea cuya URL coincide con la recién abierta → ese es tu `pageId`. Pasarlo en TODOS los tool calls siguientes (regla de `~/AGENTS.md`).

### Step 2 — Inyectar overlay

Leer `references/click-overlay.js` y ejecutar su contenido con `mcp__chrome-devtools__evaluate_script({pageId, function: <contenido>})`. Devuelve `'overlay-installed'` (o `'already-installed'`).

El overlay aporta tres elementos al video:
- **Anillo rojo en cada click** (1s pulse, centrado en el coord del CDP).
- **Banner grande bottom-center** con dos estados explícitos para evitar ambigüedad sobre si la URL es la actual o el destino:
  - **Idle (`ON /current`)**: pill oscuro con label azul "ON" + path actual.
  - **Navigating (`NAVIGATING /from → /to`)**: pill azul brillante con label amarillo "NAVIGATING" + URL anterior tachada + flecha animada + URL destino. Dura 1.8s y vuelve a idle con el path nuevo.
  Reemplaza la barra del navegador, que el screencast del CDP no captura.
- **Progress bar al tope** (gradient azul-amarillo) que corre 0→100% en ~800ms en cada navegación, simulando el indicador de carga del browser.

Re-injectar después de cada `navigate_page` — el overlay se pierde en cada navegación. Las navegaciones SPA (clicks que cambian la ruta sin recargar) NO requieren re-inject; el banner se actualiza solo via polling cada 250ms.

### Step 3 — Grabar

```
screencast_start({pageId, filePath: "/tmp/<nombre>.webm"})
# acciones via tools MCP, todas con pageId — usar `mcp__chrome-devtools__click`
# para que el marker aparezca centrado (clicks programáticos `el.click()`
# sin coords dibujan en (0,0))
screencast_stop({pageId})
```

### Step 4 — Trim

```
python3 ~/scripts/trim-screencast.py /tmp/<nombre>.webm /tmp/<nombre>-trimmed.webm
```

Tunables:
- `--threshold` (default `0.05`) — subir a `0.10` para UIs con animación de fondo permanente (loaders, pulsos, tooltips animados). Bajar a `0.02` si el trim pierde animaciones sutiles.
- `--gap-frames` (default `30` ≈ 1.2s) — subir a 50-60 si hay texto que leer.

### Step 5 — Mostrar al usuario

- Reportar duración/tamaño antes y después y % de reducción.
- Abrir el video con `xdg-open /tmp/<nombre>-trimmed.webm`.
- Generar contact sheet (1 frame por segundo) y mostrarlo con Read:
  ```
  ffmpeg -y -i /tmp/<nombre>-trimmed.webm \
    -vf "fps=1,scale=480:-1,tile=<cols>x1:padding=4:color=white" \
    /tmp/<nombre>-contact.png
  ```
  donde `<cols>` = `ceil(duración)`.

## Troubleshooting

- **`new_page` timeout cuando la app redirige a un IdP (Auth0, SSO, etc.):** la sesión del proveedor de auth no siempre se hereda en tabs nuevas (third-party cookies bloqueadas por defecto en Chrome moderno). Pedir al usuario que haga login manualmente en la tab abierta y reintentar `navigate_page` a la URL real con `timeout: 30000`.
- **Marker dibujado en (0,0):** un click programático `el.click()` no incluye coords. Usar siempre `mcp__chrome-devtools__click` (CDP `Input.dispatchMouseEvent`) — sí incluye `clientX/Y`.
- **Trim recorta demasiado o muy poco:** ajustar `--threshold`. Si la UI tiene loaders/pulsos permanentes, sube el floor del MAD; subí el threshold por encima del floor (medirlo con `--keep-frames` y un script ad-hoc si hace falta).
