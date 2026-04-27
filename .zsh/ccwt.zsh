# ccwt — interactive Claude worktree manager (single entrypoint)
# Auto-detects project from pwd (falls back to default). Requires: gum, git, gh (for PR flow).
#
# Usage:
#   ccwt                → 4-option menu (go, delete, delete-all, list)
#   ccwt <arg>          → skip menu; <arg> resolves to:
#                            pure digits  → PR number
#                            https://…/pull/N → PR URL
#                            existing worktree name → open it
#                            existing branch (local or origin) → open/create worktree
#                            anything else → offer to create scratch from default branch

_CCWT_PROJECT_DEFAULT="$HOME/dev/rabbet/lift"
_CCWT_PROJECT=""  # resolved on each ccwt() invocation

# ── Helpers ────────────────────────────────────────────────────

_ccwt_require_gum() {
  if ! command -v gum >/dev/null 2>&1; then
    echo "  ✗ 'gum' no está instalado."
    echo "    Ver /tmp/install-gum.sh o https://github.com/charmbracelet/gum#installation"
    return 1
  fi
}

# Detects main project path by walking up from pwd to the nearest git common dir.
# If not in a repo, falls back to _CCWT_PROJECT_DEFAULT.
_ccwt_detect_project() {
  local gitdir
  gitdir=$(command git rev-parse --git-common-dir 2>/dev/null)
  if [[ -n "$gitdir" ]]; then
    [[ "$gitdir" != /* ]] && gitdir="$(pwd)/$gitdir"
    local candidate
    candidate=$(cd "$gitdir/.." 2>/dev/null && pwd)
    [[ -n "$candidate" ]] && { echo "$candidate"; return 0; }
  fi
  echo "$_CCWT_PROJECT_DEFAULT"
}

# Returns the default branch name (e.g. master, main) detected from origin/HEAD.
_ccwt_default_branch() {
  local head
  head=$(command git -C "$_CCWT_PROJECT" symbolic-ref refs/remotes/origin/HEAD 2>/dev/null)
  if [[ -n "$head" ]]; then
    echo "${head#refs/remotes/origin/}"
  else
    echo "master"
  fi
}

# Populates global _ccwt_branch_to_wt map (branch → worktree path).
_ccwt_build_branch_map() {
  typeset -gA _ccwt_branch_to_wt
  _ccwt_branch_to_wt=()
  local _wt_path="" _wt_branch=""
  while IFS= read -r line; do
    if [[ "$line" == worktree\ * ]]; then
      _wt_path="${line#worktree }"
    elif [[ "$line" == branch\ * ]]; then
      _wt_branch="${line#branch refs/heads/}"
      _ccwt_branch_to_wt[$_wt_branch]="$_wt_path"
    fi
  done < <(command git -C "$_CCWT_PROJECT" worktree list --porcelain 2>/dev/null)
}

# Formats a worktree directory as a rich label: "name  [branch]  date"
_ccwt_format_worktree_label() {
  local dir="$1"
  local name="${dir:t}"
  local branch modified
  branch=$(command git -C "$dir" branch --show-current 2>/dev/null)
  modified=$(command stat -c '%y' "$dir" 2>/dev/null | command cut -d' ' -f1)
  if [[ -n "$branch" && "$branch" != "$name" && "$branch" != "worktree-$name" ]]; then
    printf "%-40s  [%s]  %s" "$name" "$branch" "$modified"
  else
    printf "%-40s  %s" "$name" "$modified"
  fi
}

# Shared: given a branch name, ensure it exists locally (auto-fetch from origin) and
# either resume its existing worktree or create a new one.
_ccwt_open_branch() {
  local branch="$1"
  [[ -z "$branch" ]] && { echo "  ✗ rama vacía"; return 1; }

  if ! command git -C "$_CCWT_PROJECT" rev-parse --verify --quiet "refs/heads/$branch" >/dev/null 2>&1; then
    echo "  → rama no existe local, buscando en origin…"
    if command git -C "$_CCWT_PROJECT" ls-remote --exit-code --heads origin "$branch" >/dev/null 2>&1; then
      echo "  → fetching origin/$branch…"
      if ! command git -C "$_CCWT_PROJECT" fetch origin "$branch:$branch" 2>&1; then
        echo "  ✗ fetch falló"
        return 1
      fi
    else
      echo "  ✗ rama '$branch' no existe ni local ni en origin"
      return 1
    fi
  fi

  _ccwt_build_branch_map
  if [[ -n "${_ccwt_branch_to_wt[$branch]}" ]]; then
    local existing="${_ccwt_branch_to_wt[$branch]}"
    echo ""
    echo "  → worktree ya existe, abriendo ${existing:t} (sesión nueva)"
    cd "$existing" && cc
    return
  fi

  local wt_name="${branch#*/}"
  wt_name="${wt_name:0:64}"
  wt_name="${wt_name%-}"

  echo ""
  echo "  → creando worktree desde rama: $branch"
  [[ "$wt_name" != "$branch" ]] && echo "  → nombre worktree: $wt_name"
  cd "$_CCWT_PROJECT" && cc --worktree "$wt_name"
}

# ── Main ────────────────────────────────────────────────────────

function ccwt() {
  _ccwt_require_gum || return 1
  _CCWT_PROJECT=$(_ccwt_detect_project)

  if [[ "$_CCWT_PROJECT" != "$_CCWT_PROJECT_DEFAULT" ]]; then
    echo "  📁 Proyecto: ${_CCWT_PROJECT:t}  ($_CCWT_PROJECT)"
    echo ""
  fi

  # Shortcut: ccwt <arg> skips the menu.
  if [[ $# -gt 0 ]]; then
    _ccwt_dispatch_arg "$1"
    return
  fi

  local action
  action=$(gum choose --header="¿Qué querés hacer?" \
    "🚀  Ir a un worktree (crear o abrir)" \
    "🗑  Borrar worktree(s)" \
    "💣  Borrar TODOS los worktrees" \
    "📋  Listar worktrees") || { echo "  Cancelado."; return 1; }

  case "$action" in
    *"Ir a un worktree"*)          _ccwt_go ;;
    *"Borrar TODOS"*)              _ccwt_delete_all ;;
    *"Borrar worktree"*)           _ccwt_delete_some ;;
    *"Listar"*)                    _ccwt_list ;;
  esac
}

# ── Arg dispatcher (ccwt <arg>) ─────────────────────────────────

_ccwt_dispatch_arg() {
  local arg="$1"
  arg="${arg#"${arg%%[![:space:]]*}"}"
  arg="${arg%"${arg##*[![:space:]]}"}"
  [[ -z "$arg" ]] && { echo "  ✗ arg vacío"; return 1; }

  # 1. PR number or GitHub PR URL
  if [[ "$arg" =~ ^[0-9]+$ || "$arg" == https://github.com/*/pull/* ]]; then
    _ccwt_resolve_pr "$arg"
    return
  fi

  _ccwt_build_branch_map

  # 2. Existing worktree by directory name
  local worktrees_dir="$_CCWT_PROJECT/.claude/worktrees"
  if [[ -d "$worktrees_dir/$arg" ]]; then
    echo "  → abriendo worktree existente: $arg"
    cd "$worktrees_dir/$arg" && cc
    return
  fi

  # 3. Existing branch (local or origin)
  if command git -C "$_CCWT_PROJECT" rev-parse --verify --quiet "refs/heads/$arg" >/dev/null 2>&1 \
     || command git -C "$_CCWT_PROJECT" ls-remote --exit-code --heads origin "$arg" >/dev/null 2>&1; then
    _ccwt_open_branch "$arg"
    return
  fi

  # 4. Fallback: offer to create new scratch from default branch
  local default_branch
  default_branch=$(_ccwt_default_branch)
  echo "  ℹ '$arg' no existe como worktree, rama (local u origin), ni PR."
  if gum confirm "¿Crear worktree nuevo '$arg' desde origin/$default_branch?"; then
    _ccwt_create_new "$arg"
  else
    echo "  Cancelado."
  fi
}

# ── Unified go: pick worktree, branch, or create new ─────────────

function _ccwt_go() {
  _ccwt_build_branch_map

  local default_branch
  default_branch=$(_ccwt_default_branch)

  local worktrees_dir="$_CCWT_PROJECT/.claude/worktrees"
  local -a dirs
  dirs=("$worktrees_dir"/*(N/om))  # mtime desc

  local -A merged_set
  while IFS= read -r b; do
    merged_set[${b## }]=1
  done < <(command git -C "$_CCWT_PROJECT" branch --merged "origin/$default_branch" --format='%(refname:short)' 2>/dev/null)

  local -a all_branches
  all_branches=($(command git -C "$_CCWT_PROJECT" branch --sort=-committerdate --format='%(refname:short)' 2>/dev/null))

  local NEW_LABEL="🆕   Rama nueva desde origin/$default_branch…"
  local PR_LABEL="📎   Desde PR…"
  local MANUAL_LABEL="✏️    Abrir rama por nombre (remote-only)…"

  local -a labels
  local -A label_to_action
  labels=("$NEW_LABEL" "$PR_LABEL" "$MANUAL_LABEL")
  label_to_action[$NEW_LABEL]="new:"
  label_to_action[$PR_LABEL]="pr:"
  label_to_action[$MANUAL_LABEL]="manual:"

  for dir in "${dirs[@]}"; do
    local lbl="📂   $(_ccwt_format_worktree_label "$dir")"
    labels+=("$lbl")
    label_to_action[$lbl]="wt:$dir"
  done

  for b in "${all_branches[@]}"; do
    [[ "$b" == "$default_branch" ]] && continue
    [[ -n "${merged_set[$b]}" ]] && continue
    [[ -n "${_ccwt_branch_to_wt[$b]}" ]] && continue  # already shown as worktree
    local lbl="🌿   $b"
    labels+=("$lbl")
    label_to_action[$lbl]="br:$b"
  done

  local selected
  selected=$(printf "%s\n" "${labels[@]}" | gum filter --no-strict --header="Ir a un worktree — filtrá, elegí o tipeá libre" --height=20) || { echo "  Cancelado."; return 1; }

  local action="${label_to_action[$selected]}"
  local type="${action%%:*}"
  local value="${action#*:}"

  case "$type" in
    wt)     echo "  → ${value:t} (sesión nueva)"; cd "$value" && cc ;;
    br)     _ccwt_open_branch "$value" ;;
    new)    _ccwt_create_new ;;
    pr)     _ccwt_resolve_pr ;;
    manual) _ccwt_open_manual ;;
    *)
      # Selection is free-form text (--no-strict) that didn't match any label.
      # Route it through the same smart resolver as `ccwt <arg>`.
      _ccwt_dispatch_arg "$selected"
      ;;
  esac
}

# ── Flows ───────────────────────────────────────────────────────

# Create a new scratch worktree from origin/<default>. Optional positional arg
# pre-fills the name (used by the ccwt <arg> shortcut).
function _ccwt_create_new() {
  local default_branch
  default_branch=$(_ccwt_default_branch)

  local name="$1"
  if [[ -z "$name" ]]; then
    name=$(gum input --header="Nombre del worktree (desde $default_branch)" --placeholder="feature-xyz") || { echo "  Cancelado."; return 1; }
    name="${name#"${name%%[![:space:]]*}"}"
    name="${name%"${name##*[![:space:]]}"}"
    [[ -z "$name" ]] && { echo "  Sin nombre, cancelado."; return 1; }
  fi

  # Collision check: if the typed name matches an existing branch (local or origin),
  # offer to open that branch instead of creating a scratch worktree-<name>.
  if command git -C "$_CCWT_PROJECT" rev-parse --verify --quiet "refs/heads/$name" >/dev/null 2>&1 \
     || command git -C "$_CCWT_PROJECT" ls-remote --exit-code --heads origin "$name" >/dev/null 2>&1; then
    echo ""
    echo "  ⚠ '$name' ya existe como rama (local o en origin)."
    if gum confirm "¿Abrir esa rama en vez de crear scratch?"; then
      _ccwt_open_branch "$name"
      return
    fi
    echo "  → seguimos con scratch: worktree-$name"
  fi

  local wt_name="${name#*/}"
  wt_name="${wt_name:0:64}"
  wt_name="${wt_name%-}"

  local worktrees_dir="$_CCWT_PROJECT/.claude/worktrees"
  local collision_path="$worktrees_dir/$wt_name"
  if [[ -d "$collision_path" ]]; then
    local is_registered
    is_registered=$(command git -C "$_CCWT_PROJECT" worktree list --porcelain 2>/dev/null | \
      command awk -v p="$collision_path" '$1=="worktree" && $2==p {c++} END{print c+0}')

    if (( is_registered > 0 )); then
      echo ""
      echo "  ⚠ ya existe un worktree llamado: $wt_name"
      if gum confirm "¿Abrir el existente en sesión nueva?"; then
        cd "$collision_path" && cc
      else
        echo "  Cancelado."
      fi
      return
    else
      echo ""
      echo "  ⚠ hay un directorio huérfano en $wt_name (no registrado como worktree)"
      if gum confirm "¿Limpiar y crear uno nuevo?"; then
        _ccwt_delete_worktree "$_CCWT_PROJECT" "$collision_path"
        echo ""
      else
        echo "  Cancelado."
        return
      fi
    fi
  fi

  if command git -C "$_CCWT_PROJECT" rev-parse --verify --quiet "refs/heads/worktree-$wt_name" >/dev/null 2>&1; then
    echo ""
    echo "  ⚠ ya existe una rama: worktree-$wt_name"
    if ! gum confirm "¿Continuar igual?"; then
      echo "  Cancelado."
      return
    fi
  fi

  echo ""
  echo "  → nuevo worktree desde origin/$default_branch: $wt_name"
  cd "$_CCWT_PROJECT" && cc --worktree "$wt_name"
}

# Resolve a PR number/URL to its branch and open/create the worktree. Prompts if no arg.
function _ccwt_resolve_pr() {
  if ! command -v gh >/dev/null 2>&1; then
    echo "  ✗ 'gh' no está instalado."
    return 1
  fi

  local input="$1"
  if [[ -z "$input" ]]; then
    input=$(gum input --header="Número de PR o URL" --placeholder="6800") || { echo "  Cancelado."; return 1; }
    input="${input#"${input%%[![:space:]]*}"}"
    input="${input%"${input##*[![:space:]]}"}"
    [[ -z "$input" ]] && { echo "  Sin PR, cancelado."; return 1; }
  fi

  echo "  → buscando rama del PR $input…"
  local branch
  branch=$(command gh pr view "$input" --json headRefName -q .headRefName 2>/dev/null)
  if [[ -z "$branch" ]]; then
    echo "  ✗ no se pudo obtener la rama del PR '$input'"
    return 1
  fi
  echo "  → rama: $branch"

  _ccwt_open_branch "$branch"
}

# Free-text branch-name input (for remote-only branches not shown in the picker).
function _ccwt_open_manual() {
  local branch
  branch=$(gum input --header="Nombre de la rama" --placeholder="feature/..." --width=80) || { echo "  Cancelado."; return 1; }
  branch="${branch#"${branch%%[![:space:]]*}"}"
  branch="${branch%"${branch##*[![:space:]]}"}"
  [[ -z "$branch" ]] && { echo "  Sin nombre, cancelado."; return 1; }
  _ccwt_open_branch "$branch"
}

function _ccwt_delete_some() {
  local worktrees_dir="$_CCWT_PROJECT/.claude/worktrees"
  local dirs=("$worktrees_dir"/*(N/))
  if [[ ${#dirs[@]} -eq 0 ]]; then
    echo "  No hay worktrees."
    return 0
  fi

  local labels=()
  local -A label_to_dir
  for dir in "${dirs[@]}"; do
    local lbl
    lbl=$(_ccwt_format_worktree_label "$dir")
    labels+=("$lbl")
    label_to_dir[$lbl]="$dir"
  done

  local selected
  selected=$(printf "%s\n" "${labels[@]}" | gum filter --no-limit --header="Tab selecciona, Enter confirma — worktree(s) a borrar" --height=20) || { echo "  Cancelado."; return 1; }
  [[ -z "$selected" ]] && { echo "  Nada seleccionado."; return 0; }

  local -a paths_to_delete=()
  while IFS= read -r lbl; do
    [[ -n "${label_to_dir[$lbl]}" ]] && paths_to_delete+=("${label_to_dir[$lbl]}")
  done <<< "$selected"

  echo ""
  echo "  Se van a borrar:"
  for p in "${paths_to_delete[@]}"; do echo "    - ${p:t}"; done

  local current_pwd will_lose_pwd=0
  current_pwd=$(pwd)
  for p in "${paths_to_delete[@]}"; do
    [[ "$current_pwd" == "$p"* ]] && { will_lose_pwd=1; break; }
  done
  if (( will_lose_pwd )); then
    echo ""
    echo "  ⚠ estás dentro de un worktree a borrar — vas a terminar en $_CCWT_PROJECT"
  fi

  echo ""
  gum confirm "¿Confirmás?" || { echo "  Cancelado."; return 0; }

  for p in "${paths_to_delete[@]}"; do
    _ccwt_delete_worktree "$_CCWT_PROJECT" "$p"
  done

  (( will_lose_pwd )) && cd "$_CCWT_PROJECT"
}

function _ccwt_delete_all() {
  local worktrees_dir="$_CCWT_PROJECT/.claude/worktrees"
  local dirs=("$worktrees_dir"/*(N/))
  if [[ ${#dirs[@]} -eq 0 ]]; then
    echo "  No hay worktrees."
    return 0
  fi

  echo ""
  echo "  Se van a borrar TODOS los worktrees (${#dirs[@]}):"
  for dir in "${dirs[@]}"; do echo "    - ${dir:t}"; done

  local current_pwd will_lose_pwd=0
  current_pwd=$(pwd)
  for dir in "${dirs[@]}"; do
    [[ "$current_pwd" == "$dir"* ]] && { will_lose_pwd=1; break; }
  done
  if (( will_lose_pwd )); then
    echo ""
    echo "  ⚠ estás dentro de un worktree a borrar — vas a terminar en $_CCWT_PROJECT"
  fi

  echo ""
  gum confirm "¿Confirmás?" || { echo "  Cancelado."; return 0; }

  for dir in "${dirs[@]}"; do
    _ccwt_delete_worktree "$_CCWT_PROJECT" "$dir"
  done

  (( will_lose_pwd )) && cd "$_CCWT_PROJECT"
}

function _ccwt_list() {
  local worktrees_dir="$_CCWT_PROJECT/.claude/worktrees"
  local dirs=("$worktrees_dir"/*(N/))
  if [[ ${#dirs[@]} -eq 0 ]]; then
    echo "  No hay worktrees."
    return 0
  fi

  echo ""
  echo "  Claude worktrees — ${_CCWT_PROJECT:t}"
  echo "  ─────────────────────────────────────────"
  for dir in "${dirs[@]}"; do
    echo "    $(_ccwt_format_worktree_label "$dir")"
  done
}

# ── Internal: delete one worktree, its branch, and its Claude project dir ──
function _ccwt_delete_worktree() {
  # Defensive: ensure system bins are reachable. PATH from a parent `cc`
  # session can drop /usr/bin or /bin, breaking `command awk` / `command rm`.
  local PATH="/usr/bin:/bin:$PATH"

  local project="$1"
  local path="$2"
  local name="${path:t}"

  echo "  Borrando $name..."

  local is_registered
  is_registered=$(command git -C "$project" worktree list --porcelain 2>/dev/null | \
    command awk -v p="$path" '$1=="worktree" && $2==p {c++} END{print c+0}')

  if (( is_registered > 0 )); then
    local branch
    branch=$(command git -C "$path" symbolic-ref --short HEAD 2>/dev/null)
    command git -C "$project" worktree remove --force "$path" 2>/dev/null
    command git -C "$project" worktree prune 2>/dev/null
    if [[ -n "$branch" && "$branch" == worktree-* ]]; then
      command git -C "$project" branch -D "$branch" 2>/dev/null && echo "    rama $branch borrada"
    elif [[ -n "$branch" ]]; then
      echo "    rama $branch preservada (no auto-borrada)"
    fi
  else
    echo "    (huérfano — borrando solo el directorio)"
    command rm -rf "$path"
  fi

  local encoded="${path//\//-}"
  encoded="${encoded//./-}"
  local claude_project="$HOME/.claude/projects/$encoded"
  if [[ -d "$claude_project" ]]; then
    command rm -rf "$claude_project" && echo "    claude project dir limpiado"
  fi

  echo "    listo"
}
