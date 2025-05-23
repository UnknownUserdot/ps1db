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
GAME_DB_PATH = os.path.join(os.path.dirname(__file__), "data", "ps1_games.db")
USER_DB_PATH = os.path.join(get_user_data_dir(), "user_collection.db")

# Ensure the game database exists
if not os.path.exists(GAME_DB_PATH):
    os.makedirs(os.path.dirname(GAME_DB_PATH), exist_ok=True)
    # TODO: Initialize with game data

# Create user database engine
user_engine = create_engine(f"sqlite:///{USER_DB_PATH}")
UserSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=user_engine)
Base = declarative_base()

class Game(Base):
    __tablename__ = "games"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    serial_number = Column(String, index=True)
    developer = Column(String)
    publisher = Column(String)
    release_date_jp = Column(String)
    release_date_eu = Column(String)
    release_date_na = Column(String)
    is_launch_title = Column(Boolean, default=False)
    reference_url = Column(String)
    region_jp = Column(Boolean, default=False)
    region_eu = Column(Boolean, default=False)
    region_na = Column(Boolean, default=False)
    notes = Column(String)
    local_path = Column(String, nullable=True)  # Path to local backup if exists

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
    db = UserSessionLocal()
    try:
        query = db.query(Game)
        
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
                query = query.filter(Game.region_jp == True)
            elif region.upper() == 'EU':
                query = query.filter(Game.region_eu == True)
            elif region.upper() == 'NA':
                query = query.filter(Game.region_na == True)
            
        if local:
            query = query.filter(Game.local_path.isnot(None))
        
        games = query.all()
        
        if not games:
            click.echo("No games found matching your criteria.")
            return

        # Prepare table data
        table_data = [
            [g.title, g.serial_number, g.developer, g.publisher, g.region, 
             '✓' if g.local_path else '✗']
            for g in games
        ]
        
        # Print results in a nice table
        click.echo(tabulate(
            table_data,
            headers=['Title', 'Serial', 'Developer', 'Publisher', 'Regions', 'In Collection'],
            tablefmt='grid'
        ))
        
        click.echo(f"\nFound {len(games)} games")
        
    finally:
        db.close()

@main.command()
def stats():
    """Show statistics about your PS1 collection"""
    db = UserSessionLocal()
    try:
        total_games = db.query(Game).count()
        total_local = db.query(Game).filter(Game.local_path.isnot(None)).count()
        
        jp_games = db.query(Game).filter(Game.region_jp == True).count()
        eu_games = db.query(Game).filter(Game.region_eu == True).count()
        na_games = db.query(Game).filter(Game.region_na == True).count()
        
        click.echo(f"\nTotal Games in Database: {total_games}")
        click.echo(f"Games in Your Collection: {total_local}")
        click.echo("\nGames by Region:")
        click.echo(f"Japan: {jp_games} (You have: {db.query(Game).filter(Game.region_jp == True, Game.local_path.isnot(None)).count()})")
        click.echo(f"Europe: {eu_games} (You have: {db.query(Game).filter(Game.region_eu == True, Game.local_path.isnot(None)).count()})")
        click.echo(f"North America: {na_games} (You have: {db.query(Game).filter(Game.region_na == True, Game.local_path.isnot(None)).count()})")
            
    finally:
        db.close()

@main.command()
@click.argument('directory', type=click.Path(exists=True))
def scan(directory):
    """Scan a directory for PS1 games and update your collection"""
    db = UserSessionLocal()
    try:
        # Look for .bin, .iso, and .img files
        patterns = ['*.bin', '*.iso', '*.img']
        found_files = []
        for pattern in patterns:
            found_files.extend(glob.glob(os.path.join(directory, '**', pattern), recursive=True))
        
        if not found_files:
            click.echo("No PS1 game files found in the specified directory.")
            return
            
        # Update database with found files
        for file_path in found_files:
            # Get game name from filename
            filename = os.path.splitext(os.path.basename(file_path))[0]
            
            # Check for region indicators in filename
            is_jp = any(jp in filename.upper() for jp in ['JPN', 'JAP', '(J)'])
            is_pal = any(pal in filename.upper() for pal in ['PAL', 'EUR', '(E)'])
            is_na = any(na in filename.upper() for na in ['USA', 'NA', '(U)']) or (not is_jp and not is_pal)
            
            # Build query based on filename and region
            query = db.query(Game)
            
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
            
            # Try exact match first with region filter
            if is_jp:
                exact_matches = query.filter(func.lower(Game.title) == clean_name.lower(), Game.region_jp == True)
            elif is_pal:
                exact_matches = query.filter(func.lower(Game.title) == clean_name.lower(), Game.region_eu == True)
            else:  # Default to NA
                exact_matches = query.filter(func.lower(Game.title) == clean_name.lower(), Game.region_na == True)
            
            if exact_matches.count() > 0:
                games = exact_matches.all()
            else:
                # Fall back to partial match with region filter
                if is_jp:
                    query = query.filter(Game.title.ilike(f"%{clean_name}%"), Game.region_jp == True)
                elif is_pal:
                    query = query.filter(Game.title.ilike(f"%{clean_name}%"), Game.region_eu == True)
                else:  # Default to NA
                    query = query.filter(Game.title.ilike(f"%{clean_name}%"), Game.region_na == True)
                games = query.all()
            
            if games:
                if len(games) == 1:
                    # Exact match found
                    game = games[0]
                    game.local_path = file_path
                    regions = []
                    if game.region_jp: regions.append("JP")
                    if game.region_eu: regions.append("EU")
                    if game.region_na: regions.append("NA")
                    click.echo(f"Updated: {game.title} ({', '.join(regions)})")
                else:
                    # Multiple matches found
                    click.echo(f"\nMultiple matches found for {filename}:")
                    for i, game in enumerate(games, 1):
                        regions = []
                        if game.region_jp: regions.append("JP")
                        if game.region_eu: regions.append("EU")
                        if game.region_na: regions.append("NA")
                        click.echo(f"{i}. {game.title} ({', '.join(regions)})")
                    click.echo("Please manually verify this game")
            else:
                click.echo(f"No match found for: {filename}")
        
        db.commit()
        click.echo("\nScan completed!")
        
    finally:
        db.close()

if __name__ == '__main__':
    main() 