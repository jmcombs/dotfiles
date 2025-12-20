#!/bin/bash

set -e  # Exit immediately if any command fails

# ====================
# Configuration Variables
# ====================
# Dotfiles directory (hidden folder)
DOTFILES_DIR="$HOME/.dotfiles"

# Dotfiles repository URL
REPO_URL="https://github.com/jmcombs/dotfiles.git"

# Backup directory for existing configuration files (timestamped)
BACKUP_DIR="$HOME/.dotfiles-backup-$(date +%Y%m%d-%H%M%S)"

# Homebrew location for oh-my-posh themes (Apple Silicon Macs)
POSH_THEMES_DIR="/opt/homebrew/opt/oh-my-posh/themes"

# Ghostty configuration directory (XDG-compliant location)
GHOSTTY_CONFIG_DIR="$HOME/.config/ghostty"

echo "=== jmcombs/dotfiles Installer ==="
echo "Dotfiles location: $DOTFILES_DIR"
echo "Backup directory:  $BACKUP_DIR"
echo ""

# ====================
# Ensure Xcode Command Line Tools are installed
# ====================
# Skip this check if we're re-executing after cloning (set by self-bootstrap below)
if [ "$DOTFILES_INSTALLING" != "true" ]; then
  echo "Checking for Xcode Command Line Tools..."
  if ! xcode-select -p &> /dev/null; then
    echo "Xcode Command Line Tools not found. Installing..."
    xcode-select --install
    echo "Please complete the installation dialog and run this script again."
    exit 1
  else
    echo "Xcode Command Line Tools are installed."
  fi

  echo ""
fi

# ====================
# Self-bootstrap: Clone repository if not running from local copy
# ====================
# This allows the script to be run directly via curl | bash
if [ "$(basename "$(pwd)" 2>/dev/null || echo "")" != ".dotfiles" ] || [ ! -d "$DOTFILES_DIR/.git" ]; then
  echo "Cloning dotfiles repository to $DOTFILES_DIR..."
  rm -rf "$DOTFILES_DIR"  # Remove any partial/incomplete previous clone
  git clone "$REPO_URL" "$DOTFILES_DIR"
  cd "$DOTFILES_DIR"
  chmod +x install.sh
  echo "Repository cloned. Re-running installer from local copy..."
  exec env DOTFILES_INSTALLING=true ./install.sh  # Replace current process with local version
fi

echo "Running from local repository: $DOTFILES_DIR"
echo ""

# Create backup directory for any existing configuration files
mkdir -p "$BACKUP_DIR"

# ====================
# Helper function: Create symlink with backup of existing files
# ====================
link_file() {
  local src="$1"
  local dst="$2"

  if [ -e "$dst" ] && [ ! -L "$dst" ]; then
    echo "Backing up existing $dst → $BACKUP_DIR/"
    mv "$dst" "$BACKUP_DIR/"
  elif [ -L "$dst" ]; then
    echo "Removing old symlink $dst"
    rm "$dst"
  fi

  echo "Symlinking $src → $dst"
  ln -sf "$src" "$dst"
}

# ====================
# Helper function: Install Oh My Zsh plugins
# ====================
install_omz_plugin() {
  local plugin_name="$1"
  local plugin_repo="$2"
  local ZSH_CUSTOM="${ZSH_CUSTOM:-$HOME/.oh-my-zsh/custom}"
  
  # Skip if it's a built-in plugin
  if [ -d "$HOME/.oh-my-zsh/plugins/$plugin_name" ]; then
    return 0
  fi
  
  # Install custom plugin if not already present
  if [ ! -d "$ZSH_CUSTOM/plugins/$plugin_name" ]; then
    echo "Installing $plugin_name..."
    git clone "$plugin_repo" "$ZSH_CUSTOM/plugins/$plugin_name"
  else
    echo "$plugin_name already installed"
  fi
}

# ====================
# Install Oh My Zsh
# ====================
echo "Installing Oh My Zsh..."
if [ ! -d "$HOME/.oh-my-zsh" ]; then
  sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)" "" --unattended
else
  echo "Oh My Zsh already installed."
fi

# Install Oh My Zsh plugins from .zshrc
echo "Installing Oh My Zsh plugins..."
if [ -f "$DOTFILES_DIR/zsh/.zshrc" ]; then
  # Extract plugin names from the plugins=(...) array in .zshrc
  plugins=$(grep -A 10 '^plugins=(' "$DOTFILES_DIR/zsh/.zshrc" | sed -n '/^plugins=(/,/^)/p' | grep -v '^plugins=\|^)' | tr -d ' ')
  
  for plugin in $plugins; do
    case "$plugin" in
      zsh-autosuggestions)
        install_omz_plugin "zsh-autosuggestions" "https://github.com/zsh-users/zsh-autosuggestions"
        ;;
      zsh-syntax-highlighting)
        install_omz_plugin "zsh-syntax-highlighting" "https://github.com/zsh-users/zsh-syntax-highlighting"
        ;;
      # Add more custom plugins here as needed
      *)
        # Skip built-in plugins (git, etc.)
        ;;
    esac
  done
fi

# ====================
# Homebrew: Install if not present
# ====================
echo "Checking Homebrew installation..."
if [ -x "/opt/homebrew/bin/brew" ]; then
  echo "Homebrew already installed."
else
  echo "Installing Homebrew..."
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

  # Ensure Homebrew is added to shell environment for future sessions
  if ! grep -q 'eval "$(/opt/homebrew/bin/brew shellenv)"' ~/.zprofile; then
    echo >> ~/.zprofile
    echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
  fi
fi

# Activate Homebrew for the current script session
eval "$(/opt/homebrew/bin/brew shellenv)"

# ====================
# Install applications and tools via Homebrew Bundle
# ====================
echo "Updating Homebrew..."
brew update

echo "Installing applications from Brewfile..."
cd "$DOTFILES_DIR"
brew bundle

# ====================
# Configure Git User Settings
# ====================
echo "Configuring Git user settings..."
echo ""

# Prompt for git user.name
current_name=$(git config --global user.name || true)
if [ -n "$current_name" ]; then
  echo "Git user.name is set to: $current_name"
  read -p "Change it? (y/N): " change_name
  if [[ "$change_name" =~ ^[Yy]$ ]]; then
    read -p "Enter new Git user.name: " git_name
    if [ -n "$git_name" ]; then
      git config --global user.name "$git_name"
      echo "Updated git user.name to '$git_name'"
    fi
  fi
else
  read -p "Git user.name (for commits): " git_name
  if [ -n "$git_name" ]; then
    git config --global user.name "$git_name"
    echo "Set git user.name to '$git_name'"
  fi
fi

# Prompt for git user.email
current_email=$(git config --global user.email || true)
if [ -n "$current_email" ]; then
  echo "Git user.email is set to: $current_email"
  read -p "Change it? (y/N): " change_email
  if [[ "$change_email" =~ ^[Yy]$ ]]; then
    read -p "Enter new Git user.email: " git_email
    if [ -n "$git_email" ]; then
      git config --global user.email "$git_email"
      echo "Updated git user.email to '$git_email'"
    fi
  fi
else
  read -p "Git user.email (for commits): " git_email
  if [ -n "$git_email" ]; then
    git config --global user.email "$git_email"
    echo "Set git user.email to '$git_email'"
  fi
fi

# Prompt for git user.signingkey (SSH public key)
current_signingkey=$(git config --global user.signingkey || true)
echo ""
if [ -n "$current_signingkey" ]; then
  echo "Git commit signing is already configured"
  read -p "Change the signing key? (y/N): " change_signingkey
  if [[ "$change_signingkey" =~ ^[Yy]$ ]]; then
    read -p "Enter your new SSH public key for signing (or leave blank to skip): " git_signingkey
    if [ -n "$git_signingkey" ]; then
      git config --global user.signingkey "$git_signingkey"
      echo "Updated git signing key"
    fi
  fi
else
  echo "Git commit signing with SSH key (optional):"
  read -p "Enter your SSH public key for signing (or leave blank to skip): " git_signingkey
  if [ -n "$git_signingkey" ]; then
    git config --global user.signingkey "$git_signingkey"
    git config --global gpg.format ssh
    git config --global commit.gpgsign true
    echo "Commit signing enabled with SSH key"
  fi
fi

echo ""

# ====================
# Configure Git Large File Storage (LFS)
# ====================
echo "Configuring Git LFS..."
git lfs install

# ====================
# Create symlinks for managed configuration files
# ====================
echo "Creating symlinks..."

link_file "$DOTFILES_DIR/zsh/.zprofile"     "$HOME/.zprofile"
link_file "$DOTFILES_DIR/zsh/.zshrc"       "$HOME/.zshrc"
link_file "$DOTFILES_DIR/git/.gitconfig"   "$HOME/.gitconfig"

# Install custom oh-my-posh theme into Homebrew's theme directory
echo "Installing custom oh-my-posh theme..."
link_file "$DOTFILES_DIR/posh/jmcombs_p10k_latte.omp.json" "$POSH_THEMES_DIR/jmcombs_p10k_latte.omp.json"

# Set up Ghostty configuration in the standard XDG location
echo "Setting up Ghostty configuration..."
mkdir -p "$GHOSTTY_CONFIG_DIR"
link_file "$DOTFILES_DIR/ghostty/config" "$GHOSTTY_CONFIG_DIR/config"

# ====================
# Installation complete
# ====================
echo ""
echo "=== Setup complete! ==="
echo "• Open a new terminal or run: exec zsh"
echo "• Backups of previous configs are in: $BACKUP_DIR"
echo ""
echo "Optional post-install steps:"
echo "• 1Password CLI: Run 'op plugin init <plugin>' for shell integrations"
echo "  Available plugins: gh, aws, glab, stripe, etc. (see 'op plugin list')"
echo "• Mac App Store: Caffeinated, Wipr 2, Yoink"
echo "• Direct downloads: DDPM, Cisco Accessory Hub, Webex, Microsoft Office/Teams"
echo "• A reboot is recommended (required for Logitech Options+ and some drivers)"
echo ""
echo "Your macOS environment is now fully configured and portable. Enjoy!"