import sqlite3

def print_results(cursor, query, params=()):
    """Execute a query and print results in a formatted way."""
    cursor.execute(query, params)
    results = cursor.fetchall()
    if not results:
        print("No results found")
        return
    
    # Get column names
    columns = [description[0] for description in cursor.description]
    
    # Print header
    print("\n" + "="*100)
    print(" | ".join(columns))
    print("="*100)
    
    # Print rows
    for row in results:
        print(" | ".join(str(item) if item is not None else 'None' for item in row))
    print("="*100 + "\n")

def main():
    conn = sqlite3.connect('ps1_games.db')
    cursor = conn.cursor()
    
    # 1. Count total games
    cursor.execute('SELECT COUNT(*) FROM games')
    total_games = cursor.fetchone()[0]
    print(f"\nTotal games in database: {total_games}")
    
    # 2. Show launch titles
    print("\nLaunch Titles:")
    print_results(cursor, '''
        SELECT title, developer, publisher, 
               release_date_jp, release_date_eu, release_date_na
        FROM games 
        WHERE is_launch_title = 1
    ''')
    
    # 3. Count games by region
    print("\nGames by Region:")
    cursor.execute('''
        SELECT 
            SUM(region_jp) as Japan,
            SUM(region_eu) as Europe,
            SUM(region_na) as "North America"
        FROM games
    ''')
    regions = cursor.fetchone()
    print(f"Japan: {regions[0]}")
    print(f"Europe: {regions[1]}")
    print(f"North America: {regions[2]}")
    
    # 4. Sample of 5 random games
    print("\nRandom Sample of Games:")
    print_results(cursor, '''
        SELECT title, developer, publisher
        FROM games 
        ORDER BY RANDOM() 
        LIMIT 5
    ''')
    
    conn.close()

if __name__ == "__main__":
    main() 