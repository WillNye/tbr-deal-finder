# 🐍 Python CLI Guide

Complete guide for installing, using, and updating TBR Deal Finder via Python's pip package manager.

## 🚀 Installation

### Prerequisites

#### Python Installation
1. **Download Python**: Visit [python.org/downloads](https://www.python.org/downloads/)
2. **Version Required**: Python 3.13 or higher
3. **Verify Installation**:
   ```bash
   python3 --version
   # Should show Python 3.13.x or higher
   ```

#### Package Manager Check
Ensure you have pip (comes with Python 3.13+):
```bash
pip3 --version
# or
pip --version
```

### Installing TBR Deal Finder

#### Virtual Environment (Optional but recommended)
Keep your system Python clean:
```bash
# Create virtual environment
python3 -m venv tbr-env

# Activate virtual environment
# On macOS/Linux:
source tbr-env/bin/activate
# On Windows:
tbr-env\Scripts\activate

# Install in virtual environment
pip install tbr-deal-finder

# To deactivate later:
deactivate
```

#### Basic Installation
```bash
pip3 install tbr-deal-finder
```

### Verify Installation
Test that installation worked:
```bash
tbr-deal-finder --help
```

You should see the help message with available commands.

## 🔧 Initial Setup

### Getting Your Reading Lists
Before setup, export your reading lists. 
Details on that can be found in the Configuration section [here](../README) 

### Configuration Wizard
Run the interactive setup:
```bash
tbr-deal-finder setup
```

You'll be prompted to:
1. **CSV File Paths**: Enter path(s) to your exported reading lists
2. **Locale Selection**: Choose your country/region for deals
3. **Price Limits**: Set maximum amount you want to spend
4. **Discount Threshold**: Minimum discount percentage (e.g., 20%)

Configuration is saved automatically for future use.

## 📖 Using the CLI

### Available Commands

#### Setup and Configuration
```bash
# Initial setup or update configuration
tbr-deal-finder setup

# View current version
tbr-deal-finder --version

# Get help
tbr-deal-finder --help
tbr-deal-finder [command] --help
```

#### Finding Deals
```bash
# Find new deals since last check
tbr-deal-finder latest-deals

# Browse all currently active deals  
tbr-deal-finder active-deals
```

#### GUI Access (Optional)
If you want the desktop interface:
```bash
# Launch graphical interface
tbr-deal-finder-gui
```

### Understanding Command Output

#### Latest Deals Output
Shows deals discovered since your last run:
- **Book title and author**
- **Retailer** (Audible, Kindle, Chirp, Libro.fm)
- **Original price** vs **Sale price**
- **Discount percentage**
- **Direct purchase link**

#### Active Deals Output
Shows all currently available deals:
- **Same information as latest deals**
- **Includes previously seen deals**
- **Great for browsing all options**

### Command Examples
```bash
# Complete workflow example
tbr-deal-finder setup                 # One-time configuration
tbr-deal-finder latest-deals          # Check for new deals
tbr-deal-finder active-deals          # Browse all available deals

# Update configuration
tbr-deal-finder setup                 # Add new CSV files or change settings

# Quick help
tbr-deal-finder --help               # General help
tbr-deal-finder setup --help         # Command-specific help
```

## 🔄 Regular Usage Workflow

### Daily Deal Checking (2 minutes)
```bash
# Quick check for new deals
tbr-deal-finder latest-deals
```
- **Best Time**: Morning or evening routine
- **Frequency**: Daily for best deal coverage
- **Output**: Only shows new deals since last run

### Weekly Deal Browsing (10 minutes)
```bash
# See all active deals
tbr-deal-finder active-deals
```
- **Purpose**: Comprehensive view of all current deals
- **Best For**: Weekend browsing when you have more time
- **Planning**: Great for planning weekly book purchases

### Monthly Maintenance (15 minutes)
```bash
# Update your reading lists
tbr-deal-finder setup
```
- **Update CSV Files**: Upload fresh exports from reading apps
- **Adjust Settings**: Update price limits or discount thresholds
- **Clean Library**: Remove purchased books from tracking

### Advanced Usage Patterns

#### Automation with Cron (Linux/macOS)
```bash
# Add to crontab for daily 9 AM checks
0 9 * * * /usr/local/bin/tbr-deal-finder latest-deals

# Email results to yourself
0 9 * * * /usr/local/bin/tbr-deal-finder latest-deals | mail -s "Daily Book Deals" you@email.com
```

#### Output Redirection
```bash
# Save deals to a file
tbr-deal-finder latest-deals > today-deals.txt

# Append to running log
tbr-deal-finder latest-deals >> all-deals.log

# Filter and process output
tbr-deal-finder active-deals | grep "Audible" | head -5
```

## 🔄 Updating

### Check Current Version
```bash
# See installed version
tbr-deal-finder --version

# Check what's installed
pip show tbr-deal-finder

# See if updates are available
pip list --outdated | grep tbr-deal-finder
```

### Standard Updates
```bash
# Upgrade to latest version
pip3 install tbr-deal-finder --upgrade
```

### Alternative Update Commands
```bash
# Using pip directly
pip install tbr-deal-finder --upgrade

# Using python -m pip
python3 -m pip install tbr-deal-finder --upgrade

# For specific Python version
python3.13 -m pip install tbr-deal-finder --upgrade
```

### Virtual Environment Updates
```bash
# Activate environment first
source tbr-env/bin/activate  # macOS/Linux
# tbr-env\Scripts\activate     # Windows

# Then upgrade
pip install tbr-deal-finder --upgrade

# Verify update
tbr-deal-finder --version
```

### Update Troubleshooting
```bash
# Force clean reinstall
pip uninstall tbr-deal-finder
pip install tbr-deal-finder

# Clear pip cache if needed
pip install --no-cache-dir --upgrade tbr-deal-finder

# Force reinstall with dependencies
pip install --force-reinstall tbr-deal-finder
```

## 🐛 Troubleshooting

### Installation Issues

#### "Command not found: tbr-deal-finder"
**Problem**: pip installed to directory not in PATH

**Solutions**:
```bash
# Option 1: Use full Python module path
python3 -m tbr_deal_finder.cli setup
python3 -m tbr_deal_finder.cli latest-deals

# Option 2: Add pip bin to PATH (add to ~/.bashrc or ~/.zshrc)
export PATH="$HOME/.local/bin:$PATH"

# Option 3: Use virtual environment (recommended)
python3 -m venv tbr-env
source tbr-env/bin/activate
pip install tbr-deal-finder
```

#### "Permission denied" during installation
**Solutions**:
```bash
# Option 1: Install for current user only
pip3 install --user tbr-deal-finder

# Option 2: Use virtual environment (recommended)
python3 -m venv tbr-env
source tbr-env/bin/activate
pip install tbr-deal-finder

# Option 3: Use sudo (not recommended)
sudo pip3 install tbr-deal-finder
```

#### Python version conflicts
```bash
# Use specific Python version
python3.13 -m pip install tbr-deal-finder
python3.13 -m tbr_deal_finder.cli setup

# Check available Python versions
ls /usr/bin/python*  # Linux/macOS
# or
py -0                # Windows
```

### Usage Issues

#### No deals found
**Possible causes and solutions**:
- **Check CSV format**: Ensure titles and authors match book listings
- **Adjust filters**: Lower discount threshold or raise price limit
- **Verify configuration**: Run `tbr-deal-finder setup` to review settings
- **Network issues**: Ensure internet connection is working

#### Configuration not saving
**Solutions**:
```bash
# Check permissions on config directory
ls -la ~/.config/  # or equivalent on Windows

# Run setup again with verbose output
tbr-deal-finder setup

# Verify config file exists and is readable
# Config location varies by OS - check documentation
```

#### SSL/Certificate errors
```bash
# Update certificates
pip install --upgrade certifi

# Use trusted hosts if behind firewall
pip install --trusted-host pypi.org --trusted-host pypi.python.org tbr-deal-finder
```

### Performance Issues

#### Slow deal checking
- **Network**: Check internet connection speed
- **Location**: Use locale closest to your region
- **Frequency**: Don't run too frequently (max once per hour)

#### Memory usage
- **Virtual Environment**: Use isolated environments
- **Python Version**: Ensure using supported Python 3.13+
- **System Resources**: Close other applications if needed

## 💡 Advanced Usage

### Multiple Configurations
```bash
# Use different config files for different reading lists
tbr-deal-finder --config-file ~/work-books.config setup
tbr-deal-finder --config-file ~/personal-books.config setup
```

### Integration with Other Tools
```bash
# Use with grep for filtering
tbr-deal-finder active-deals | grep -i "audible"

# Count number of deals
tbr-deal-finder latest-deals | wc -l

# Extract just book titles
tbr-deal-finder active-deals | grep -E "^[A-Za-z]" | head -10
```

### Development and Testing
```bash
# Install development version from GitHub
pip install git+https://github.com/yourusername/tbr-deal-finder.git

# Install specific version
pip install tbr-deal-finder==0.2.1

# Install pre-release versions
pip install --pre tbr-deal-finder
```

## 🎯 Tips for Success

### Optimize Your Reading Lists
- **Keep Updated**: Remove purchased books regularly
- **Multiple Sources**: Combine StoryGraph, Goodreads, and custom lists
- **Series Tracking**: Include upcoming books in series you follow

### Configuration Best Practices
- **Realistic Prices**: Set maximum prices you'll actually pay
- **Sweet Spot Discounts**: Usually 20-30% minimum works well
- **Multiple Retailers**: Enable all retailers you use

### Automation Ideas
- **Daily Cron Jobs**: Automatic morning deal checks
- **Email Integration**: Get deals delivered to inbox
- **Log Files**: Keep history of deals for analysis

## ✅ Why Choose Python CLI?

### Advantages
- **Lightweight**: Minimal system resources
- **Automation**: Easy to script and automate
- **Integration**: Works with other command-line tools
- **Flexible**: Customize behavior with scripts
- **Fast**: Quick execution for regular checks

### Best For
- **Python Developers**: Natural fit for existing workflow
- **Power Users**: Those comfortable with command line
- **Automation Enthusiasts**: Want scripted deal checking
- **Server Deployments**: Running on headless systems

---

**Ready to start finding book deals from the command line? Install with pip and begin saving!** 📚⌨️
