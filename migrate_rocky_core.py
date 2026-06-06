"""
migrate_rocky_core.py
Run once against the live DATABASE_URL to create the rocky_core_entries table.

Usage:
    DATABASE_URL=your_connection_string python migrate_rocky_core.py
"""

import os
import psycopg2

DATABASE_URL = os.environ.get('DATABASE_URL')

if not DATABASE_URL:
    print("ERROR: DATABASE_URL environment variable not set.")
    exit(1)

conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

cur.execute("""
    CREATE TABLE IF NOT EXISTS rocky_core_entries (
        id              SERIAL PRIMARY KEY,
        entry_type      VARCHAR(20) NOT NULL CHECK (entry_type IN ('story', 'opinion', 'fact', 'testimonial')),
        content         TEXT NOT NULL,
        significance    SMALLINT NOT NULL DEFAULT 1 CHECK (significance IN (1, 2, 3)),
        created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
""")

conn.commit()
cur.close()
conn.close()

print("rocky_core_entries table created (or already existed).")
