import sqlite3
from datetime import datetime

def create_user_library_tables():
    """Create the user's library tables for tracking game ownership and backups."""
    conn = sqlite3.connect('ps1_games.db')
    cursor = conn.cursor()
    
    # Create user game status table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS game_status (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        game_id INTEGER,
        status TEXT CHECK(status IN ('OWNED', 'HUNTING', 'NONE')) DEFAULT 'NONE',
        date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        notes TEXT,
        FOREIGN KEY (game_id) REFERENCES games(id)
    )
    ''')
    
    # Create digital backups table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS digital_backups (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        game_id INTEGER,
        file_path TEXT,
        file_type TEXT CHECK(file_type IN ('.iso', '.bin', '.pbp', '.chd')),
        file_size INTEGER,
        crc32 TEXT,
        last_verified TIMESTAMP,
        emulator_config TEXT,  -- Store emulator-specific settings as JSON
        FOREIGN KEY (game_id) REFERENCES games(id)
    )
    ''')
    
    # Create indexes for faster lookups
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_status_game_id ON game_status(game_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_status_type ON game_status(status)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_backup_game_id ON digital_backups(game_id)')
    
    conn.commit()
    conn.close()
    print("User library tables created successfully!")

if __name__ == "__main__":
    create_user_library_tables() 