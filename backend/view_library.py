import sqlite3
from tabulate import tabulate

def view_library():
    """View the user's game library with details from the main database."""
    conn = sqlite3.connect('ps1_games.db')
    cursor = conn.cursor()
    
    # Join usr_lib with games table to get full game information
    cursor.execute('''
        SELECT 
            g.title,
            g.developer,
            g.publisher,
            ul.file_type,
            ul.file_size,
            ul.last_scanned,
            ul.file_path
        FROM usr_lib ul
        JOIN games g ON ul.game_id = g.id
        ORDER BY g.title
    ''')
    
    results = cursor.fetchall()
    
    if not results:
        print("\nNo games found in your library!")
        return
    
    # Convert file sizes to MB
    formatted_results = []
    for row in results:
        title, dev, pub, ftype, size, scanned, path = row
        size_mb = f"{size / (1024*1024):.2f} MB" if size else "Unknown"
        formatted_results.append([title, dev, pub, ftype, size_mb, scanned])
    
    # Print results in a nice table
    headers = ["Title", "Developer", "Publisher", "File Type", "Size", "Last Scanned"]
    print("\nYour PS1 Game Library:")
    print(tabulate(formatted_results, headers=headers, tablefmt="grid"))
    
    # Print summary
    print(f"\nTotal games in library: {len(results)}")
    
    # Count by file type
    cursor.execute('SELECT file_type, COUNT(*) FROM usr_lib GROUP BY file_type')
    type_counts = cursor.fetchall()
    print("\nFile types:")
    for ftype, count in type_counts:
        print(f"  {ftype}: {count} files")
    
    conn.close()

if __name__ == "__main__":
    view_library() 