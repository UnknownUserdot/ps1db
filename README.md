# PS1 Game Collection Manager

A web-based application for managing your PlayStation 1 (PS1) game collection. This application uses a SQLite database to store comprehensive game information about your games.

## Current Features

- **SQLite Database with Game Information**:
  - Title
  - Serial Number
  - Developer
  - Publisher
  - Release Dates (JP/EU/NA)
  - Region Information
  - Launch Title Status
  - Notes

- **Collection Management**:
  - Track game ownership status (Owned/Hunting/None)
  - Add notes to your collection entries
  - Track when games were added to your collection

- **Digital Backup Tracking**:
  - Store information about your digital backups
  - Support for multiple formats (.iso, .bin, .pbp, .chd)
  - Track file checksums and verification dates
  - Store emulator-specific configurations

## Technical Stack

- **Backend**: Python with FastAPI
- **Database**: SQLite
- **Frontend**: React (in development)

## Getting Started

### Prerequisites
- Python 3.8+
- pip

### Installation

1. Clone the repository
```bash
git clone <repository-url>
cd ps1-database
```

2. Create and activate virtual environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
```

3. Install dependencies
```bash
pip install -r requirements.txt
```

### Database Setup

To create the initial database structure:

```bash
python backend/create_db.py
```

This will create a new SQLite database (`ps1_games.db`) with the following structure:

- `games` table: Stores basic game information
- `game_status` table: Tracks your collection status for each game
- `digital_backups` table: Manages information about your digital copies

The database comes with a few sample entries to demonstrate the structure. You can add your own game information manually or implement data import functionality as needed.

## Project Structure

```
ps1-database/
├── README.md
├── requirements.txt
├── backend/
│   ├── create_db.py
│   └── app/
│       ├── api/
│       ├── models/
│       └── services/
└── frontend/  # Coming soon
```

## Database Schema

### Games Table
- Primary game information
- Includes title, serial number, developer, publisher
- Tracks release dates for different regions
- Includes reference URLs and notes

### Game Status Table
- Tracks ownership status (OWNED/HUNTING/NONE)
- Records when games were added to collection
- Allows for personal notes

### Digital Backups Table
- Tracks digital copy information
- Supports multiple file formats
- Stores checksums and verification dates
- Manages emulator configurations

## Contributing

This is a personal learning project. While suggestions are welcome, I'm not accepting direct contributions at this time as I'm using this project to learn and improve my development skills working with Cursor's AI powered IDE.

## License

This project is for personal use and learning purposes. 