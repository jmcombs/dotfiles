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

---

### How to use these Modelfiles with Pi
Since the model parameters (temperature, top_p, etc.) are now encapsulated in Ollama `Modelfile`s rather than just being passed via API calls, you must register them locally before they can be used by the Pi Agent.

#### Step 1: Register the models in Ollama
Run these commands in your terminal to create local versions of the models with optimized parameters:
```bash
ollama create gemma4-31b-tuned -f ollama/gemma4-31b.Modelfile
ollama create gemma4-26b-tuned -f ollama/gemma4-26b.Modelfile
ollama create qwen3.6-coding-tuned -f ollama/qwen3.6-coding.Modelfile
```

#### Step 2: Configure Pi to use the tuned models
Update `pi/.pi/agent/models.json` so that the `id` field of your model entry matches the name you created in Ollama (e.g., change `"gemma4:31b-mxfp8"` to `"gemma4-31b-tuned"`).
