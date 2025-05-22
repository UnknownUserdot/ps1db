import sqlite3
import os

def create_database():
    """Create the PS1 games database and its tables."""
    
    # Make sure we're in the right directory
    db_path = "ps1_games.db"
    
    # Create a new database connection
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create the games table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS games (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        serial_number TEXT,
        developer TEXT,
        publisher TEXT,
        release_date_jp TEXT,
        release_date_eu TEXT,
        release_date_na TEXT,
        is_launch_title INTEGER DEFAULT 0,  -- SQLite doesn't have boolean, using INTEGER (0/1)
        reference_url TEXT,
        region_jp INTEGER DEFAULT 0,
        region_eu INTEGER DEFAULT 0,
        region_na INTEGER DEFAULT 0,
        notes TEXT
    )
    ''')
    
    # Create the game status table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS game_status (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        game_id INTEGER UNIQUE,
        status TEXT CHECK(status IN ('OWNED', 'HUNTING', 'NONE')) DEFAULT 'NONE',
        date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        notes TEXT,
        FOREIGN KEY (game_id) REFERENCES games(id)
    )
    ''')
    
    # Create the digital backups table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS digital_backups (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        game_id INTEGER UNIQUE,
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
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_title ON games(title)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_serial ON games(serial_number)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_publisher ON games(publisher)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_status_game_id ON game_status(game_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_status_type ON game_status(status)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_backup_game_id ON digital_backups(game_id)')
    
    # Add some sample data for testing
    cursor.execute('''
    INSERT OR IGNORE INTO games (title, serial_number, publisher, developer, region_na)
    VALUES 
    ('Final Fantasy VII', 'SCUS-94163', 'Sony Computer Entertainment', 'Square', 1),
    ('Crash Bandicoot', 'SCUS-94900', 'Sony Computer Entertainment', 'Naughty Dog', 1),
    ('Metal Gear Solid', 'SLUS-00594', 'Konami', 'Konami Computer Entertainment Japan', 1)
    ''')
    
    # Commit the changes and close the connection
    conn.commit()
    conn.close()
    
    print(f"Database created successfully at: {os.path.abspath(db_path)}")

if __name__ == "__main__":
    create_database() 