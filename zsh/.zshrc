# ====================
# Oh My Zsh configuration
# ====================
export ZSH="$HOME/.oh-my-zsh"

# Update behavior - automatic background updates
zstyle ':omz:update' mode auto

# Completion feedback - subtle yellow dots while waiting for slow completions
COMPLETION_WAITING_DOTS="%F{yellow}waiting...%f"

# Plugins (moved up for quicker scanning)
plugins=(
  git
  zsh-autosuggestions
  zsh-syntax-highlighting
)

# Source Oh My Zsh
source $ZSH/oh-my-zsh.sh

# ====================
# Aliases (modern replacements)
# ====================
alias ls='eza'
alias cat='bat'
alias more='bat'

# ====================
# Third-party completions & integrations
# ====================

# Docker Desktop CLI completions
fpath=($HOME/.docker/completions $fpath)
autoload -Uz compinit
compinit

# 1Password CLI (op) completions
if [ -f "$HOME/.config/op/plugins.sh" ]; then
  source $HOME/.config/op/plugins.sh
fi

# ====================
# Prompt: Oh My Posh with jmcombs p10k Latte theme
# ====================
# Set theme path to Homebrew's theme directory
export POSH_THEMES_PATH="/opt/homebrew/opt/oh-my-posh/themes"

# Load custom theme by full path
eval "$(oh-my-posh init zsh --config $POSH_THEMES_PATH/jmcombs_p10k_latte.omp.json)"

# ====================
# System info on startup (neofetch)
# ====================
# Only run neofetch in interactive shells (normal terminal sessions)
if [[ -o interactive ]]; then
    neofetch
fi

# ====================
# Items automatically added by other tools
# ====================
