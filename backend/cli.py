#!/usr/bin/env python3
import argparse
import sys
import os
from manage_collection import CollectionManager
from tabulate import tabulate
import json
from colorama import init, Fore, Style
from difflib import SequenceMatcher
import glob

# Initialize colorama for cross-platform color support
init()

def similar(a, b):
    """Calculate string similarity ratio"""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

def create_parser():
    parser = argparse.ArgumentParser(
        description='PS1 Game Collection Manager - Manage your digital PS1 game collection',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Mark a game as owned
  %(prog)s status --game-id 123 --set-status OWNED --notes "Complete backup, tested working"
  
  # Add a game to hunting list
  %(prog)s status --game-id 456 --set-status HUNTING --notes "Looking for US version"
  
  # Add a digital backup
  %(prog)s backup --game-id 123 --file "/path/to/game.chd"
  
  # Search for games
  %(prog)s search "Final Fantasy"
  %(prog)s search --publisher "Square"
  %(prog)s search --serial "SLUS"
  
  # View hunting list
  %(prog)s list --hunting
  
  # View owned games
  %(prog)s list --owned
  
  # Verify backup integrity
  %(prog)s verify --game-id 123
  
  # Scan directory for games
  %(prog)s scan --directory "/path/to/roms" --match-threshold 0.8
''')

    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # Status command
    status_parser = subparsers.add_parser('status', help='Update game status (OWNED/HUNTING/NONE)')
    status_parser.add_argument('--game-id', type=int, required=True, help='Game ID from database')
    status_parser.add_argument('--set-status', choices=['OWNED', 'HUNTING', 'NONE'], required=True,
                              help='Set the game status')
    status_parser.add_argument('--notes', help='Optional notes about the game')

    # Backup command
    backup_parser = subparsers.add_parser('backup', help='Add or update digital backup')
    backup_parser.add_argument('--game-id', type=int, required=True, help='Game ID from database')
    backup_parser.add_argument('--file', required=True, help='Path to the backup file')
    backup_parser.add_argument('--emulator-config', help='JSON string of emulator settings')

    # Search command
    search_parser = subparsers.add_parser('search', help='Search for games')
    search_group = search_parser.add_mutually_exclusive_group(required=True)
    search_group.add_argument('query', nargs='?', help='Search by game title')
    search_group.add_argument('--publisher', help='Search by publisher')
    search_group.add_argument('--serial', help='Search by serial number')

    # List command
    list_parser = subparsers.add_parser('list', help='List games by status')
    list_group = list_parser.add_mutually_exclusive_group(required=True)
    list_group.add_argument('--hunting', action='store_true', help='List games in hunting list')
    list_group.add_argument('--owned', action='store_true', help='List owned games')

    # Verify command
    verify_parser = subparsers.add_parser('verify', help='Verify backup integrity')
    verify_parser.add_argument('--game-id', type=int, required=True, help='Game ID to verify')

    # Scan command
    scan_parser = subparsers.add_parser('scan', help='Scan directory for game backups')
    scan_parser.add_argument('--directory', required=True, help='Directory containing game backups')
    scan_parser.add_argument('--match-threshold', type=float, default=0.8,
                            help='Similarity threshold for name matching (0.0-1.0)')

    return parser

def format_game_list(games, include_backup_info=False):
    if not games:
        return "No games found."

    headers = ['ID', 'Title', 'Serial', 'Publisher', 'Status', 'Notes', 'Added Date']
    if include_backup_info:
        headers.extend(['Backup Path', 'Format', 'Last Verified'])

    rows = []
    for game in games:
        # Color code based on status
        status = game[-3] if len(game) > 8 else 'NONE'  # Adjust index based on your data structure
        if status == 'OWNED':
            title_color = Fore.GREEN
        elif status == 'HUNTING':
            title_color = Fore.RED
        else:
            title_color = Style.RESET_ALL

        row = [
            game[0],  # ID
            f"{title_color}{game[1]}{Style.RESET_ALL}",  # Colored title
            game[2],  # Serial
            game[4],  # Publisher
            status,   # Status
            game[-2],  # Notes
            game[-1].split('.')[0] if game[-1] else 'N/A'  # Date without microseconds
        ]
        if include_backup_info and len(game) > 10:  # Adjust based on your data structure
            row.extend([
                game[-3] or 'No backup',  # Backup path
                game[-2] or 'N/A',        # Format
                game[-1].split('.')[0] if game[-1] else 'Never' # Last verified
            ])
        rows.append(row)

    return tabulate(rows, headers=headers, tablefmt='grid')

def scan_directory(directory, manager, match_threshold):
    """Scan directory for game backups and match with database"""
    supported_extensions = ('.iso', '.bin', '.chd', '.pbp')
    found_games = []
    
    # Get all games from database
    all_games = manager.get_all_games()  # We'll need to add this method to CollectionManager
    
    # Find all files with supported extensions
    for ext in supported_extensions:
        pattern = os.path.join(directory, f"*{ext}")
        for file_path in glob.glob(pattern):
            base_name = os.path.splitext(os.path.basename(file_path))[0]
            
            # Find best match in database
            best_match = None
            best_ratio = 0
            
            for game in all_games:
                ratio = similar(base_name, game[1])  # Compare with game title
                if ratio > best_ratio and ratio >= match_threshold:
                    best_ratio = ratio
                    best_match = game
            
            if best_match:
                found_games.append((best_match, file_path, best_ratio))
    
    return found_games

def main():
    parser = create_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    manager = CollectionManager()

    try:
        if args.command == 'status':
            manager.update_game_status(args.game_id, args.set_status, args.notes)
            print(f"Updated game {args.game_id} status to {args.set_status}")

        elif args.command == 'backup':
            emulator_config = None
            if args.emulator_config:
                try:
                    emulator_config = json.loads(args.emulator_config)
                except json.JSONDecodeError:
                    print("Error: Invalid JSON in emulator config")
                    sys.exit(1)

            manager.add_digital_backup(args.game_id, args.file, emulator_config)
            print(f"Added/updated backup for game {args.game_id}")

        elif args.command == 'search':
            if args.query:
                games = manager.search_games(title=args.query)
            elif args.publisher:
                games = manager.search_games(publisher=args.publisher)
            elif args.serial:
                games = manager.search_games(serial=args.serial)
            
            print("\n=== Search Results ===")
            print(format_game_list(games))

        elif args.command == 'list':
            if args.hunting:
                games = manager.get_hunting_list()
                print(f"\n{Fore.RED}=== Games in Hunting List ==={Style.RESET_ALL}")
                print(format_game_list(games))
            else:  # owned
                games = manager.get_owned_games()
                print(f"\n{Fore.GREEN}=== Owned Games ==={Style.RESET_ALL}")
                print(format_game_list(games, include_backup_info=True))

        elif args.command == 'verify':
            is_valid = manager.verify_backup(args.game_id)
            if is_valid:
                print(f"{Fore.GREEN}Backup for game {args.game_id} is valid!{Style.RESET_ALL}")
            else:
                print(f"{Fore.RED}Backup for game {args.game_id} is invalid or not found!{Style.RESET_ALL}")

        elif args.command == 'scan':
            print(f"\nScanning directory: {args.directory}")
            print("Note: File names should closely match game titles for accurate matching")
            print(f"Matching threshold: {args.match_threshold}")
            
            found_games = scan_directory(args.directory, manager, args.match_threshold)
            
            if not found_games:
                print("\nNo matches found.")
                return
            
            print("\n=== Found Matches ===")
            for game, file_path, ratio in found_games:
                print(f"\n{Fore.CYAN}Match found ({ratio:.2%} confidence):{Style.RESET_ALL}")
                print(f"Game: {game[1]} (ID: {game[0]})")
                print(f"File: {file_path}")
                
                # Prompt for action
                while True:
                    action = input(f"\nAdd this game as OWNED? (y/n/s=skip): ").lower()
                    if action in ('y', 'n', 's'):
                        break
                
                if action == 'y':
                    manager.update_game_status(game[0], 'OWNED', f"Added from scan: {file_path}")
                    manager.add_digital_backup(game[0], file_path)
                    print(f"{Fore.GREEN}Added to collection!{Style.RESET_ALL}")
                elif action == 'n':
                    print("Skipped.")
                else:
                    continue

    except Exception as e:
        print(f"{Fore.RED}Error: {str(e)}{Style.RESET_ALL}")
        sys.exit(1)

if __name__ == '__main__':
    main() 