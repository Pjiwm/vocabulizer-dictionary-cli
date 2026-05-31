import os
import sqlite3
from pathlib import Path


class DictionaryInstaller:
    def __init__(self, db_file_name):
        self.db_file_name = db_file_name
        self.extract_dir = './extracted_files'
        self.db_dir = Path("./db_files")
        self.db_file = self.db_dir / db_file_name

    def setup(self):
        """Prepare the directories for the extraction and database."""
        print(f"Database file will be created at: {self.db_file}")
        self.db_dir.mkdir(exist_ok=True)
        # Remove existing db to rebuild cleanly
        if self.db_file.exists():
            self.db_file.unlink()

    def create_tables(self, cursor, conn):
        """Create the normalized tables in the database."""
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS words (
                sequence INTEGER PRIMARY KEY,
                jlpt_level INTEGER
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS senses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sequence INTEGER NOT NULL REFERENCES words(sequence),
                term TEXT NOT NULL,
                reading TEXT NOT NULL,
                pos TEXT,
                frequency INTEGER DEFAULT 0,
                translation TEXT,
                pitch_accent TEXT
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS kanji (
                character TEXT PRIMARY KEY,
                stroke_count INTEGER,
                grade INTEGER,
                jlpt_level INTEGER,
                meanings TEXT,
                readings_on TEXT,
                readings_kun TEXT
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS glosses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sense_id INTEGER NOT NULL REFERENCES senses(id),
                gloss TEXT NOT NULL,
                position INTEGER NOT NULL DEFAULT 0
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS kanji_word_map (
                character TEXT NOT NULL,
                sequence INTEGER NOT NULL,
                PRIMARY KEY (character, sequence)
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_kwm_sequence ON kanji_word_map(sequence)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_sense_term ON senses(term)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_sense_reading ON senses(reading)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_sense_sequence ON senses(sequence)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_gloss_text ON glosses(gloss COLLATE NOCASE)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_gloss_sense ON glosses(sense_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_kanji_char ON kanji(character)')
        conn.commit()
        print("Database tables created.")

    def cleanup(self):
        """Remove extracted files directory."""
        print(f"Cleaning up extracted files from {self.extract_dir}")
        if os.path.exists(self.extract_dir):
            for root, dirs, files in os.walk(self.extract_dir, topdown=False):
                for file in files:
                    os.remove(os.path.join(root, file))
                for directory in dirs:
                    os.rmdir(os.path.join(root, directory))
            os.rmdir(self.extract_dir)
        print("Cleanup complete.")
