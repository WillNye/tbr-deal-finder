# tbr-deal-finder

Track price drops and find deals on books in your TBR (To Be Read) list across audiobook and ebook formats.

## Features
- Uses your StoryGraph exports, Goodreads exports, and custom csvs (spreadsheet) to track book deals
- Supports multiple of the library exports above 
- Supports multiple locales and currencies
- Finds the latest and active deals from supported sellers
- Simple CLI interface for setup and usage
- Only get notified for new deals or view all active deals 

## Support

### Audiobooks
* Audible
* Chirp
* Libro.fm (Work in progress)

### Locales
* US
* CA
* UK
* AU
* FR
* DE
* JP
* IT
* IN
* ES
* BR

## Installation Guide

### Python (Recommended)
1. If it's not already on your computer, download Python https://www.python.org/downloads/
   1. tbr-deal-finder requires Python3.13 or higher
2. Optional: Install and use virtualenv
3. Open your Terminal/Commmand Prompt
4. Run `pip3.13 install tbr-deal-finder`

### UV
1. Clone the repository:
   ```sh
   git clone https://github.com/yourusername/tbr-deal-finder.git
   cd tbr-deal-finder
   ```
2. Install uv:
   https://docs.astral.sh/uv/getting-started/installation/

## Configuration
This tool relies on the csv generated by the app you use to track your TBRs.
Here are the steps to get your export.

### StoryGraph
* Open https://app.thestorygraph.com/ in the browser of your choice
* Click on your profile icon in the top right corner
* Select "Manage Account"
* Scroll down to "Manage Your Data"
* Click the button "Export StoryGraph Library"
* You will be navigated to https://app.thestorygraph.com/user-export
* Click "Generate export"
* Wait a few minutes and refresh the page
* A new item will appear that says "Your export from ... - Download" will appear
* Click "Download"

### Goodreads
* Open https://www.goodreads.com/review/import in the browser of your choice
* At the top of the page click the button "Export Library"
* Wait a few minutes and refresh the page
* A new item will appear that says "Your export from ..." will appear
* Click it to download the csv

### Custom csv
If you've got your own CSV you're using to track your TBRs all you need are the following columns for it to be in a valid format
* `Title`
* `Authors`
* `Read Status`* (See below)
 
Optionally, you can add the `Read Status` column. Set `to-read` for all books you want to be tracked.
If you don't add this column the deal finder will run on ALL books in the CSV.

### tbr-deal-finder setup

#### Python
```sh
tbr-deal-finder setup
```

#### UV
```sh
uv run -m tbr_deal_finder.main setup
```

You will be prompted to:
- Enter the path(s) to your StoryGraph export CSV file(s)
- Select your locale (country/region)
- Set your maximum price for deals
- Set your minimum discount percentage

The configuration will be saved for future runs.

## Usage
All commands are available via the CLI:

- `setup`         – Set up or update your configuration interactively.
- `latest-deals`  – Find and print the latest book deals based on your config.
- `active-deals`  – Show all currently active deals.

#### Python
```sh
tbr-deal-finder [COMMAND]
```

#### UV
```sh
uv run -m tbr_deal_finder.main [COMMAND]
```

Example:
```sh
tbr-deal-finder latest-deals

# or

uv run -m tbr_deal_finder.main latest-deals
```

## Updating your TBR
To update tbr-deal-finder as your TBR changes, regenerate and download your library export.
See [Configuration](#Configuration) for steps.


## Updating the tbr-deal-finder

### Python
```sh
pip3.13 install tbr-deal-finder --upgrade
```

### UV
```sh
# From the repo directory
git checkout main && git fetch
```


---

Happy deal hunting!
