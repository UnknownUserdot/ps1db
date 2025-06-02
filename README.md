# PS1 Database Manager

⚠️ **Work in Progress**: This application is currently under development. While functional, it may have bugs and incomplete features. Use with caution.

## Overview
PS1 Database Manager is a command-line tool for managing your PlayStation 1 game collection. It helps you organize your PS1 ROMs by matching them against a database of known games, handling different regions (USA/PAL/JPN), and managing multi-disc games.

## Recent Updates
- Added region-specific game tracking (JP/EU/NA versions tracked separately)
- Improved manual matching system for unmatched games
- Added smart search tips when no matches are found
- Enhanced region detection with separate paths for each regional version
- Added visual indicators for owned games (✓/✗) by region
- Improved filename matching for games with special characters
- Better handling of multi-disc games
- Enhanced region detection (USA/PAL/JPN)
- Fixed issues with extra spaces in filenames
- Added detailed table output for search results

## Features
- **Region-Specific Collection Tracking**
  - Track JP/EU/NA versions separately
  - Visual indicators (✓/✗) for owned versions
  - Separate file paths for each regional version

- **Smart Game Matching**
  - Automatic region detection from filenames
  - Manual matching for unmatched games
  - Interactive search and selection process
  - Region availability verification

- **Helpful Search System**
  - Smart search tips when no matches found
  - Suggestions for better search terms
  - Region-specific search filtering
  - Support for partial name matching

## Installation

1. Clone or download the repository and navigate to its directory.

2. Install the required dependencies:
```bash
pip install -r requirements.txt
```

## Database Setup

The application uses two separate databases:

1. Game Database (`ps1_games.db`):
   - Ships with the package
   - Contains only game information (titles, release dates, regions)
   - Read-only, same for all users
   - No personal information

2. User Collection Database (`user_collection.db`):
   - Created in your personal app data directory:
     - Windows: `%LOCALAPPDATA%/ps1db/user_collection.db`
     - macOS/Linux: `~/.local/share/ps1db/user_collection.db`
   - Stores your personal collection data
   - Never shared or uploaded
   - Completely private to your installation

When you first run any command, the tool will:
1. Use the included game database
2. Create a personal collection database in your app data directory
3. Keep your collection data separate and private

## Usage

### Basic Commands

1. Scan your PS1 game directory:
```bash
python3 ps1db.py scan "/path/to/your/ps1/games"
```

2. Search for games:
```bash
python3 ps1db.py search "game name"
```
- Use quotes for names with spaces
- Optional: Filter by region with `-r` flag (NA/EU/JP)
- Optional: Show only games in your collection with `-l` flag

3. View collection statistics:
```bash
python3 ps1db.py stats
```

### Search Results
The search command displays results in a formatted table with the following information:
- Title: Game title
- Serial: Game serial number
- Developer: Game developer
- Publisher: Game publisher
- Regions: Available regions with ownership status (JP ✓/✗ | EU ✓/✗ | NA ✓/✗)

### Examples

Search for a specific game:
```bash
python3 ps1db.py search "Final Fantasy VII"
```

Search for Japanese games only:
```bash
python3 ps1db.py search -r JP "Final Fantasy"
```

Show all games in your collection:
```bash
python3 ps1db.py search -l
```

View collection statistics:
```bash
python3 ps1db.py stats
```

## Database Statistics
The database currently includes:
- Total Games: 4099
- Regional Breakdown:
  * Japan: 3014 titles
  * Europe: 1267 titles
  * North America: 1372 titles

## Known Issues
- Some multi-disc games may not match correctly
- Japanese titles might need exact matching
- Special game versions (like Gran Turismo 2 Arcade/Simulation) need manual verification
- Some games with colons or special characters in titles may not match perfectly

## Contributing
This is an open-source project in active development. Contributions, bug reports, and feature requests are welcome!

## Disclaimer
This tool is for personal use in managing legally obtained game backups. The developers do not condone or promote piracy. 