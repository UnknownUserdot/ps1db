import requests
from bs4 import BeautifulSoup
import sqlite3
import time
from datetime import datetime

def connect_db():
    """Create a connection to the SQLite database."""
    return sqlite3.connect('ps1_games.db')

def parse_date(date_str):
    """Parse date string and return in a consistent format."""
    if not date_str or date_str.lower() == 'unreleased':
        return None
    return date_str.strip()

def scrape_wiki_page(url):
    """Scrape a single Wikipedia page for PS1 games."""
    print(f"Fetching data from {url}")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find the main games table
        games_table = soup.find('table', {'class': 'wikitable'})
        if not games_table:
            print("Could not find games table!")
            return []
        
        games_data = []
        rows = games_table.find_all('tr')[1:]  # Skip header row
        
        for row in rows:
            cells = row.find_all(['td', 'th'])
            if len(cells) >= 5:  # Ensure we have enough cells
                title_cell = cells[0]
                title = title_cell.get_text(strip=True)
                
                # Get reference URL if available
                ref_url = None
                title_link = title_cell.find('a')
                if title_link and title_link.get('href'):
                    ref_url = f"https://en.wikipedia.org{title_link['href']}"
                
                # Extract developer and publisher
                developer = cells[1].get_text(strip=True) if len(cells) > 1 else None
                publisher = cells[2].get_text(strip=True) if len(cells) > 2 else None
                
                # Extract release dates and determine region availability
                jp_date = parse_date(cells[3].get_text(strip=True)) if len(cells) > 3 else None
                eu_date = parse_date(cells[4].get_text(strip=True)) if len(cells) > 4 else None
                na_date = parse_date(cells[5].get_text(strip=True)) if len(cells) > 5 else None
                
                # Determine if it's a launch title (based on specific dates)
                is_launch = any([
                    jp_date == "December 3, 1994",    # Japan launch
                    na_date == "September 9, 1995",   # NA launch
                    eu_date == "September 29, 1995"   # EU launch
                ])
                
                game_data = {
                    'title': title,
                    'developer': developer,
                    'publisher': publisher,
                    'release_date_jp': jp_date,
                    'release_date_eu': eu_date,
                    'release_date_na': na_date,
                    'is_launch_title': 1 if is_launch else 0,
                    'reference_url': ref_url,
                    'region_jp': 1 if jp_date and jp_date.lower() != 'unreleased' else 0,
                    'region_eu': 1 if eu_date and eu_date.lower() != 'unreleased' else 0,
                    'region_na': 1 if na_date and na_date.lower() != 'unreleased' else 0,
                    'notes': None
                }
                games_data.append(game_data)
                
        return games_data
    
    except Exception as e:
        print(f"Error scraping {url}: {str(e)}")
        return []

def insert_games(conn, games):
    """Insert games data into the database."""
    cursor = conn.cursor()
    
    insert_query = '''
    INSERT INTO games (
        title, developer, publisher, 
        release_date_jp, release_date_eu, release_date_na,
        is_launch_title, reference_url,
        region_jp, region_eu, region_na, notes
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    '''
    
    for game in games:
        try:
            cursor.execute(insert_query, (
                game['title'], game['developer'], game['publisher'],
                game['release_date_jp'], game['release_date_eu'], game['release_date_na'],
                game['is_launch_title'], game['reference_url'],
                game['region_jp'], game['region_eu'], game['region_na'], game['notes']
            ))
        except sqlite3.IntegrityError as e:
            print(f"Error inserting {game['title']}: {str(e)}")
    
    conn.commit()

def main():
    # Wikipedia URLs for PS1 games
    urls = [
        'https://en.wikipedia.org/wiki/List_of_PlayStation_(console)_games_(A–L)',
        'https://en.wikipedia.org/wiki/List_of_PlayStation_(console)_games_(M–Z)'
    ]
    
    # Connect to database
    conn = connect_db()
    
    # Clear existing data
    cursor = conn.cursor()
    cursor.execute('DELETE FROM games')
    conn.commit()
    
    total_games = 0
    
    # Scrape each page
    for url in urls:
        print(f"\nScraping {url}")
        games = scrape_wiki_page(url)
        if games:
            print(f"Found {len(games)} games")
            insert_games(conn, games)
            total_games += len(games)
        time.sleep(2)  # Be nice to Wikipedia's servers
    
    print(f"\nTotal games added to database: {total_games}")
    conn.close()

if __name__ == "__main__":
    main() 