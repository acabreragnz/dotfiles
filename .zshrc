# If you come from bash you might have to change your $PATH.
# export PATH=$HOME/bin:/usr/local/bin:$PATH

# Path to your oh-my-zsh installation.
export ZSH="$HOME/.oh-my-zsh"

# Set name of the theme to load --- if set to "random", it will
# load a random theme each time oh-my-zsh is loaded, in which case,
# to know which specific one was loaded, run: echo $RANDOM_THEME
# See https://github.com/ohmyzsh/ohmyzsh/wiki/Themes
ZSH_THEME="agnoster"

# Set list of themes to pick from when loading at random
# Setting this variable when ZSH_THEME=random will cause zsh to load
# a theme from this variable instead of looking in $ZSH/themes/
# If set to an empty array, this variable will have no effect.
# ZSH_THEME_RANDOM_CANDIDATES=( "robbyrussell" "agnoster" )

# Uncomment the following line to use case-sensitive completion.
# CASE_SENSITIVE="true"

DEFAULT_USER=$(whoami)

# Uncomment the following line to use hyphen-insensitive completion.
# Case-sensitive completion must be off. _ and - will be interchangeable.
# HYPHEN_INSENSITIVE="true"

# Uncomment one of the following lines to change the auto-update behavior
# zstyle ':omz:update' mode disabled  # disable automatic updates
# zstyle ':omz:update' mode auto      # update automatically without asking
# zstyle ':omz:update' mode reminder  # just remind me to update when it's time

# Uncomment the following line to change how often to auto-update (in days).
# zstyle ':omz:update' frequency 13

# Uncomment the following line if pasting URLs and other text is messed up.
# DISABLE_MAGIC_FUNCTIONS="true"

# Uncomment the following line to disable colors in ls.
# DISABLE_LS_COLORS="true"

# Uncomment the following line to disable auto-setting terminal title.
# DISABLE_AUTO_TITLE="true"

# Uncomment the following line to enable command auto-correction.
# ENABLE_CORRECTION="true"

# Uncomment the following line to display red dots whilst waiting for completion.
# You can also set it to another string to have that shown instead of the default red dots.
# e.g. COMPLETION_WAITING_DOTS="%F{yellow}waiting...%f"
# Caution: this setting can cause issues with multiline prompts in zsh < 5.7.1 (see #5765)
# COMPLETION_WAITING_DOTS="true"

# Uncomment the following line if you want to disable marking untracked files
# under VCS as dirty. This makes repository status check for large repositories
# much, much faster.
# DISABLE_UNTRACKED_FILES_DIRTY="true"

# Uncomment the following line if you want to change the command execution time
# stamp shown in the history command output.
# You can set one of the optional three formats:
# "mm/dd/yyyy"|"dd.mm.yyyy"|"yyyy-mm-dd"
# or set a custom format using the strftime function format specifications,
# see 'man strftime' for details.
# HIST_STAMPS="mm/dd/yyyy"

# Would you like to use another custom folder than $ZSH/custom?
# ZSH_CUSTOM=/path/to/new-custom-folder

# Which plugins would you like to load?
# Standard plugins can be found in $ZSH/plugins/
# Custom plugins may be added to $ZSH_CUSTOM/plugins/
# Example format: plugins=(rails git textmate ruby lighthouse)
# Add wisely, as too many plugins slow down shell startup.
plugins=(git zsh-autosuggestions zsh-syntax-highlighting npm z zsh-npm-scripts-autocomplete)

source $ZSH/oh-my-zsh.sh

# User configuration

# export MANPATH="/usr/local/man:$MANPATH"

# You may need to manually set your language environment
# export LANG=en_US.UTF-8

# Preferred editor for local and remote sessions
# if [[ -n $SSH_CONNECTION ]]; then
#   export EDITOR='vim'
# else
#   export EDITOR='mvim'
# fi

# Compilation flags
# export ARCHFLAGS="-arch x86_64"

# Set personal aliases, overriding those provided by oh-my-zsh libs,
# plugins, and themes. Aliases can be placed here, though oh-my-zsh
# users are encouraged to define aliases within the ZSH_CUSTOM folder.
# For a full list of active aliases, run `alias`.
#
# Example aliases
# alias zshconfig="mate ~/.zshrc"
# alias ohmyzsh="mate ~/.oh-my-zsh"
bindkey '^H' backward-kill-word

### aliases
alias gcom="git checkout -m"

### Claude CLI aliases
alias cc="claude"
alias ccd="claude --dangerously-skip-permissions"
alias ccp="claude -p"
alias ccc="claude -c"
alias ccr="claude -r"
alias ccpt="claude -p --no-session-persistence --model haiku --settings '{\"alwaysThinkingEnabled\":false}'"

# alias npm=pnpm
alias pn=pnpm
alias pnx='pnpm dlx'

alias pnr="cat package.json | jq -r '.scripts | keys[]' | fzf | xargs -I {} npm run {}"
alias zshrc="code ~/.zshrc"

# Docker Compose aliases for Elixir development
alias dexec="docker compose exec"
alias drestart="docker compose restart"
alias dup="docker compose up -d"

alias dmix="docker compose exec app mix"
alias dtest="docker compose exec test mix test"
alias diex="docker compose exec -it app iex -S mix"
alias dpsql="docker compose exec -it postgres psql -U postgres"
alias dlogs="docker compose logs -f"

### functions
# Instalar archivos .deb o paquetes desde repositorios
# Ejemplos:
#   debi archivo.deb              -> instala archivo local en directorio actual
#   debi ~/Descargas/app.deb      -> instala archivo con ruta completa
#   debi /tmp/paquete.deb         -> instala archivo con ruta absoluta
#   debi nombre-paquete           -> instala paquete desde repositorios
debi() {
  if [ -f "$1" ]; then
    # Si el archivo existe, asegurarse de que tenga ./ al inicio si no tiene ruta
    if [[ "$1" != */* ]]; then
      sudo apt install "./$1"
    else
      sudo apt install "$1"
    fi
  else
    # Si no es un archivo, pasar como paquete normal
    sudo apt install "$@"
  fi
}

function gacp() {
  git add -A
  git commit -m "$1"
  git push
}

function git_alias() {
    if [ "$#" -ne 2 ]; then
        echo "Usage: git_alias <alias_name> <command>"
        return 1
    fi
    git config --global alias."$1" "$2"
    echo "Alias added: $1 -> $2"
}

dcpest() {
    docker compose run --rm php vendor/bin/pest "$@" 2>&1 | sed 's|/var/www/html/||g'
}

### misc

# Initialize Homebrew (must come before any brew commands)
eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv zsh)"

# =================================================================
# PROJECT RABBET - Version Manager Toggle
# =================================================================
# Set to true to use asdf (for Rabbet project)
# Set to false to use nvm (for other projects)
export USE_RABBET=true

if [ "$USE_RABBET" = "true" ]; then
  # ASDF configuration (for Rabbet project) - installed via brew
  . $(brew --prefix asdf)/libexec/asdf.sh

  # Auto-enable corepack when installing Node.js versions
  export ASDF_NODEJS_AUTO_ENABLE_COREPACK=1
else
  # NVM configuration (for other projects)
  export NVM_DIR="$HOME/.nvm"
  [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"  # This loads nvm
  [ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"  # This loads nvm bash_completion

  # Auto-load .nvmrc files
  autoload -U add-zsh-hook
  load-nvmrc() {
    local node_version="$(nvm version)"
    local nvmrc_path="$(nvm_find_nvmrc)"

    if [ -n "$nvmrc_path" ]; then
      local nvmrc_node_version=$(nvm version "$(cat "${nvmrc_path}")")

      if [ "$nvmrc_node_version" = "N/A" ]; then
        nvm install
      elif [ "$nvmrc_node_version" != "$node_version" ]; then
        nvm use
      fi
    elif [ "$node_version" != "$(nvm version default)" ]; then
      echo "Reverting to nvm default version"
      nvm use default
    fi
  }
  add-zsh-hook chpwd load-nvmrc
  load-nvmrc

  # NVM aliases
  alias oldnpm="$(nvm which current | sed 's/\/node$/\/npm/')"
fi

# Helper functions to switch between Rabbet and non-Rabbet modes
rabbet-on() {
  sed -i 's/export USE_RABBET=.*/export USE_RABBET=true/' ~/.zshrc
  echo "✓ Rabbet mode activated (using asdf)"
  echo "Please restart your terminal or run: source ~/.zshrc"
}

rabbet-off() {
  sed -i 's/export USE_RABBET=.*/export USE_RABBET=false/' ~/.zshrc
  echo "✓ Rabbet mode deactivated (using nvm)"
  echo "Please restart your terminal or run: source ~/.zshrc"
}

PATH=~/.console-ninja/.bin:$PATH


# pnpm
export PNPM_HOME="$HOME/.local/share/pnpm"
case ":$PATH:" in
  *":$PNPM_HOME:"*) ;;
  *) export PATH="$PNPM_HOME:$PATH" ;;
esac
# pnpm end
export PATH="$HOME/.local/bin:$PATH"
export PATH="$HOME/.config/composer/vendor/bin:$PATH"
export DOCKER_HOST=unix:///var/run/docker.sock
alias cursor="cursor --no-sandbox"

# Android Studio y React Native configuration
export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
export ANDROID_HOME=$HOME/Android/Sdk
export ANDROID_SDK_ROOT=$HOME/Android/Sdk
export ANDROID_STUDIO=/opt/android-studio
export PATH=$PATH:$ANDROID_HOME/emulator
export PATH=$PATH:$ANDROID_HOME/platform-tools
export PATH=$PATH:$ANDROID_HOME/build-tools
export DOTNET_ROOT=$HOME/.dotnet
export PATH=$PATH:$HOME/.dotnet:$HOME/.dotnet/tools

# opencode
export PATH=$HOME/.opencode/bin:$PATH
