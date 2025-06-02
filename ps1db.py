#!/usr/bin/env python3
import click
from tabulate import tabulate
from sqlalchemy import create_engine, or_, func, Column, Integer, String, Boolean
from sqlalchemy.orm import sessionmaker, declarative_base
import os
import sys
from datetime import datetime
import glob

# Database setup
def get_user_data_dir():
    """Get the user-specific data directory"""
    if os.name == 'nt':  # Windows
        base_dir = os.path.expandvars('%LOCALAPPDATA%')
    else:  # macOS and Linux
        base_dir = os.path.expanduser('~/.local/share')
    
    app_dir = os.path.join(base_dir, 'ps1db')
    os.makedirs(app_dir, exist_ok=True)
    return app_dir

# Use separate files for game data and user collection
POSSIBLE_DB_LOCATIONS = [
    os.path.join(os.path.dirname(__file__), "ps1_games.db"),  # Local development
    os.path.join(os.path.dirname(__file__), "data", "ps1_games.db"),  # Package data
    "/usr/local/lib/ps1db/data/ps1_games.db",  # System-wide installation
    os.path.join(os.getcwd(), "ps1_games.db")  # Current directory
]

# Find the game database
GAME_DB_PATH = None
for path in POSSIBLE_DB_LOCATIONS:
    if os.path.exists(path):
        GAME_DB_PATH = path
        break

if not GAME_DB_PATH:
    click.echo("Error: Could not find game database. Checked locations:", err=True)
    for path in POSSIBLE_DB_LOCATIONS:
        click.echo(f"  - {path}", err=True)
    sys.exit(1)

USER_DB_PATH = os.path.join(get_user_data_dir(), "user_collection.db")

# Create database engines
game_engine = create_engine(f"sqlite:///{GAME_DB_PATH}")
user_engine = create_engine(f"sqlite:///{USER_DB_PATH}")
GameSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=game_engine)
UserSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=user_engine)
Base = declarative_base()

class Game(Base):
    __tablename__ = "games"

    id = Column(Integer, primary_key=True)
    title = Column(String, index=True)
    serial_number = Column(String, index=True)
    developer = Column(String)
    publisher = Column(String)
    release_date_jp = Column(String)
    release_date_eu = Column(String)
    release_date_na = Column(String)
    is_launch_title = Column(Integer)  # Changed from Boolean to Integer to match SQLite
    reference_url = Column(String)
    region_jp = Column(Integer)  # Changed from Boolean to Integer to match SQLite
    region_eu = Column(Integer)  # Changed from Boolean to Integer to match SQLite
    region_na = Column(Integer)  # Changed from Boolean to Integer to match SQLite
    notes = Column(String)

    def __repr__(self):
        regions = []
        if self.region_jp:
            regions.append("JP")
        if self.region_eu:
            regions.append("EU")
        if self.region_na:
            regions.append("NA")
        return f"<Game {self.title} ({', '.join(regions)})>"

    @property
    def region(self):
        """Helper property to get regions as a string"""
        regions = []
        if self.region_jp:
            regions.append("JP")
        if self.region_eu:
            regions.append("EU")
        if self.region_na:
            regions.append("NA")
        return ", ".join(regions)

class UserGame(Base):
    """Model for tracking user's local game collection"""
    __tablename__ = "user_games"

    id = Column(Integer, primary_key=True)
    game_id = Column(Integer)  # References games.id
    title = Column(String)
    serial_number = Column(String)
    has_jp_version = Column(Boolean, default=False)
    has_eu_version = Column(Boolean, default=False)
    has_na_version = Column(Boolean, default=False)
    jp_path = Column(String, nullable=True)
    eu_path = Column(String, nullable=True)
    na_path = Column(String, nullable=True)

def init_db():
    """Create tables if they don't exist"""
    Base.metadata.create_all(bind=user_engine)

@click.group()
def main():
    """PlayStation 1 Game Database Tool"""
    init_db()
    pass

@main.command()
@click.argument('search_term', required=False)
@click.option('--region', '-r', help='Filter by region (NA/EU/JP)')
@click.option('--local', '-l', is_flag=True, help='Show only games in your local collection')
def search(search_term=None, region=None, local=False):
    """Search for PS1 games in the database"""
    if not search_term:
        click.echo("\nTip: Try searching with part of the name (e.g., 'crash' instead of 'Crash Bandicoot')")
        click.echo("     This often helps find games that might have different regional titles.\n")
    
    game_db = GameSessionLocal()
    user_db = UserSessionLocal()
    try:
        query = game_db.query(Game)
        
        if search_term:
            search_filter = or_(
                Game.title.ilike(f"%{search_term}%"),
                Game.developer.ilike(f"%{search_term}%"),
                Game.publisher.ilike(f"%{search_term}%"),
                Game.serial_number.ilike(f"%{search_term}%")
            )
            query = query.filter(search_filter)
        
        if region:
            if region.upper() == 'JP':
                query = query.filter(Game.region_jp == 1)
            elif region.upper() == 'EU':
                query = query.filter(Game.region_eu == 1)
            elif region.upper() == 'NA':
                query = query.filter(Game.region_na == 1)
            
        games = query.all()
        
        if not games:
            click.echo("No games found matching your criteria.")
            click.echo("\nTip: Try using a shorter, unique part of the title")
            click.echo("     For example: 'metal' instead of 'Metal Gear Solid'")
            return

        # Get local collection info
        local_games = {g.game_id: g for g in user_db.query(UserGame).all()}
        
        # Prepare table data
        table_data = []
        for g in games:
            user_game = local_games.get(g.id)
            regions = []
            if g.region_jp:
                regions.append(f"JP {'✓' if user_game and user_game.has_jp_version else '✗'}")
            if g.region_eu:
                regions.append(f"EU {'✓' if user_game and user_game.has_eu_version else '✗'}")
            if g.region_na:
                regions.append(f"NA {'✓' if user_game and user_game.has_na_version else '✗'}")
            
            table_data.append([
                g.title,
                g.serial_number,
                g.developer,
                g.publisher,
                ' | '.join(regions)
            ])
        
        # Print results in a nice table
        click.echo(tabulate(
            table_data,
            headers=['Title', 'Serial', 'Developer', 'Publisher', 'Regions'],
            tablefmt='grid'
        ))
        
        click.echo(f"\nFound {len(games)} games")
        
    finally:
        game_db.close()
        user_db.close()

@main.command()
def stats():
    """Show statistics about your PS1 collection"""
    game_db = GameSessionLocal()
    user_db = UserSessionLocal()
    try:
        total_games = game_db.query(Game).count()
        total_local = user_db.query(UserGame).count()
        
        jp_games = game_db.query(Game).filter(Game.region_jp == 1).count()
        eu_games = game_db.query(Game).filter(Game.region_eu == 1).count()
        na_games = game_db.query(Game).filter(Game.region_na == 1).count()
        
        # Get local collection stats
        local_game_ids = {g.game_id for g in user_db.query(UserGame).all()}
        jp_owned = game_db.query(Game).filter(Game.id.in_(local_game_ids), Game.region_jp == 1).count()
        eu_owned = game_db.query(Game).filter(Game.id.in_(local_game_ids), Game.region_eu == 1).count()
        na_owned = game_db.query(Game).filter(Game.id.in_(local_game_ids), Game.region_na == 1).count()
        
        click.echo(f"\nTotal Games in Database: {total_games}")
        click.echo(f"Games in Your Collection: {total_local}")
        click.echo("\nGames by Region:")
        click.echo(f"Japan: {jp_games} (You have: {jp_owned})")
        click.echo(f"Europe: {eu_games} (You have: {eu_owned})")
        click.echo(f"North America: {na_games} (You have: {na_owned})")
            
    finally:
        game_db.close()
        user_db.close()

def manual_match(game_db, user_db, unmatched_files):
    """Interactive function to manually match unmatched games"""
    if not unmatched_files:
        return
    
    click.echo("\nUnmatched games found. Would you like to manually match them? [y/N]")
    if not click.confirm(''):
        return
    
    click.echo("\nTip: When searching, try using part of the name (e.g., 'crash' instead of 'Crash Bandicoot')")
    click.echo("     This often helps find games that might have different regional titles.\n")
    
    for file_path in unmatched_files:
        filename = os.path.splitext(os.path.basename(file_path))[0]
        click.echo(f"\nTrying to match: {filename}")
        
        while True:
            # Get game title from user
            title = click.prompt("Enter the correct game title (or 'skip' to move to next)", type=str)
            
            if title.lower() == 'skip':
                break
            
            # Search for matches
            matches = game_db.query(Game).filter(
                or_(
                    Game.title.ilike(f"%{title}%"),
                    Game.title.ilike(f"{title}%"),
                    Game.title.ilike(f"%{title}")
                )
            ).all()
            
            if not matches:
                click.echo("No matches found. Try a different title.")
                click.echo("Tip: Try using a shorter, unique part of the title (e.g., 'spyro' instead of 'Spyro the Dragon')")
                continue
            
            # Show matches
            click.echo("\nPotential matches:")
            for idx, game in enumerate(matches, 1):
                regions = []
                if game.region_jp: regions.append("JP")
                if game.region_eu: regions.append("EU")
                if game.region_na: regions.append("NA")
                click.echo(f"{idx}. {game.title} ({', '.join(regions)})")
            click.echo("0. None of these - try again")
            
            # Get user choice
            choice = click.prompt("Select the correct game (0 to try again)", type=int, default=0)
            
            if choice == 0:
                continue
            
            if 1 <= choice <= len(matches):
                game = matches[choice - 1]
                
                # Get region from user
                click.echo("\nAvailable regions for this game:")
                available_regions = []
                if game.region_jp: available_regions.append("JP")
                if game.region_eu: available_regions.append("EU")
                if game.region_na: available_regions.append("NA")
                click.echo(f"Regions: {', '.join(available_regions)}")
                
                region = click.prompt(
                    "Enter the region code for your version (JP/EU/NA)",
                    type=click.Choice(['JP', 'EU', 'NA'], case_sensitive=False)
                ).upper()
                
                # Verify region is valid for this game
                if (region == 'JP' and not game.region_jp) or \
                   (region == 'EU' and not game.region_eu) or \
                   (region == 'NA' and not game.region_na):
                    click.echo(f"Error: This game is not available in {region} region.")
                    continue
                
                # Update or create user game entry
                user_game = user_db.query(UserGame).filter_by(game_id=game.id).first()
                if not user_game:
                    user_game = UserGame(
                        game_id=game.id,
                        title=game.title,
                        serial_number=game.serial_number,
                        has_jp_version=False,
                        has_eu_version=False,
                        has_na_version=False
                    )
                    user_db.add(user_game)
                
                # Update region-specific flags and paths
                if region == 'JP':
                    user_game.has_jp_version = True
                    user_game.jp_path = file_path
                elif region == 'EU':
                    user_game.has_eu_version = True
                    user_game.eu_path = file_path
                else:  # NA
                    user_game.has_na_version = True
                    user_game.na_path = file_path
                
                user_db.commit()
                click.echo(f"Successfully matched: {game.title} ({region})")
                break

@main.command()
@click.argument('directory', type=click.Path(exists=True))
def scan(directory):
    """Scan a directory for PS1 games and update your collection"""
    game_db = GameSessionLocal()
    user_db = UserSessionLocal()
    try:
        # Look for .bin, .iso, and .img files
        patterns = ['*.bin', '*.iso', '*.img']
        found_files = []
        for pattern in patterns:
            found_files.extend(glob.glob(os.path.join(directory, '**', pattern), recursive=True))
        
        if not found_files:
            click.echo("No PS1 game files found in the specified directory.")
            return
        
        unmatched_files = []
            
        # Update database with found files
        for file_path in found_files:
            # Get game name from filename
            filename = os.path.splitext(os.path.basename(file_path))[0]
            
            # Check for region indicators in filename
            is_jp = any(jp in filename.upper() for jp in ['JPN', 'JAP', '(J)'])
            is_pal = any(pal in filename.upper() for pal in ['PAL', 'EUR', '(E)'])
            is_na = any(na in filename.upper() for na in ['USA', 'NA', '(U)']) or (not is_jp and not is_pal)
            
            # Remove common region indicators and disc numbers for better matching
            clean_name = filename.upper()
            for indicator in ['JPN', 'JAP', 'PAL', 'EUR', 'USA', 'NA', '(J)', '(E)', '(U)',
                            'DISC 1', 'DISC 2', 'DISK 1', 'DISK 2', 'DISC1', 'DISC2',
                            '(DISC 1)', '(DISC 2)', '(DISK 1)', '(DISK 2)',
                            '(PAL)', '(USA)', '(JPN)', '(JAP)',
                            '(ARCADE MODE)', '(SIMULATION MODE)']:
                clean_name = clean_name.replace(indicator, '').strip()
            
            # Handle special characters and normalize spaces
            clean_name = clean_name.replace(":", "").replace("_", " ")
            clean_name = " ".join(clean_name.split())  # Normalize multiple spaces to single space
            clean_name = clean_name.strip()
            
            # Try exact match first
            exact_matches = game_db.query(Game).filter(func.lower(Game.title) == clean_name.lower())
            
            if exact_matches.count() > 0:
                games = exact_matches.all()
            else:
                # Fall back to partial match
                games = game_db.query(Game).filter(Game.title.ilike(f"%{clean_name}%")).all()
            
            if games:
                if len(games) == 1:
                    # Exact match found
                    game = games[0]
                    # Update or create user game entry
                    user_game = user_db.query(UserGame).filter_by(game_id=game.id).first()
                    if not user_game:
                        user_game = UserGame(
                            game_id=game.id,
                            title=game.title,
                            serial_number=game.serial_number,
                            has_jp_version=False,
                            has_eu_version=False,
                            has_na_version=False
                        )
                        user_db.add(user_game)
                    
                    # Update region-specific paths and flags
                    if is_jp and game.region_jp:
                        user_game.has_jp_version = True
                        user_game.jp_path = file_path
                    elif is_pal and game.region_eu:
                        user_game.has_eu_version = True
                        user_game.eu_path = file_path
                    elif is_na and game.region_na:
                        user_game.has_na_version = True
                        user_game.na_path = file_path
                    
                    regions = []
                    if game.region_jp: regions.append(f"JP {'✓' if user_game.has_jp_version else '✗'}")
                    if game.region_eu: regions.append(f"EU {'✓' if user_game.has_eu_version else '✗'}")
                    if game.region_na: regions.append(f"NA {'✓' if user_game.has_na_version else '✗'}")
                    click.echo(f"Updated: {game.title} ({', '.join(regions)})")
                else:
                    # Multiple matches found - add to unmatched for manual processing
                    unmatched_files.append(file_path)
                    click.echo(f"Multiple matches found for: {filename} (will prompt for manual matching)")
            else:
                unmatched_files.append(file_path)
                click.echo(f"No match found for: {filename}")
        
        user_db.commit()
        click.echo("\nAutomatic scan completed!")
        
        # Handle manual matching for unmatched files
        manual_match(game_db, user_db, unmatched_files)
        
    finally:
        game_db.close()
        user_db.close()

if __name__ == '__main__':
    main() 