# Ensure system binaries are always in PATH — even in non-interactive shells
# (e.g. Claude Code's ! runner, which inherits only plugin dirs).
path=(/usr/local/bin /usr/bin /bin /usr/local/sbin /usr/sbin /sbin "$HOME/.local/bin" "$HOME/bin" $path)
typeset -U path  # deduplicate

. "$HOME/.cargo/env"
