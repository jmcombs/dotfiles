# jmcombs/dotfiles

Personal macOS configuration – apps, shell, Ghostty, oh-my-posh theme.

## One-Command Setup on a Fresh Mac

```bash
curl -fsSL https://raw.githubusercontent.com/jmcombs/dotfiles/main/install.sh | bash
```

## Future Enhancements

- [ ] macOS Terminal profile integration with Blue PSL 10K - to be implemented later

---

## One-Off Utility Tools

These tools are installed via Oh My Zsh plugins or custom scripts for specific, non-daily tasks:

- **`omz-plugin-rsvg`**: A specialized plugin for quick SVG to PNG conversions using `rsvg-convert`. Useful for one-off graphic asset processing.

## Package Rationale

This section explains why certain packages are included in this environment configuration:

### CLI & Shell Enhancements
- **`bat`**: Modern replacement for `cat` with syntax highlighting and Git integration.
- **`eza`**: A modern, feature-rich replacement for `ls`.
- **`oh-my-posh`**: Provides a highly customizable and informative shell prompt.
- **`zsh-autosuggestions` & `zsh-syntax-highlighting`**: Enhances Zsh productivity with command completions and real-time syntax feedback.

### Graphics & Media
- **`librsvg`**: Essential library for rendering SVG files; required by the `omz-plugin-rsvg` plugin.

### Development & Infrastructure
- **`gh`**: Official GitHub CLI for managing repositories, issues, and PRs directly from the terminal.
- **`docker-desktop`**: Containerization platform for local development environments.
- **`visual-studio-code`**: Primary IDE for software development.
- **`git-lfs`**: Handles large file versioning within Git repositories.

### System & Productivity
- **`stow`**: Used to manage these dotfiles via symlinks.
- **`macprefs`**: Automates the application of macOS system preferences defined in this repo.
- **`1password-cli`**: Integrates password management directly into the terminal workflow.

