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
  exec ./install.sh  # Replace current process with local version
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
# Install Oh My Zsh
# ====================
echo "Installing Oh My Zsh..."
if [ ! -d "$HOME/.oh-my-zsh" ]; then
  sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)" "" --unattended
else
  echo "Oh My Zsh already installed."
fi

# ====================
# Homebrew: Install if not present
# ====================
echo "Checking Homebrew installation..."
if command -v brew >/dev/null 2>&1 && [ -x "/opt/homebrew/bin/brew" ]; then
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
brew bundle --no-lock  # Prevent creation of a lockfile

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
echo "• Remaining manual installations:"
echo "   - Mac App Store: Caffeinated, Wipr 2, Yoink"
echo "   - Direct downloads: DDPM, Cisco Accessory Hub, Webex, Microsoft Office/Teams"
echo "• A reboot is recommended (required for Logitech Options+ and some drivers)"
echo ""
echo "Your macOS environment is now fully configured and portable. Enjoy!"