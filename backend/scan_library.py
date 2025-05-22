import os
import sqlite3
from datetime import datetime
import subprocess
import re
from pathlib import Path
from difflib import SequenceMatcher
import signal
from contextlib import contextmanager
import time

class TimeoutException(Exception):
    pass

@contextmanager
def timeout(seconds):
    def timeout_handler(signum, frame):
        raise TimeoutException("Operation timed out")
    
    # Register the signal function handler
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(seconds)
    
    try:
        yield
    finally:
        # Disable the alarm
        signal.alarm(0)

class PS1GameScanner:
    def __init__(self, db_path='ps1_games.db'):
        self.db_path = db_path
        self.supported_extensions = {'.iso', '.bin', '.cue'}
        self.region_patterns = {
            'USA': r'\(USA\)|\(US\)|\(NTSC-U\)',
            'Europe': r'\(Europe\)|\(EU\)|\(PAL\)|\(E\)',
            'Japan': r'\(Japan\)|\(JP\)|\(NTSC-J\)|\(J\)'
        }
        self.disc_patterns = {
            'number': r'(?:disc|disk)\s*(\d+)',
            'total': r'(?:of|\/)\s*(\d+)',
            'cd': r'cd\s*(\d+)'
        }
        
    def connect_db(self):
        """Create a database connection."""
        return sqlite3.connect(self.db_path)
    
    def extract_disc_info(self, filename):
        """Extract disc number and total discs from filename."""
        filename = filename.lower()
        disc_info = {'number': 1, 'total': 1}
        
        # Try different disc number patterns
        for pattern_type, pattern in self.disc_patterns.items():
            if pattern_type == 'number':
                match = re.search(pattern, filename, re.IGNORECASE)
                if match:
                    disc_info['number'] = int(match.group(1))
            elif pattern_type == 'total':
                match = re.search(pattern, filename, re.IGNORECASE)
                if match:
                    disc_info['total'] = int(match.group(1))
            elif pattern_type == 'cd':
                match = re.search(pattern, filename, re.IGNORECASE)
                if match:
                    disc_info['number'] = int(match.group(1))
        
        return disc_info
    
    def extract_iso_title(self, file_path):
        """Extract the actual game title from ISO file."""
        try:
            with open(file_path, 'rb') as f:
                # Try multiple known locations for PS1 game titles
                
                # 1. Try the system.cnf file in the first few sectors
                f.seek(0)
                system_area = f.read(32 * 2048)  # Read first 32 sectors
                
                # Look for system.cnf content
                sys_cnf_match = re.search(br'BOOT\s*=\s*cdrom:\\?([^;\\]+)', system_area)
                if sys_cnf_match:
                    boot_file = sys_cnf_match.group(1).decode('ascii', errors='ignore').strip()
                    # Convert boot filename to title (e.g., SLUS_005.27;1 -> proper name)
                    clean_boot = re.sub(r'[\d.;_\\]', ' ', boot_file).strip()
                    if len(clean_boot) > 4:
                        return clean_boot
                
                # 2. Try the Volume Descriptor (sector 16)
                f.seek(16 * 2048)
                vd_data = f.read(2048)
                
                # Check if it's a valid ISO9660 descriptor
                if vd_data[1:6] == b'CD001':
                    # Try volume name (both standard and Joliet)
                    volume_name = vd_data[40:72].decode('ascii', errors='ignore').strip()
                    volume_name = re.sub(r'[;_\s]+$', '', volume_name)
                    
                    if len(volume_name) > 4 and not volume_name.startswith('PLAYSTATION'):
                        return volume_name
                
                # 3. Try the license data area
                f.seek(4 * 2048)  # License data typically starts at sector 4
                license_data = f.read(2048)
                license_text = license_data.decode('ascii', errors='ignore')
                
                # Look for common patterns in license text
                title_match = re.search(r'(?:TITLE|GAME)[:\s]+([A-Za-z0-9\s\-]+)', license_text)
                if title_match:
                    title = title_match.group(1).strip()
                    if len(title) > 4:
                        return title
                
                # 4. Try searching for the serial in the first 32KB and use it for title lookup
                f.seek(0)
                header_data = f.read(32 * 1024)
                serial_match = re.search(br'([A-Z]{4}-\d{5})', header_data)
                if serial_match:
                    serial = serial_match.group(1).decode('ascii')
                    # Note: We'll handle the serial->title lookup in the match_game_title method
                    return f"SERIAL:{serial}"
                
                return None
        except Exception as e:
            print(f"Error reading ISO title: {e}")
            return None
    
    def extract_serial_from_iso(self, file_path):
        """Extract serial number from ISO file using optimized approach."""
        try:
            # Only read the first 256KB of the ISO where serial numbers are typically located
            with open(file_path, 'rb') as f:
                # Read in 64KB chunks
                chunk_size = 64 * 1024
                data = b''
                for _ in range(4):  # 4 chunks = 256KB
                    data += f.read(chunk_size)
                
                # Convert to string, ignoring non-ASCII characters
                text = data.decode('ascii', errors='ignore')
                
                # Look for PS1 serial number patterns
                serial_matches = re.findall(r'(S[CLK][A-Z][A-Z]-\d{5})', text)
                if serial_matches:
                    return serial_matches[0]
                
                return None
        except Exception as e:
            print(f"Error reading ISO serial: {e}")
            return None
    
    def get_iso_metadata(self, file_path):
        """Extract metadata from ISO file using 'file' command and optimized serial extraction."""
        metadata = {}
        
        try:
            # Basic file info with timeout
            with timeout(5):  # 5 second timeout for file command
                result = subprocess.run(['file', file_path], capture_output=True, text=True)
                metadata['file_info'] = result.stdout
            
            # Extract serial number
            serial = self.extract_serial_from_iso(file_path)
            if serial:
                metadata['serial_number'] = serial
            
            # Extract actual game title from ISO
            iso_title = self.extract_iso_title(file_path)
            if iso_title:
                metadata['iso_title'] = iso_title
                print(f"Found title in ISO: {iso_title}")
            
            # Extract disc information from filename
            disc_info = self.extract_disc_info(os.path.basename(file_path))
            metadata.update(disc_info)
            
            return metadata
        except TimeoutException:
            print(f"Warning: Metadata extraction timed out for {os.path.basename(file_path)}")
            return metadata
        except Exception as e:
            print(f"Error reading ISO metadata: {e}")
            return metadata
    
    def normalize_title(self, title):
        """Normalize game title for better matching."""
        # Remove disc/volume indicators first
        title = re.sub(r'\s*(?:disc|disk|cd)\s*\d+(?:\s*(?:of|\/)\s*\d+)?', '', title, flags=re.IGNORECASE)
        title = re.sub(r'\s*(?:arcade|simulation)\s*mode', '', title, flags=re.IGNORECASE)  # Remove GT2 mode indicators
        
        # Remove region indicators
        for pattern in self.region_patterns.values():
            title = re.sub(pattern, '', title, flags=re.IGNORECASE)
        
        # Remove common patterns and special characters
        title = re.sub(r'\(.*?\)|\[.*?\]', '', title)  # Remove parentheses/brackets and contents
        title = re.sub(r'[\._]', ' ', title)  # Convert dots and underscores to spaces
        title = re.sub(r'[^\w\s\-:!]', '', title)  # Keep only word chars, spaces, hyphens, colons, and exclamation marks
        
        # Common filename patterns to proper titles
        title_patterns = {
            # Abbreviations
            r'^MGS\b': 'Metal Gear Solid',
            r'^GT\b': 'Gran Turismo',
            r'^FF\b': 'Final Fantasy',
            r'^RE\b': 'Resident Evil',
            r'^PE\b': 'Parasite Eve',
            r'^HOD\b': 'House of the Dead',
            r'^CC\b': 'Chrono Cross',
            
            # Specific game patterns
            r'Gran[\s_]?Turismo[\s_]?2': 'Gran Turismo 2',
            r'Metal Gear(?!\s+Solid)': 'Metal Gear Solid',
            r'Spyro(?:\s+)?(?:rr|Ripto|2.+Rage)': 'Spyro 2: Ripto\'s Rage!',
            r'Crash(?:\s+)?(\d)': r'Crash Bandicoot \1',
            r'Crash(?:\s+)?(?:Bandicoot\s+)?(?:3|III|Warped)': 'Crash Bandicoot: Warped',
            r'Ape(?:\s+)?Ex(?:c)?ape': 'Ape Escape',
            r'Parasite[\s_]?EVE[\s_]?(?:2|II)': 'Parasite Eve II',
            r'House[\s_]?of[\s_]?(?:the[\s_])?Dead[\s_]?(\d)': r'House of the Dead \1',
            
            # Shin Megami Tensei variations
            r'Shin[\s_]?Megami[\s_]?Te?i?nse?i?[\s_]?(?:Devil[\s_]?Summoner[\s_]?)?Soul[\s_]?Hackers': 
                'Shin Megami Tensei: Devil Summoner: Soul Hackers',
            r'Shin[\s_]?Megami[\s_]?Te?i?nse?i?(?!:)': 'Shin Megami Tensei',
        }
        
        # Apply title patterns
        title = title.strip()
        for pattern, replacement in title_patterns.items():
            title = re.sub(pattern, replacement, title, flags=re.IGNORECASE)
        
        # Handle numbered sequels
        title = re.sub(r'(\w+)\s*(\d+)', r'\1 \2', title)  # Add space between title and number
        
        # Convert multiple spaces to single space
        title = re.sub(r'\s+', ' ', title).strip()
        
        return title
    
    def calculate_title_similarity(self, title1, title2):
        """Calculate similarity ratio between two titles."""
        # Normalize both titles
        norm1 = self.normalize_title(title1.lower())
        norm2 = self.normalize_title(title2.lower())
        
        # Try exact match first (case insensitive)
        if norm1 == norm2:
            return 1.0
        
        # Split titles by common separators
        split_pattern = r'[:\u2022]'  # Matches : and • characters
        parts1 = set(p.strip() for p in re.split(split_pattern, norm1) if p.strip())
        parts2 = set(p.strip() for p in re.split(split_pattern, norm2) if p.strip())
        
        # If any part matches exactly
        if parts1.intersection(parts2):
            return 0.9
            
        # Check if one title is a complete word subset of the other
        words1 = set(norm1.split())
        words2 = set(norm2.split())
        if words1.issubset(words2) or words2.issubset(words1):
            # Calculate what percentage of words match
            match_ratio = len(words1.intersection(words2)) / max(len(words1), len(words2))
            if match_ratio > 0.8:  # If more than 80% of words match
                return 0.9
        
        # Handle numbered sequels
        base1 = re.sub(r'\s*\d+$', '', norm1)
        base2 = re.sub(r'\s*\d+$', '', norm2)
        if base1 == base2:
            return 0.95
        
        # Use SequenceMatcher for other cases
        ratio = SequenceMatcher(None, norm1, norm2).ratio()
        
        # Penalize very short matches to avoid matching abbreviations
        if len(min(norm1, norm2)) <= 2:  # If either title is 2 chars or less
            ratio *= 0.5  # Reduce the similarity score
        
        return ratio
    
    def match_game_title(self, cursor, title, metadata=None):
        """Enhanced game title matching with multiple strategies."""
        # Normalize the input title
        clean_title = self.normalize_title(title)
        
        # Try exact match first
        cursor.execute('SELECT id, title FROM games WHERE LOWER(title) = LOWER(?)', (clean_title,))
        result = cursor.fetchone()
        if result:
            return result
        
        # Try fuzzy matching
        cursor.execute('SELECT id, title FROM games')
        all_games = cursor.fetchall()
        best_match = None
        best_ratio = 0
        
        for game_id, db_title in all_games:
            ratio = self.calculate_title_similarity(clean_title, db_title)
            if ratio > best_ratio:
                # Additional check for very short titles to avoid false matches
                if len(db_title) <= 2 and ratio < 0.95:  # Require very high confidence for short titles
                    continue
                best_ratio = ratio
                best_match = (game_id, db_title)
                if ratio == 1.0:  # Perfect match found
                    break
        
        # Return match only if similarity is high enough
        if best_ratio >= 0.8:  # 80% similarity threshold
            return best_match
        
        return None
    
    def get_cue_metadata(self, file_path):
        """Extract metadata from CUE file with enhanced parsing."""
        metadata = {}
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                # Look for TITLE information
                title_match = re.search(r'TITLE\s+"([^"]+)"', content)
                if title_match:
                    metadata['title'] = title_match.group(1)
                
                # Look for PERFORMER (publisher) information
                performer_match = re.search(r'PERFORMER\s+"([^"]+)"', content)
                if performer_match:
                    metadata['publisher'] = performer_match.group(1)
                
                return metadata
        except Exception as e:
            print(f"Error reading CUE metadata: {e}")
            return None
    
    def scan_directory(self, directory_path):
        """Scan a directory for PS1 games and update the user library."""
        conn = self.connect_db()
        cursor = conn.cursor()
        current_time = datetime.now().isoformat()
        
        # Get list of existing files in usr_lib
        cursor.execute('SELECT file_path FROM usr_lib')
        existing_files = {row[0] for row in cursor.fetchall()}
        
        # Track current files for cleanup
        current_files = set()
        
        # Statistics for reporting
        stats = {
            'total_processed': 0,
            'matched': 0,
            'unmatched': 0,
            'updated': 0,
            'serials_found': 0
        }
        
        # Walk through the directory
        for root, _, files in os.walk(directory_path):
            for filename in files:
                file_path = os.path.join(root, filename)
                ext = os.path.splitext(filename)[1].lower()
                
                if ext not in self.supported_extensions:
                    continue
                
                abs_path = os.path.abspath(file_path)
                current_files.add(abs_path)
                stats['total_processed'] += 1
                
                print(f"\nProcessing: {filename}")
                
                # Get metadata based on file type
                metadata = None
                if ext == '.iso':
                    metadata = self.get_iso_metadata(file_path)
                elif ext == '.cue':
                    metadata = self.get_cue_metadata(file_path)
                
                # Try to match with database
                match = self.match_game_title(cursor, os.path.splitext(filename)[0], metadata)
                
                if match:
                    game_id, game_title = match
                    print(f"Matched: {game_title}")
                    stats['matched'] += 1
                    
                    # Try to update serial number if available
                    if metadata and isinstance(metadata, dict) and metadata.get('serial_number'):
                        try:
                            cursor.execute('UPDATE games SET serial_number = ? WHERE id = ?',
                                         (metadata['serial_number'], game_id))
                            stats['serials_found'] += 1
                        except sqlite3.OperationalError:
                            # If serial_number column doesn't exist, skip the update
                            pass
                    
                    # Add or update usr_lib entry
                    if abs_path in existing_files:
                        cursor.execute('''
                            UPDATE usr_lib 
                            SET file_type = ?, file_size = ?, last_scanned = ?
                            WHERE file_path = ?
                        ''', (ext[1:], os.path.getsize(file_path), current_time, abs_path))
                        stats['updated'] += 1
                    else:
                        cursor.execute('''
                            INSERT INTO usr_lib (game_id, file_path, file_type, file_size, last_scanned)
                            VALUES (?, ?, ?, ?, ?)
                        ''', (game_id, abs_path, ext[1:], os.path.getsize(file_path), current_time))
                else:
                    print(f"No match found for: {filename}")
                    stats['unmatched'] += 1
        
        # Remove entries for files that no longer exist
        cursor.execute('DELETE FROM usr_lib WHERE file_path NOT IN (%s)' % 
                      ','.join('?' * len(current_files)), list(current_files))
        
        conn.commit()
        
        # Print detailed summary
        print("\nScan Summary:")
        print(f"Total files processed: {stats['total_processed']}")
        print(f"Successfully matched: {stats['matched']}")
        print(f"Unmatched files: {stats['unmatched']}")
        print(f"Updated entries: {stats['updated']}")
        print(f"Serial numbers found: {stats['serials_found']}")
        
        cursor.execute('SELECT COUNT(*) FROM usr_lib')
        total_games = cursor.fetchone()[0]
        print(f"Total games in library: {total_games}")
        
        conn.close()

def main():
    scanner = PS1GameScanner()
    
    # Create usr_lib table if it doesn't exist
    from create_usr_lib import create_user_library_table
    create_user_library_table()
    
    # Get directory path from user
    print("\nPlease enter the directory path containing your PS1 games:")
    directory = input().strip()
    
    if os.path.isdir(directory):
        print(f"\nScanning directory: {directory}")
        scanner.scan_directory(directory)
    else:
        print("Invalid directory path!")

if __name__ == "__main__":
    main() 