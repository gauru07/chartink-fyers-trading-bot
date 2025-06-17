import sqlite3

# Connect to the database (this will create it if not exists)
conn = sqlite3.connect("alerts.db")
cursor = conn.cursor()

# Create the alerts table
cursor.execute("""
    CREATE TABLE IF NOT EXISTS alerts (
        alert_id TEXT PRIMARY KEY,
        stock TEXT,
        trigger_price REAL,
        side TEXT,
        timestamp TEXT,
        status TEXT
    )
""")

conn.commit()
conn.close()
