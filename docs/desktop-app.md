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
   - [Opening app from unknown developer](https://support.apple.com/guide/mac-help/open-a-mac-app-from-an-unknown-developer-mh40616/mac)
5. **Install**: Drag the TBR Deal Finder app to your Applications folder
6. **Launch**: Double-click the app in Applications

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

#### Troubleshooting Windows
- **Windows Defender blocks**: Click "More info" → "Run anyway"
- **Still blocked**: Temporarily disable real-time protection, install, then re-enable

### 🐧 Linux Installation

#### Download & Install
1. Go to the [latest release](https://github.com/yourusername/tbr-deal-finder/releases/latest)
2. Download `TBRDealFinder-{version}-Linux`
3. **Make Executable**: 
   ```bash
   chmod +x TBRDealFinder-{version}-Linux
   ```
4. **Move to Applications** (optional):
   ```bash
   sudo mv TBRDealFinder-{version}-Linux /usr/local/bin/tbr-deal-finder
   ```
5. **Launch**: 
   ```bash
   ./TBRDealFinder-{version}-Linux
   # Or if moved: tbr-deal-finder
   ```

#### Create Desktop Entry (Linux)
For easier launching, create a desktop entry:
```bash
cat > ~/.local/share/applications/tbr-deal-finder.desktop << EOF
[Desktop Entry]
Name=TBR Deal Finder
Comment=Track price drops and find deals on books
Exec=/path/to/TBRDealFinder-{version}-Linux
Icon=applications-office
Terminal=false
Type=Application
Categories=Office;Utility;
EOF
```

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

## 📖 Using the Desktop App

### Main Interface

#### 🆕 Latest Deals View
- **Purpose**: Shows newly discovered deals since your last check
- **Features**: Book covers, titles, authors, current and original prices
- **Actions**: Click any book for detailed information and purchase links

#### 📚 All Active Deals View  
- **Purpose**: Browse all currently active deals
- **Features**: Filter by retailer, price range, discount percentage
- **Sorting**: By discount amount, price, or date discovered
- **Best For**: Weekly browsing of all available deals

#### 📖 All Books View
- **Purpose**: Manage your tracked books library
- **Features**: See all books being tracked for deals
- **Actions**: Add new books or remove books from tracking
- **Status**: See which books currently have active deals

#### ⚙️ Settings View
- **Configuration**: Update deal preferences and price limits
- **Data Management**: Add new CSV files or update existing ones
- **Notifications**: Configure how you want to be alerted about deals
- **Account**: Manage your locale and retailer preferences

### Navigation Tips
- **Side Menu**: Quick switching between views
- **Search Bar**: Find specific books or authors instantly  
- **Filter Panel**: Narrow results by price, discount, or retailer
- **Book Details**: Click any book for comprehensive information

### Understanding Deal Information
Each deal displays:
- **Book cover and title**
- **Author name(s)**
- **Original price** vs **Sale price**
- **Discount percentage** 
- **Retailer** (Audible, Kindle, Chirp, Libro.fm)
- **Deal expiration** (when available)

## 🔄 Regular Usage Workflow

### Daily Deal Checking (5 minutes)
1. **Open the App**
2. **Check Latest Deals View** 
3. **Review New Discoveries**
4. **Click Through** to purchase interesting deals

### Weekly Management (15 minutes)  
1. **Browse All Active Deals** for comprehensive view
2. **Update Your Library** by adding new books to track
3. **Remove Purchased Books** to keep library current
4. **Adjust Settings** if your preferences have changed

### Monthly Maintenance (30 minutes)
1. **Export Fresh Reading Lists** from StoryGraph/Goodreads
2. **Upload Updated CSVs** via Settings
3. **Review Price Limits** and adjust for seasonal sales
4. **Clean Up Library** by removing uninteresting books

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
   - Linux: `TBRDealFinder-{version}-Linux`
2. **Install Over Existing**: Follow same installation steps
3. **Preserve Settings**: Your configuration and data are automatically preserved
4. **Verify Update**: Check version in Settings after installation

## ❓ Troubleshooting

### App Won't Launch
- **macOS**: Right-click app → Open, check Security & Privacy settings
- **Windows**: Run as administrator, check Windows Defender
- **Linux**: Verify file permissions (`chmod +x`)

### No Deals Found
- **Check CSV Format**: Ensure titles and authors are correct
- **Adjust Filters**: Lower discount threshold or raise price limit
- **Wait**: Deals fluctuate - check back regularly

### Performance Issues
- **Restart App**: Close and reopen to clear memory
- **Update**: Ensure you're running the latest version
- **System**: Close other applications to free resources

### Settings Not Saving
- **Permissions**: Ensure app can write to user directory
- **Restart**: Close app completely and reopen
- **Reinstall**: Download fresh copy if issues persist

## 📊 System Requirements

### Minimum Requirements
- **macOS**: 10.14 or later
- **Windows**: Windows 10 or later  
- **Linux**: Modern distribution with GUI support

## 💡 What Makes This App Special

### Smart Deal Discovery
- **Automated Searching**: Checks multiple retailers automatically
- **Intelligent Matching**: Finds your books across different platforms
- **Price Tracking**: Monitors for temporary sales and price drops

### User-Friendly Design
- **No Command Line**: Everything through visual interface
- **Beautiful Interface**: Modern design with book covers
- **Easy Setup**: Wizard guides you through configuration

### Comprehensive Coverage
- **Multiple Retailers**: Audible, Kindle, Chirp, Libro.fm
- **Global Support**: Works in US, CA, UK, AU, FR, DE, JP, IT, IN, ES, BR
- **Both Formats**: Audiobooks and ebooks in one place

## 🆘 Getting Help

### Self-Help Resources
1. **Check This Guide**: Most questions are answered here
2. **Try Troubleshooting**: Common issues have solutions above
3. **Update App**: Many issues are fixed in newer versions

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
