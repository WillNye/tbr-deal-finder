# 🛠️ Development Guide

Complete guide for developers and contributors who want to work with TBR Deal Finder source code, customize features, or contribute improvements.

## 🚀 Development Installation

### Prerequisites

#### Git
```bash
# Verify Git is installed
git --version
```
Install from [git-scm.com](https://git-scm.com/downloads) if needed.

#### UV (Recommended Package Manager)
UV is fast and perfect for Python development:
```bash
# Install UV (macOS/Linux)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install UV (Windows)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Verify installation
uv --version
```

Alternative: [UV Installation Guide](https://docs.astral.sh/uv/getting-started/installation/)

### Setting Up the Development Environment

#### Clone and Install
```bash
# Clone the repository
git clone https://github.com/yourusername/tbr-deal-finder.git
cd tbr-deal-finder

# Install project and all dependencies
uv sync

# Verify installation
uv run -m tbr_deal_finder.cli --help
```

## 🔧 Development Setup

### Initial Configuration
```bash
# Set up your development configuration
uv run -m tbr_deal_finder.cli setup
```

## 📖 Development Usage

### Running from Source

#### CLI Commands
```bash
# Development setup
uv run -m tbr_deal_finder.cli setup

# Find deals
uv run -m tbr_deal_finder.cli latest-deals
uv run -m tbr_deal_finder.cli active-deals

# Check version
uv run -m tbr_deal_finder.cli --version
```

#### GUI Application
```bash
# Launch desktop GUI from source
uv run -m tbr_deal_finder.gui.main
```

### Development Workflow

#### 1. Code Changes
Make your changes using any editor or IDE:
- **VS Code**: Excellent Python support
- **PyCharm**: Full-featured Python IDE  
- **Vim/Neovim**: Lightweight editing
- **Any text editor**: Python is readable!

#### 2. Testing Changes
```bash
# Test CLI functionality
uv run -m tbr_deal_finder.cli $TARGET_COMMAND

# Test GUI changes
uv run -m tbr_deal_finder.gui.main
```

## 🔄 Staying Updated

### Sync with Upstream
```bash
# Pull latest changes
git checkout main
git pull origin main

# Update dependencies
uv sync

# Verify everything works
uv run -m tbr_deal_finder.cli --version
```

### Branch Management
```bash
# List available branches
git branch -r

# Switch to feature branch
git checkout feature-branch-name
uv sync  # Update dependencies for branch

# Create new feature branch
git checkout -b feature/my-new-feature
```

### Managing Dependencies
```bash
# Add new dependency
uv add requests

# Add development dependency
uv add --dev pytest

# Remove dependency
uv remove requests

# Update specific dependency
uv lock --upgrade-package requests

# Update all dependencies
uv lock --upgrade
```

## 🧪 Advanced Development

### Adding New Retailers
1. **Create retailer module**: `tbr_deal_finder/retailer/new_retailer.py`
2. **Implement required methods**: Search, parse deals, handle authentication
3. **Add to retailer factory**: Register in `tbr_deal_finder/retailer/__init__.py`
4. **Update configuration**: Add retailer options to setup
5. **Test thoroughly**: Verify deal discovery works

### Database Schema Changes
```bash
# Create migration
# Edit tbr_deal_finder/migrations.py
# Add migration function

# Test migration
uv run python -c "from tbr_deal_finder import migrations; migrations.run_migrations()"
```

### GUI Development
```bash
# Run GUI with hot reload (if available)
uv run -m tbr_deal_finder.gui.main --debug

# Edit pages in tbr_deal_finder/gui/pages/
# Changes require app restart
```

### Performance Profiling
```bash
# Profile CLI performance
uv run python -m cProfile -o profile.prof -m tbr_deal_finder.cli latest-deals

# Analyze profile
uv run python -c "import pstats; pstats.Stats('profile.prof').sort_stats('cumulative').print_stats(20)"
```

## 🚀 Contributing

### Before Contributing
1. **Fork the repository** on GitHub
2. **Clone your fork**: `git clone https://github.com/yourusername/tbr-deal-finder.git`
3. **Create feature branch**: `git checkout -b feature/description`
4. **Set up development environment**: `uv sync`

### Development Standards
- **Code Style**: Follow PEP 8, use Black formatter
- **Type Hints**: Add type annotations for new functions
- **Documentation**: Update docstrings and documentation
- **Dependencies**: Minimize new dependencies

### Pull Request Process
1. **Ensure tests pass**: Run full test suite
2. **Update documentation**: Include relevant doc updates
3. **Describe changes**: Clear PR description with examples
4. **Link issues**: Reference any related GitHub issues
5. **Be responsive**: Address review feedback promptly

