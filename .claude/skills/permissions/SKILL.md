---
name: permissions
description: Use when the user wants to add, remove, or move entries between allow/ask/deny lists in Claude Code global permissions (~/.claude/settings.json). Triggers on /permissions command, "agrega permiso", "quita permiso", "mueve a allow/ask/deny", "mcp__x en allow", "ponelo ask", "ponelo allow", "permisos de claude code", "agrega a permissions".
---

# Permissions — Gestión de permisos globales de Claude Code

## Overview

Gestiona las listas `allow`, `ask` y `deny` en `~/.claude/settings.json` de forma segura. Siempre leer el archivo primero, editar con `Edit` (nunca `Write`), y confirmar el cambio al usuario.

## Flujo obligatorio

1. **Leer** `~/.claude/settings.json` con la herramienta `Read`
2. **Detectar intención** del usuario (ver tabla abajo)
3. **Validar formato** de la nueva entrada
4. **Aplicar** con `Edit` — nunca reemplazar el archivo entero
5. **Confirmar** mostrando qué cambió

## Detección de intención

| El usuario dice... | Acción |
|---|---|
| `/permissions` sin args | Mostrar resumen de las 3 listas y preguntar qué hacer |
| "agrega X" / "add X" | Agregar a la lista mencionada; si no la menciona, preguntar |
| "quita X" / "remove X" | Buscar en las 3 listas y eliminar donde esté |
| "mueve X de allow a ask" | Quitar de la lista origen, agregar en la destino |
| "ponelo ask" / "ponelo allow" | Mover la entrada mencionada en contexto a esa lista |

## Modo interactivo (`/permissions` sin args)

Mostrar un resumen así y preguntar con `AskUserQuestion`:

```
Permisos globales (~/.claude/settings.json):
  allow: N entradas  (ej: mcp__chrome-devtools__*, Bash(git status), ...)
  ask:   N entradas  (ej: Edit, Write, Bash(git commit:*), ...)
  deny:  N entradas  (ej: Bash(sudo:*), Read(**/.env*), ...)
```

Luego preguntar: ¿qué querés hacer? con opciones: Agregar, Quitar, Mover, Ver lista completa.

## Formatos válidos de entradas

```
# MCPs
"mcp__server__tool_name"         # tool específico
"mcp__server__*"                 # todos los tools del server

# Bash
"Bash(comando)"                  # comando exacto
"Bash(comando:*)"                # comando con cualquier argumento

# Archivos
"Read(**/*.ext)"                 # leer por patrón
"Write(path/**)"                 # escribir en path
"Edit(path/**)"                  # editar en path
```

## Reglas de seguridad

- **deny tiene prioridad sobre allow** — si una entrada está en `deny`, agregarla a `allow` no la desbloquea. Advertir al usuario.
- **No agregar wildcards peligrosos** como `"Bash(*)"` o `"Bash(rm:*)"` en allow.
- **`skipDangerousModePermissionPrompt: true` está activo** en este settings — todo lo que esté en `allow` se ejecuta sin confirmación. Ser conservador.
- Si el usuario pide mover algo de `deny` a `allow`, confirmar explícitamente antes de proceder.

## Cómo editar el archivo

Usar `Edit` con el contexto suficiente para ubicar la línea correcta. Ejemplo para agregar al final de `allow`:

```
old: "mcp__plugin_context7_context7__*"
new: "mcp__plugin_context7_context7__*",
     "mcp__nueva_entrada__*"
```

Para quitar una entrada del medio de una lista:
```
old: "entrada_a_quitar",\n      "siguiente_entrada"
new: "siguiente_entrada"
```

## Verificar resultado

Después de editar, confirmar al usuario qué cambió:
> ✓ Agregado `"mcp__figma__*"` a **allow** en `~/.claude/settings.json`

Si hay dudas sobre si el JSON quedó válido, leer el archivo nuevamente para verificar.

## Notas de versión relevantes

### Compound bash commands — fix 2.1.77
Antes de 2.1.77, cuando el usuario aceptaba "Always Allow" en un comando compuesto como `cd src && npm test`, CC guardaba una regla para el string completo → nunca volvía a matchear → regla muerta en allow.
Desde 2.1.77, guarda una regla **por subcomando**.
**Cómo detectar reglas muertas:** buscar en `allow` entradas `Bash(...)` que contengan `&&`, `||`, `;` o `|` — esas son candidatas a limpiar.

### Comandos en allowlist interna de CC — desde 2.1.72
Estos comandos fueron agregados al allowlist interno de Claude Code (no requieren entrada en settings.json):
`lsof`, `pgrep`, `ss`, `fd`, `fdfind`, `tput`
Se agregaron también al `allow` del usuario para consistencia y documentación explícita.
