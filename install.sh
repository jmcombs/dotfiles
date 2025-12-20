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

echo ""

# ====================
# Configure macOS Terminal profile (Github Light)
# ====================
PROFILE_FILE="$DOTFILES_DIR/terminal/GitHub Light.terminal"
echo "Configuring macOS Terminal profile..."
if [ -f "$PROFILE_FILE" ]; then
  # Read current default profile; if not Github, import and set
  current_default=$(defaults read com.apple.Terminal "Default Window Settings" 2>/dev/null || echo "")
  if [ "$current_default" != "GitHub Light" ]; then
    echo "Importing GitHub Light Terminal profile and setting as default..."
    # Import the .terminal profile into Terminal (adds it to Profiles)
    open "$PROFILE_FILE"
    # Give macOS a moment to register the profile
    sleep 1
    # Set as default and startup profile
    defaults write com.apple.Terminal "Default Window Settings" -string "GitHub Light"
    defaults write com.apple.Terminal "Startup Window Settings" -string "GitHub Light"
    echo "macOS Terminal default profile set to: GitHub Light"
  else
    echo "macOS Terminal default profile already set to GitHub Light."
  fi
else
  echo "Terminal profile not found at: $PROFILE_FILE"
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