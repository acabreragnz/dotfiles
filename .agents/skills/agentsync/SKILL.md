---
name: agentsync
description: Use when configurando, ejecutando o debugging agentsync — agregar/renombrar skills, sincronizar configs entre Claude/OpenCode/Codex, editar agentsync.toml, verificar symlinks, agregar MCP servers o agregar un tool nuevo al setup. También usar después de crear/renombrar/borrar un skill para correr `apply` automáticamente.
---

# AgentSync

CLI Rust que sincroniza configs de AI agents (instructions, skills, MCPs) via symlinks. Source of truth en `.agents/` + `AGENTS.md`. Repo: https://github.com/dallay/agentsync

## Filosofía

- `.agents/` y `AGENTS.md` son la **única fuente de verdad** — editar SIEMPRE ahí, nunca en `.claude/`, `.opencode/`, `.codex/` (esos son symlinks).
- `agentsync.toml` declara los symlinks → `agentsync apply` los materializa.
- Idempotente: `apply` se puede correr N veces sin romper nada.

## Setups conocidos

| Path | Tipo | Tools sincronizados |
|------|------|---------------------|
| `~/agentsync.toml` | Global — skills + instructions | Claude (`.claude/`), OpenCode (`.opencode/`), Codex (`.codex/`) — `symlink-contents` para skills |
| `~/agentsync-codex-mcp.toml` | Global — MCPs (solo Codex) | Mergea `[mcp_servers.*]` en `~/.codex/config.toml` |
| `~/personal/obsidian/second-brain/agentsync.toml` | Vault Obsidian | Claude, OpenCode, Codex — `symlink` directo del dir `.agents/skills` |

**Apply de cada uno:**
- Skills/instructions global: `agentsync apply` (desde `~`)
- MCPs Codex: `agentsync apply --config ~/agentsync-codex-mcp.toml --agents codex`
- Vault: `agentsync apply` (desde el vault root)

## Cuándo usar cada comando

### Edité un skill o `AGENTS.md`
**No hacer nada.** Los symlinks ya apuntan a `.agents/`. Cambio visible al instante en todos los tools.

### Creé/renombré/borré un skill, o edité `agentsync.toml`
```bash
agentsync apply
```
Idempotente. Reconstruye symlinks faltantes, deja los OK como están.

### Verificar estado
```bash
agentsync status   # lista cada symlink: OK / roto / faltante
agentsync doctor   # health check + valida sources, conflictos, MCP, skills no gestionados
```
Exit code 0 = OK, 1 = problemas.

### Antes de cualquier cambio dudoso
```bash
agentsync apply --dry-run --verbose
```
Muestra qué haría sin tocar nada. Recomendado antes de aplicar cambios al toml.

### Limpiar todo (rollback)
```bash
agentsync clean   # borra todos los symlinks gestionados
```

### Filtrar por tool
```bash
agentsync apply --agents claude          # solo Claude
agentsync apply --agents claude,codex    # ambos
```

## Reglas críticas (lo que NUNCA hacer)

- ❌ **`ln -s` manual** entre `.agents/` y `.claude/`/`.opencode/`/`.codex/` cuando el dir padre ya es symlink → genera self-loops (ELOOP) que **borran el contenido canónico**. Declarar siempre en `agentsync.toml` y correr `apply`.
- ❌ **`rm -rf` en `.claude/skills/<name>`** sin verificar primero `ls -la` del padre — si el padre es symlink, estás borrando el original en `.agents/`.
- ❌ **Editar archivos en `.claude/`, `.opencode/`, `.codex/`** — son symlinks; pierde el sentido y confunde. Editar SIEMPRE en `.agents/` o `AGENTS.md`.
- ❌ **Crear duplicados** — si necesitás el mismo archivo en dos lugares, una entrada en `agentsync.toml` lo arregla.
- ❌ **Tocar configs de plugins/web MCPs** (los `claude.ai/*` y `plugin:*` que aparecen en `claude mcp list`) — se gestionan desde el cliente Claude, no desde agentsync.

## Configuración del `agentsync.toml`

### Estructura mínima

```toml
source_dir = "."

[gitignore]
enabled = false  # vault Obsidian usa git directo; ~ usa yadm — desactivado en ambos

[agents.claude]
enabled = true

[agents.claude.targets.instructions]
source = "AGENTS.md"
destination = "CLAUDE.md"
type = "symlink"

[agents.claude.targets.skills]
source = ".agents/skills"
destination = ".claude/skills"
type = "symlink"            # un symlink al dir entero
# o:
# type = "symlink-contents" # un symlink por cada subdir (útil cuando .claude/skills debe quedar como dir real)
```

### Tipos de target

| Tipo | Cuándo |
|------|--------|
| `symlink` | Caso común — link directo a archivo o dir |
| `symlink-contents` | Cuando el destination debe ser un dir real con symlinks individuales adentro (ej: `~/.claude/skills/` global, donde Claude espera un dir y crea `.skill-lock.json` adentro) |
| `nested-glob` | Monorepos con `**/AGENTS.md` en submódulos |
| `module-map` | Mapeo central → varios módulos |

### Agregar un tool nuevo

Ejemplo: sumar Cursor.

```toml
[agents.cursor]
enabled = true
description = "Cursor"

[agents.cursor.targets.instructions]
source = "AGENTS.md"
destination = ".cursor/rules/agentsync.mdc"
type = "symlink"

[agents.cursor.targets.skills]
source = ".agents/skills"
destination = ".cursor/skills"
type = "symlink"
```

Después: `agentsync apply` → crea el symlink.

## MCP servers (centralizados)

Permite declarar MCPs UNA vez y que agentsync genere `.mcp.json` (Claude project), `.codex/config.toml`, `.opencode/opencode.json`, etc.

```toml
[mcp]
enabled = true
merge_strategy = "merge"   # "merge" preserva servers existentes; "overwrite" pisa todo

[mcp_servers.exa]
type = "http"
url = "https://mcp.exa.ai/mcp"

[mcp_servers.chrome-devtools]
command = "npx"
args = ["-y", "chrome-devtools-mcp@latest", "--autoConnect"]
```

> **Limitación con Claude:** agentsync genera `.mcp.json` (project-level). El user-level (`~/.claude.json` gestionado por `claude mcp add`) NO se toca. Para sincronizar MCPs **globales** entre tools, agentsync sirve para OpenCode + Codex, pero los MCPs globales de Claude se mantienen vía `claude mcp add` o desde el cliente web.

> **Patrón "MCP en config separado":** `[mcp]` se aplica a TODOS los agents enabled (no se puede decir "skills sí, MCP no" por agente). Para evitar contaminar Claude/OpenCode con `~/.mcp.json`/`~/opencode.json` no deseados, crear un toml separado (ej: `~/agentsync-codex-mcp.toml`) con SOLO el agent que sí debe recibir MCPs habilitado, y aplicarlo con `agentsync apply --config <path> --agents <agent>`. El toml principal queda solo para skills+instructions.

> **Plugins web/curados (Anthropic, OpenAI):** los plugins `claude.ai/*` y `plugin:*` (Claude) y `plugins.<name>@openai-curated` (Codex) NO son MCPs file-based. Se gestionan vía OAuth/cuenta del cliente, no via agentsync. NO incluirlos en `[mcp_servers.*]`.

## Flujos comunes

### Crear un skill nuevo
1. `mkdir ~/.agents/skills/<nombre>` (o `<vault>/.agents/skills/<nombre>` para skills de proyecto).
2. `Write` el `SKILL.md` ahí.
3. `agentsync apply` desde el root correspondiente — crea symlinks en `.claude/skills/`, `.opencode/skills/`, `.codex/skills/`.
4. `agentsync status` para confirmar.

### Renombrar un skill
1. `mv ~/.agents/skills/old-name ~/.agents/skills/new-name`
2. `agentsync apply --clean` desde `~` — borra symlinks viejos, crea los nuevos.
3. Verificar que ningún SKILL.md o AGENTS.md referencia el nombre viejo.

### Recuperarse de un symlink roto / loop
1. `agentsync doctor` — identifica el problema.
2. Si es self-loop (ELOOP):
   - `rm` el symlink roto (NO el original — verificar con `ls -la <padre>` que el padre NO sea symlink).
   - Restaurar contenido si se borró: `git show HEAD:<path> > <path>`.
   - Reaplicar: `agentsync apply`.

### Migrar un proyecto existente con archivos sueltos
```bash
agentsync init --wizard
```
Escanea archivos de agents existentes (CLAUDE.md, .cursor/, .github/copilot-instructions.md, skills sueltos, MCP configs), permite seleccionar qué migrar a `.agents/`, hace backup opcional, y genera el toml. **Útil solo si no hay divergencia entre archivos** — si hay versiones distintas del mismo archivo, mergear manualmente primero.

## Troubleshooting
