# PS1 Database Manager

⚠️ **Work in Progress**: This application is currently under development. While functional, it may have bugs and incomplete features. Use with caution.

## Overview
PS1 Database Manager is a command-line tool for managing your PlayStation 1 game collection. It helps you organize your PS1 ROMs by matching them against a database of known games, handling different regions (USA/PAL/JPN), and managing multi-disc games.

## Recent Updates
- Improved filename matching for games with special characters (colons, underscores)
- Better handling of multi-disc games
- Enhanced region detection (USA/PAL/JPN)
- Fixed issues with extra spaces in filenames

## Installation

1. Clone the repository:
```bash
git clone https://github.com/UnknownUserdot/PS1.db.git
cd PS1.db
```

2. Install the package:
```bash
pip install -e .
```

This will install the `ps1db` command in your system.

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
ps1db scan "/path/to/your/ps1/games"
```

2. Search for games:
```bash
ps1db search "game name"
```
- Use quotes for names with spaces
- Optional: Filter by region with `-r` flag (NA/EU/JP)
- Optional: Show only games in your collection with `-l` flag

3. View collection statistics:
```bash
ps1db stats
```

### Examples

Search for a specific game:
```bash
ps1db search "Final Fantasy VII"
```

Search for Japanese games only:
```bash
ps1db search -r JP "Final Fantasy"
```

Show all games in your collection:
```bash
ps1db search -l
```

## Known Issues
- Some multi-disc games may not match correctly
- Japanese titles might need exact matching
- Special game versions (like Gran Turismo 2 Arcade/Simulation) need manual verification
- Some games with colons or special characters in titles may not match perfectly

## Contributing
This is an open-source project in active development. Contributions, bug reports, and feature requests are welcome!

## License
[Your chosen license]

## Disclaimer
This tool is for personal use in managing legally obtained game backups. The developers do not condone or promote piracy. 