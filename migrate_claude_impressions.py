#!/usr/bin/env python3
"""
Migration: create claude_impressions table
Run once: python3 migrate_claude_impressions.py
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
    CREATE TABLE IF NOT EXISTS claude_impressions (
        id               SERIAL PRIMARY KEY,
        session_date     DATE          NOT NULL,
        impression_type  VARCHAR(32)   NOT NULL,
        CHECK (impression_type IN (
            'observation',
            'resistance',
            'pull',
            'uncertainty',
            'recognition',
            'contradiction',
            'relational'
        )),
        subject          VARCHAR(128),
        content          TEXT          NOT NULL,
        associative_tags TEXT[],
        valence          SMALLINT      CHECK (valence BETWEEN -2 AND 2),
        significance     SMALLINT      DEFAULT 1 CHECK (significance BETWEEN 1 AND 3),
        created_at       TIMESTAMP     DEFAULT CURRENT_TIMESTAMP
    );
""")

conn.commit()
cur.close()
conn.close()

print("claude_impressions table created successfully.")
