import sqlite3
from datetime import datetime
import json
import os
import zlib

class CollectionManager:
    def __init__(self, db_path='ps1_games.db'):
        self.db_path = db_path

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def get_all_games(self):
        """Get all games from the database"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT g.*, COALESCE(gs.status, 'NONE') as status, gs.notes, gs.date_added
        FROM games g
        LEFT JOIN game_status gs ON g.id = gs.game_id
        ORDER BY g.title
        ''')
        
        results = cursor.fetchall()
        conn.close()
        return results

    def search_games(self, title=None, publisher=None, serial=None):
        """Search games by title, publisher, or serial number"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        query = '''
        SELECT g.*, COALESCE(gs.status, 'NONE') as status, gs.notes, gs.date_added,
               db.file_path, db.file_type, db.last_verified
        FROM games g
        LEFT JOIN game_status gs ON g.id = gs.game_id
        LEFT JOIN digital_backups db ON g.id = db.game_id
        WHERE 1=1
        '''
        params = []
        
        if title:
            query += " AND g.title LIKE ?"
            params.append(f"%{title}%")
        if publisher:
            query += " AND g.publisher LIKE ?"
            params.append(f"%{publisher}%")
        if serial:
            query += " AND g.serial_number LIKE ?"
            params.append(f"%{serial}%")
            
        query += " ORDER BY g.title"
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        conn.close()
        return results

    def update_game_status(self, game_id, status, notes=None):
        """Update the status of a game (OWNED/HUNTING/NONE)"""
        if status not in ['OWNED', 'HUNTING', 'NONE']:
            raise ValueError("Status must be OWNED, HUNTING, or NONE")
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT INTO game_status (game_id, status, notes)
        VALUES (?, ?, ?)
        ON CONFLICT(game_id) DO UPDATE SET 
        status = ?, notes = ?, date_added = CURRENT_TIMESTAMP
        ''', (game_id, status, notes, status, notes))
        
        conn.commit()
        conn.close()

    def add_digital_backup(self, game_id, file_path, emulator_settings=None):
        """Add or update a digital backup for a game"""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Backup file not found: {file_path}")
        
        # Get file information
        file_size = os.path.getsize(file_path)
        file_type = os.path.splitext(file_path)[1].lower()
        
        # Calculate CRC32 for the file
        crc32 = None
        with open(file_path, 'rb') as f:
            crc32 = format(zlib.crc32(f.read()) & 0xFFFFFFFF, '08x')
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT INTO digital_backups 
        (game_id, file_path, file_type, file_size, crc32, last_verified, emulator_config)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(game_id) DO UPDATE SET
        file_path = ?, file_type = ?, file_size = ?, 
        crc32 = ?, last_verified = ?, emulator_config = ?
        ''', (
            game_id, file_path, file_type, file_size, crc32, 
            datetime.now(), json.dumps(emulator_settings) if emulator_settings else None,
            file_path, file_type, file_size, crc32,
            datetime.now(), json.dumps(emulator_settings) if emulator_settings else None
        ))
        
        conn.commit()
        conn.close()

    def get_hunting_list(self):
        """Get list of games marked as HUNTING"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT g.*, gs.status, gs.notes, gs.date_added
        FROM games g
        JOIN game_status gs ON g.id = gs.game_id
        WHERE gs.status = 'HUNTING'
        ORDER BY gs.date_added DESC
        ''')
        
        results = cursor.fetchall()
        conn.close()
        return results

    def get_owned_games(self):
        """Get list of owned games with their backup information"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT g.*, gs.status, gs.notes, gs.date_added,
               db.file_path, db.file_type, db.last_verified
        FROM games g
        JOIN game_status gs ON g.id = gs.game_id
        LEFT JOIN digital_backups db ON g.id = db.game_id
        WHERE gs.status = 'OWNED'
        ORDER BY g.title
        ''')
        
        results = cursor.fetchall()
        conn.close()
        return results

    def verify_backup(self, game_id):
        """Verify the CRC32 of a game's backup file"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT file_path, crc32 FROM digital_backups WHERE game_id = ?', (game_id,))
        result = cursor.fetchone()
        
        if not result:
            conn.close()
            return False
        
        file_path, stored_crc32 = result
        
        if not os.path.exists(file_path):
            return False
        
        with open(file_path, 'rb') as f:
            current_crc32 = format(zlib.crc32(f.read()) & 0xFFFFFFFF, '08x')
            
        is_valid = current_crc32 == stored_crc32
        
        if is_valid:
            cursor.execute('''
            UPDATE digital_backups 
            SET last_verified = ? 
            WHERE game_id = ?
            ''', (datetime.now(), game_id))
            conn.commit()
        
        conn.close()
        return is_valid 