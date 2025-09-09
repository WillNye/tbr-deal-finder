# Desktop App Guide

Everything you need to know about installing, using, and updating the TBR Deal Finder desktop application.

## Installation

The desktop app provides a beautiful graphical interface for managing your book deals without any command line knowledge required.

### 🍎 macOS Installation

#### Download & Install
1. Go to the [latest release](https://github.com/yourusername/tbr-deal-finder/releases/latest)
2. Download `TBRDealFinder-{version}-macOS.dmg`
3. **Open the DMG**: Double-click the downloaded `.dmg` file
4. **Handle Security Warning**: macOS will show "Cannot verify developer"
   - Click Done to handle the warning before continuing with the install
   - [Follow guide from Apple](https://support.apple.com/guide/mac-help/open-a-mac-app-from-an-unknown-developer-mh40616/mac)
5. **Install**: Drag the TBR Deal Finder app to your Applications folder
6. **Launch**: Double-click the app in Applications
7. **Wait for loader**: The app has a special loader and can take a minute to load for the first time

#### Troubleshooting macOS
- **"App can't be opened"**: Use right-click → Open instead of double-clicking
- **Still getting warnings**: Go to System Preferences → Security & Privacy → General → Click "Open Anyway"

### 🪟 Windows Installation

#### Download & Install
1. Go to the [latest release](https://github.com/yourusername/tbr-deal-finder/releases/latest)
2. Download `TBRDealFinder-{version}-Windows.exe`
3. **Run the Installer**: Double-click the downloaded `.exe` file
4. **Handle Security Warning**: Windows will show "Unknown publisher"
   - **Solution**: Click "More info" → Click "Run anyway"
5. **Install**: Follow the installation wizard
6. **Launch**: The app will be available in your Start Menu or Desktop
7. **Wait for loader**: The app has a special loader and can take a minute to load for the first time

#### Troubleshooting Windows
- **Windows Defender blocks**: Click "More info" → "Run anyway"
- **Still blocked**: Temporarily disable real-time protection, install, then re-enable

## 🎯 First Time Setup

### Getting Your Reading Lists
Before using the app, export your reading lists:

#### StoryGraph Export
1. Open [StoryGraph](https://app.thestorygraph.com/)
2. Click your profile icon → "Manage Account"
3. Scroll to "Manage Your Data" → "Export StoryGraph Library"
4. Click "Generate export" → Wait and refresh → Download CSV

#### Goodreads Export  
1. Visit [Goodreads Export](https://www.goodreads.com/review/import)
2. Click "Export Library" → Wait for email → Download CSV

#### Custom CSV
Create your own with these columns:
- `Title` (required)
- `Authors` (required)
- `Read Status` (optional: set to "to-read" for tracking)

### Setup Wizard
1. **Launch the App** for the first time
2. **Follow the Setup Wizard**:
   - Upload your CSV file(s)
   - Select your country/region
   - Set maximum price for deals  
   - Set minimum discount percentage
3. **Start Finding Deals**: The app begins searching automatically

## 🔄 Updating the Desktop App

### Checking for Updates
Currently, updates require manual download:
1. **Check Current Version**: Look in Settings/About section
2. **Visit Releases**: Go to [latest releases](https://github.com/yourusername/tbr-deal-finder/releases/latest)
3. **Compare Versions**: See if a newer version is available

### Installing Updates

#### All Platforms
1. **Download Latest Version**:
   - macOS: `TBRDealFinder-{version}-macOS.dmg`
   - Windows: `TBRDealFinder-{version}-Windows.exe`
2. **Install Over Existing**: Follow same installation steps
   - If prompted, choose to replace files or overwrite the existing application
3. **Preserve Settings**: Your configuration and data are automatically preserved
4. **Verify Update**: Check version in Settings after installation

## ❓ Troubleshooting

### App Won't Launch
- **macOS**: Right-click app → Open, check Security & Privacy settings
- **Windows**: Run as administrator, check Windows Defender

### No Deals Found
- **Check CSV Format**: Ensure titles and authors are correct
- **Adjust Filters**: Lower discount threshold or raise price limit
- **Wait**: Deals fluctuate - check back regularly

### Performance Issues
#### Initial Run
When the app initially starts the app may be white up to a minute while the tbr deal finder package loads.

#### Getting latest deals
Getting pricing info for Kindle can take up to a second per book.
It doesn't sound like a lot, but if you have 400 books in your tbr it may take around 7 minutes.
If you're not checking for deals on Kindle, getting deals should only take a couple minutes.
Don't close the app while getting deals or progress may be lost.

#### Still having issues
- **Restart App**: Close and reopen to clear memory
- **Update**: Ensure you're running the latest version
- **System**: Close other applications to free resources

## 🆘 Getting Help

### Community Support
1. **GitHub Issues**: [Report bugs or ask questions](https://github.com/yourusername/tbr-deal-finder/issues)
2. **Search First**: Someone might have had the same issue
3. **Provide Details**: Include OS version, error messages, screenshots

### What to Include in Bug Reports
- **Operating System**: macOS 12.1, Windows 11, Ubuntu 22.04, etc.
- **App Version**: Found in Settings/About
- **Error Messages**: Exact text of any errors
- **Screenshots**: Visual problems are easier to diagnose
- **Steps to Reproduce**: What you did when the problem occurred

---

**Ready to discover amazing book deals? Download the desktop app and start saving money on your reading list!** 📚💰
