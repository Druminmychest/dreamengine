#!/usr/bin/env python3
"""
Migration: create time_machine_cache table
Run once: python3 migrate_time_machine_cache.py
Requires DATABASE_URL in environment.
"""

import os
import psycopg2

database_url = os.environ.get('DATABASE_URL')
if not database_url:
    print("ERROR: DATABASE_URL not set in environment.")
    exit(1)

conn = psycopg2.connect(database_url)
cur = conn.cursor()

cur.execute("""
    CREATE TABLE IF NOT EXISTS time_machine_cache (
        id           SERIAL PRIMARY KEY,
        cache_date   DATE        NOT NULL,
        era          TEXT        NOT NULL,
        title        TEXT        NOT NULL,
        narrative    TEXT        NOT NULL,
        context_pills TEXT       NOT NULL,
        created_at   TIMESTAMP   DEFAULT CURRENT_TIMESTAMP,
        UNIQUE (cache_date, era)
    );
""")

conn.commit()
cur.close()
conn.close()

print("time_machine_cache table created successfully.")
