oc() {
  # Preserve access to user-installed CLIs even when the shell starts with a thin PATH.
  local PATH="$HOME/.bun/bin:$HOME/.local/kitty.app/bin:$HOME/.local/bin:$HOME/.opencode/bin:$HOME/.config/composer/vendor/bin:$HOME/.local/share/pnpm:$HOME/.console-ninja/.bin:$HOME/.asdf/shims:/home/linuxbrew/.linuxbrew/opt/asdf/libexec/bin:/home/linuxbrew/.linuxbrew/bin:/home/linuxbrew/.linuxbrew/sbin:$HOME/.cargo/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:$PATH"
  command opencode "$@"
}

ocy() {
  # Match the proposed YOLO mode once the installed opencode version supports it.
  local PATH="$HOME/.bun/bin:$HOME/.local/kitty.app/bin:$HOME/.local/bin:$HOME/.opencode/bin:$HOME/.config/composer/vendor/bin:$HOME/.local/share/pnpm:$HOME/.console-ninja/.bin:$HOME/.asdf/shims:/home/linuxbrew/.linuxbrew/opt/asdf/libexec/bin:/home/linuxbrew/.linuxbrew/bin:/home/linuxbrew/.linuxbrew/sbin:$HOME/.cargo/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:$PATH"
  local help_text version

  help_text=$(command opencode --help 2>/dev/null)
  if [[ "$help_text" == *"--dangerously-skip-permissions"* ]]; then
    command opencode --dangerously-skip-permissions "$@"
    return
  fi

  version=$(command opencode --version 2>/dev/null)
  print -u2 "ocy: opencode ${version:-unknown} todavia no soporta --dangerously-skip-permissions; usando OPENCODE_DANGEROUSLY_SKIP_PERMISSIONS=true por compatibilidad futura."
  OPENCODE_DANGEROUSLY_SKIP_PERMISSIONS=true command opencode "$@"
}
