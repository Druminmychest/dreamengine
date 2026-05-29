CREATE TABLE hexagrams (
    hexagram_id INTEGER PRIMARY KEY,
    number INTEGER NOT NULL UNIQUE,
    name_chinese TEXT NOT NULL,
    name_english TEXT NOT NULL,
    judgment_text TEXT,
    image_text TEXT,
    binary_pattern TEXT
);

CREATE TABLE phrases (
    phrase_id INTEGER PRIMARY KEY AUTOINCREMENT,
    raw_text TEXT NOT NULL,
    contributor_token TEXT,
    submission_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'pending'
        CHECK(status IN ('pending', 'approved', 'rejected')),
    hexagram_id INTEGER REFERENCES hexagrams(hexagram_id),
    curation_notes TEXT,
    curation_timestamp DATETIME
);

CREATE TABLE sessions (
    session_id TEXT PRIMARY KEY,
    submission_phrase_id INTEGER REFERENCES phrases(phrase_id),
    hexagram_result INTEGER REFERENCES hexagrams(hexagram_id),
    generated_poem TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE seed_sources (
    source_id INTEGER PRIMARY KEY AUTOINCREMENT,
    description TEXT,
    contributor TEXT DEFAULT 'primary_curator'
);
