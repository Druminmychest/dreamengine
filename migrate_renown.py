"""
migrate_renown.py
Run once against the live DATABASE_URL to:
  1. Add 'source' and 'contributor' columns to rocky_core_entries
  2. Create the renown_submissions table for the public pending queue

Usage:
    DATABASE_URL=your_connection_string python3 migrate_renown.py
"""

import os
import psycopg2

DATABASE_URL = os.environ.get('DATABASE_URL')

if not DATABASE_URL:
    print("ERROR: DATABASE_URL environment variable not set.")
    exit(1)

conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

# 1. Add source column to rocky_core_entries (defaults to 'core' for all existing entries)
cur.execute("""
    ALTER TABLE rocky_core_entries
    ADD COLUMN IF NOT EXISTS source VARCHAR(20) NOT NULL DEFAULT 'core'
        CHECK (source IN ('core', 'renown'));
""")

# 2. Add contributor column (nullable — only populated for renown submissions)
cur.execute("""
    ALTER TABLE rocky_core_entries
    ADD COLUMN IF NOT EXISTS contributor VARCHAR(100);
""")

# 3. Create renown_submissions table for the pending approval queue
cur.execute("""
    CREATE TABLE IF NOT EXISTS renown_submissions (
        id          SERIAL PRIMARY KEY,
        entry_type  VARCHAR(20) NOT NULL CHECK (entry_type IN ('story', 'opinion', 'fact', 'testimonial', 'tall tale')),
        content     TEXT NOT NULL,
        contributor VARCHAR(100),
        status      VARCHAR(20) NOT NULL DEFAULT 'pending'
                        CHECK (status IN ('pending', 'approved', 'rejected')),
        submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
""")

conn.commit()
cur.close()
conn.close()

print("Migration complete:")
print("  - rocky_core_entries: added 'source' and 'contributor' columns")
print("  - renown_submissions: table created (or already existed)")
