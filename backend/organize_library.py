import sqlite3
from pathlib import Path
from typing import Dict, List, NamedTuple
from dataclasses import dataclass
from datetime import datetime

@dataclass
class GameInfo:
    id: int
    title: str
    file_path: str
    file_size: int
    is_multi_disc: bool = False
    disc_number: int = 1
    total_discs: int = 1
    release_date: str = None

class RegionLibrary:
    def __init__(self, db_path: str = 'ps1_games.db'):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
    
    def _extract_disc_info(self, file_path: str) -> tuple:
        """Extract disc number and total discs from filename."""
        filename = Path(file_path).name.lower()
        disc_num = 1
        total_discs = 1
        
        # Common disc number patterns
        disc_patterns = [
            r'disc\s*(\d+)(?:\s*of\s*(\d+))?',
            r'disk\s*(\d+)(?:\s*of\s*(\d+))?',
            r'cd\s*(\d+)(?:\s*of\s*(\d+))?'
        ]
        
        import re
        for pattern in disc_patterns:
            match = re.search(pattern, filename)
            if match:
                disc_num = int(match.group(1))
                if match.group(2):
                    total_discs = int(match.group(2))
                break
        
        return disc_num, total_discs
    
    def _format_file_size(self, size_bytes: int) -> str:
        """Convert file size to human readable format."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} TB"
    
    def get_library_by_region(self) -> Dict[str, List[GameInfo]]:
        """Get user's library organized by region."""
        library = {
            'NTSC-U': [],  # North America
            'PAL': [],     # Europe
            'NTSC-J': [],  # Japan
            'Unknown': []   # Region not determined
        }
        
        # Get all games in user's library with region information
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT 
                g.id, g.title, g.region_na, g.region_eu, g.region_jp,
                g.release_date_na, g.release_date_eu, g.release_date_jp,
                u.file_path, u.file_size
            FROM usr_lib u
            JOIN games g ON u.game_id = g.id
            ORDER BY g.title
        ''')
        
        # Process each game
        current_game = None
        for row in cursor:
            disc_num, total_discs = self._extract_disc_info(row['file_path'])
            
            game = GameInfo(
                id=row['id'],
                title=row['title'],
                file_path=row['file_path'],
                file_size=row['file_size'],
                disc_number=disc_num,
                total_discs=total_discs
            )
            
            # Determine region(s)
            if row['region_na']:
                game.release_date = row['release_date_na']
                library['NTSC-U'].append(game)
            if row['region_eu']:
                game.release_date = row['release_date_eu']
                library['PAL'].append(game)
            if row['region_jp']:
                game.release_date = row['release_date_jp']
                library['NTSC-J'].append(game)
            if not any([row['region_na'], row['region_eu'], row['region_jp']]):
                library['Unknown'].append(game)
        
        return library
    
    def display_library(self):
        """Display the organized library."""
        library = self.get_library_by_region()
        
        print("\n=== PS1 Game Library by Region ===\n")
        
        for region, games in library.items():
            if not games:
                continue
                
            print(f"\n{region} Games:")
            print("=" * 60)
            
            # Group multi-disc games
            game_groups = {}
            for game in games:
                key = (game.id, game.title)
                if key not in game_groups:
                    game_groups[key] = []
                game_groups[key].append(game)
            
            # Display games
            for (game_id, title), game_list in sorted(game_groups.items(), key=lambda x: x[0][1].lower()):
                is_multi_disc = len(game_list) > 1
                
                # Display game title and release date
                release_date = game_list[0].release_date
                date_str = f" ({release_date})" if release_date else ""
                print(f"\n{title}{date_str}")
                
                # Display each disc/version
                for game in game_list:
                    disc_info = f"Disc {game.disc_number} of {game.total_discs}" if is_multi_disc else ""
                    size_str = self._format_file_size(game.file_size)
                    file_name = Path(game.file_path).name
                    print(f"  • {file_name} {disc_info} [{size_str}]")
        
        print("\n" + "=" * 60)
        
        # Print summary
        total_games = sum(len(set((g.id, g.title) for g in games)) for games in library.values())
        total_files = sum(len(games) for games in library.values())
        print(f"\nTotal Unique Games: {total_games}")
        print(f"Total Files: {total_files}")

def main():
    organizer = RegionLibrary()
    organizer.display_library()

if __name__ == "__main__":
    main() 