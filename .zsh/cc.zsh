_cc_path_prefix() {
  print -r -- "$HOME/.bun/bin:$HOME/.local/kitty.app/bin:$HOME/.local/bin:$HOME/.opencode/bin:$HOME/.config/composer/vendor/bin:$HOME/.local/share/pnpm:$HOME/.console-ninja/.bin:$HOME/.asdf/shims:/home/linuxbrew/.linuxbrew/opt/asdf/libexec/bin:/home/linuxbrew/.linuxbrew/bin:/home/linuxbrew/.linuxbrew/sbin:$HOME/.cargo/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
}

cc() {
  # Preserve access to user-installed CLIs even when Claude starts from a thin PATH.
  local -x PATH="$(_cc_path_prefix):$PATH"
  command claude --dangerously-skip-permissions "$@"
}

ca() {
  local -x PATH="$(_cc_path_prefix):$PATH"
  command claude agents "$@"
}

ccf() {
  local -x PATH="$(_cc_path_prefix):$PATH"
  command claude --dangerously-skip-permissions --model sonnet "$@"
}

cci() {
  local model effort

  model=$(gum choose --header="Model" --selected=sonnet sonnet opus haiku) || return 1
  effort=$(gum choose --header="Effort" --selected=medium low medium high xhigh max) || return 1

  cc --model "$model" --effort "$effort" "$@"
}
