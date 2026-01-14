import sqlite3
import pandas as pd
from datetime import datetime

# Connect to the database
conn = sqlite3.connect('ohlc.sqlite3')
cursor = conn.cursor()

print("=" * 60)
print("CRYPTO SQLITE DATABASE ANALYSIS")
print("=" * 60)

# Get all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [row[0] for row in cursor.fetchall()]
print(f"\nFound {len(tables)} table(s): {tables}\n")

# Analyze each table
for table in tables:
    print("=" * 60)
    print(f"TABLE: {table}")
    print("=" * 60)
    
    # Get table schema
    cursor.execute(f"PRAGMA table_info({table})")
    columns = cursor.fetchall()
    print("\nColumns:")
    for col in columns:
        print(f"  - {col[1]} ({col[2]})")
    
    # Get row count
    cursor.execute(f"SELECT COUNT(*) FROM {table}")
    row_count = cursor.fetchone()[0]
    print(f"\nTotal rows: {row_count:,}")
    
    # Get sample data
    if row_count > 0:
        cursor.execute(f"SELECT * FROM {table} LIMIT 5")
        sample_data = cursor.fetchall()
        col_names = [col[1] for col in columns]
        
        print("\nSample data (first 5 rows):")
        df = pd.DataFrame(sample_data, columns=col_names)
        print(df.to_string(index=False))
        
        # Basic statistics if numeric data exists
        numeric_cols = [col[1] for col in columns if 'REAL' in col[2] or 'FLOAT' in col[2] or 'INT' in col[2]]
        if numeric_cols:
            print("\nNumeric statistics:")
            for col in numeric_cols:
                cursor.execute(f"SELECT MIN({col}), MAX({col}), AVG({col}) FROM {table}")
                stats = cursor.fetchone()
                print(f"  {col}:")
                print(f"    Min: {stats[0]}")
                print(f"    Max: {stats[1]}")
                print(f"    Avg: {stats[2]:.4f}")
    
    print("\n")

conn.close()
print("=" * 60)
print("ANALYSIS COMPLETE")
print("=" * 60)
