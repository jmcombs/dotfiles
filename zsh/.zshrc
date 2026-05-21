# ====================
# PATH
# ====================
# ~/.local/bin — user-installed binaries (e.g. Claude Code CLI native installer)
export PATH="$HOME/.local/bin:$PATH"

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

# Ollama — manual lifecycle control (registered via launchd, never auto-starts)
alias ollama-start="launchctl kickstart -k gui/\$UID/com.ollama"
alias ollama-stop="launchctl kill SIGTERM gui/\$UID/com.ollama"
alias ollama-status="launchctl print gui/\$UID/com.ollama 2>/dev/null | grep -E 'state|pid'"

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
# Prompt: Oh My Posh with Blue PSL 10K theme
# ====================
eval "$(oh-my-posh init zsh --config ~/.config/oh-my-posh/themes/blue-psl-10k.omp.json)"

# ====================
# System info on startup (fastfetch)
# ====================
# Only run fastfetch in interactive shells (normal terminal sessions)
if [[ -o interactive ]]; then
	fastfetch
fi

# ====================
# Items automatically added by other tools
# ====================
# The following lines have been added by Docker Desktop to enable Docker CLI completions.
fpath=(/Users/jmcombs/.docker/completions $fpath)
autoload -Uz compinit
compinit
# End of Docker CLI completions
