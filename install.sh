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

# Ghostty configuration directory (XDG-compliant location)
GHOSTTY_CONFIG_DIR="$HOME/.config/ghostty"

# Blue PSL 10K theme repository (external)
BLUE_PSL_REPO_URL="https://github.com/jmcombs/blue-psl-10k.git"
BLUE_PSL_CACHE_DIR="$DOTFILES_DIR/.cache/blue-psl-10k"

# Theme target directories for external themes
OH_MY_POSH_THEMES_DIR="$HOME/.config/oh-my-posh/themes"
GHOSTTY_THEMES_DIR="$GHOSTTY_CONFIG_DIR/themes"

echo "=== jmcombs/dotfiles Installer ==="
echo "Dotfiles location: $DOTFILES_DIR"
echo "Backup directory:  $BACKUP_DIR"
echo ""

# ====================
# Ensure Xcode Command Line Tools are installed
# ====================
# Skip Xcode CLI check when installer re-executes itself (controlled by DOTFILES_INSTALLING)
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
# Helper functions
# ====================

# Back up and remove an existing config file if it is not already a symlink
backup_config() {
  local path="$1"
  if [ -e "$path" ] && [ ! -L "$path" ]; then
    local name
    name="$(basename "$path")"
    echo "Backing up existing $name to $BACKUP_DIR"
    mv "$path" "$BACKUP_DIR/"
  fi
}

# Install Oh My Zsh plugins
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
# Configure Git Large File Storage (LFS)
# ====================
echo "Configuring Git LFS..."
git lfs install

# ====================
# Deploy dotfiles using GNU Stow
# ====================
echo "Deploying dotfiles with GNU stow..."
cd "$DOTFILES_DIR"

# Back up any existing config files that would conflict with stow-managed symlinks
backup_config "$HOME/.zshrc"
backup_config "$HOME/.zprofile"
backup_config "$HOME/.gitconfig"

stow zsh git ghostty
cd -

echo ""

# ====================
# Blue PSL 10K Theme Setup
# ====================
echo "Setting up Blue PSL 10K themes..."

# Ensure config and theme directories exist
mkdir -p "$GHOSTTY_CONFIG_DIR"
mkdir -p "$GHOSTTY_THEMES_DIR"
mkdir -p "$OH_MY_POSH_THEMES_DIR"

# Clone or update the Blue PSL 10K repository
if [ -d "$BLUE_PSL_CACHE_DIR/.git" ]; then
  echo "Updating Blue PSL 10K theme repository..."
  git -C "$BLUE_PSL_CACHE_DIR" pull --ff-only
else
  echo "Cloning Blue PSL 10K theme repository..."
  rm -rf "$BLUE_PSL_CACHE_DIR"
  mkdir -p "$(dirname "$BLUE_PSL_CACHE_DIR")"
  git clone "$BLUE_PSL_REPO_URL" "$BLUE_PSL_CACHE_DIR"
fi

# Copy Oh-My-Posh theme
if [ -f "$BLUE_PSL_CACHE_DIR/posh/blue-psl-10k.omp.json" ]; then
  cp "$BLUE_PSL_CACHE_DIR/posh/blue-psl-10k.omp.json" "$OH_MY_POSH_THEMES_DIR/"
else
  echo "Warning: blue-psl-10k.omp.json not found in Blue PSL 10K repo; skipping Oh-My-Posh theme copy."
fi

# Copy Ghostty theme
if [ -f "$BLUE_PSL_CACHE_DIR/ghostty/blue-psl-10k" ]; then
  cp "$BLUE_PSL_CACHE_DIR/ghostty/blue-psl-10k" "$GHOSTTY_THEMES_DIR/"
else
  echo "Warning: Ghostty theme file 'blue-psl-10k' not found in Blue PSL 10K repo; skipping Ghostty theme copy."
fi

echo ""

# ====================
# Configure Git User Settings (create .gitconfig.local)
# ====================
echo "Setting up Git user configuration..."
echo ""

if [ ! -f "$HOME/.gitconfig.local" ]; then
  echo "Creating ~/.gitconfig.local for user-specific settings..."
  
  read -p "Git user.name (for commits): " git_name
  read -p "Git user.email (for commits): " git_email
  
  cat > "$HOME/.gitconfig.local" << EOF
[user]
    name = $git_name
    email = $git_email
EOF

  echo "Git user.name set to: $git_name"
  echo "Git user.email set to: $git_email"
  
  echo ""
  echo "Git commit signing with SSH key (optional):"
  read -p "Enter your SSH public key for signing (or leave blank to skip): " git_signingkey
  if [ -n "$git_signingkey" ]; then
    cat >> "$HOME/.gitconfig.local" << EOF
    signingkey = $git_signingkey
EOF
    echo "Commit signing enabled with SSH key"
  fi
else
  echo "~/.gitconfig.local already exists"
  # Read current settings from ~/.gitconfig.local for portability across environments
  current_name=$(git config -f "$HOME/.gitconfig.local" user.name 2>/dev/null || true)
  current_email=$(git config -f "$HOME/.gitconfig.local" user.email 2>/dev/null || true)
  current_signingkey=$(git config -f "$HOME/.gitconfig.local" user.signingkey 2>/dev/null || true)
  echo "Current Git settings:"
  echo "  Name:  ${current_name:-<not set>}"
  echo "  Email: ${current_email:-<not set>}"
  if [ -n "$current_signingkey" ]; then
    echo "  Signing key: $current_signingkey"
  else
    echo "  Signing key: <none>"
  fi

  read -p "Change all three fields now? (y/N): " change_all
  if [[ "$change_all" =~ ^[Yy]$ ]]; then
    read -p "New Git user.name: " git_name
    read -p "New Git user.email: " git_email
    read -p "New SSH public signing key (or leave blank): " git_signingkey

    # Rewrite ~/.gitconfig.local with updated values
    {
      printf "[user]\n"
      printf "    name = %s\n" "$git_name"
      printf "    email = %s\n" "$git_email"
      if [ -n "$git_signingkey" ]; then
        printf "    signingkey = %s\n" "$git_signingkey"
      fi
    } > "$HOME/.gitconfig.local"

    echo "Updated ~/.gitconfig.local"
  else
    echo "No changes made. Edit ~/.gitconfig.local to update later."
  fi
fi

echo ""

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