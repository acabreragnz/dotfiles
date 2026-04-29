---
name: record-clicks
description: Use when the user asks to record, screencast, or capture a browser flow with visible clicks — for QA evidence, bug reproductions, or demos. Triggers on "grabá los clicks", "registra mis clicks", "hacé un video del flujo", "screencast con clicks visibles", "capturá lo que clickeo", or any request to produce a video showing where clicks happen in a browser.
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

Re-injectar después de cada `navigate_page` — el overlay se pierde en cada navegación.

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
- `--threshold` (default `0.05`) — subir a `0.10` para UIs ricas con animación de fondo (Lift, dashboards). Bajar a `0.02` si pierde animaciones sutiles.
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

- **`new_page` timeout en localhost:3001 → redirect a Auth0:** la sesión Auth0 no se hereda en tabs nuevas (third-party cookies bloqueadas en Chrome moderno). Pedir al usuario que haga login manualmente en la tab abierta y reintentar `navigate_page` con `timeout: 30000`.
- **Marker dibujado en (0,0):** un click programático `el.click()` no incluye coords. Usar siempre `mcp__chrome-devtools__click` (CDP `Input.dispatchMouseEvent`) — sí incluye `clientX/Y`.
- **Trim recorta demasiado o muy poco:** ajustar `--threshold`. Si la UI tiene loaders/pulsos permanentes, sube el floor del MAD; subí el threshold por encima del floor (medirlo con `--keep-frames` y un script ad-hoc si hace falta).
