import sqlite3

conn = sqlite3.connect('ohlc.sqlite3')
cursor = conn.cursor()

print("All tables in the database:")
print("=" * 60)

cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = cursor.fetchall()

for table in tables:
    print(f"\nTable: {table[0]}")
    cursor.execute(f"SELECT COUNT(*) FROM {table[0]}")
    count = cursor.fetchone()[0]
    print(f"  Rows: {count}")
    
    cursor.execute(f"PRAGMA table_info({table[0]})")
    columns = cursor.fetchall()
    print(f"  Columns: {', '.join([col[1] for col in columns])}")

conn.close()
