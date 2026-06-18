"""
migrate_add_foundation_type.py
Adds 'foundation' as a valid entry_type in rocky_core_entries.

Usage:
    DATABASE_URL=your_connection_string python3 migrate_add_foundation_type.py
"""

import os
import psycopg2

DATABASE_URL = os.environ.get('DATABASE_URL')

if not DATABASE_URL:
    print("ERROR: DATABASE_URL environment variable not set.")
    exit(1)

conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

# Drop the existing CHECK constraint and replace it with one that includes 'foundation'
cur.execute("""
    ALTER TABLE rocky_core_entries
    DROP CONSTRAINT IF EXISTS rocky_core_entries_entry_type_check;
""")

cur.execute("""
    ALTER TABLE rocky_core_entries
    ADD CONSTRAINT rocky_core_entries_entry_type_check
    CHECK (entry_type IN ('story', 'opinion', 'fact', 'testimonial', 'foundation'));
""")

conn.commit()
cur.close()
conn.close()

print("Migration complete: 'foundation' added as valid entry_type.")
