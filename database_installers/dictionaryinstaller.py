import os
import sqlite3
from pathlib import Path


class DictionaryInstaller:
    def __init__(self, downloaded_file, db_file_name):
        self.downloaded_file = downloaded_file
        self.db_file_name = db_file_name
        self.extract_dir = './extracted_files'
        self.db_dir = Path("./db_files")
        self.db_file = self.db_dir / db_file_name
        self.steps = []

    def setup(self):
        """Prepare the directories for the extraction and database."""
        print(f"Extract directory: {self.extract_dir}")
        print(f"Database file will be created at: {self.db_file}")
        self.db_dir.mkdir(exist_ok=True)

    def create_tables(self):
        """Create the normalized tables in the database."""
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS words (
                sequence INTEGER PRIMARY KEY
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS senses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sequence INTEGER NOT NULL REFERENCES words(sequence),
                term TEXT NOT NULL,
                reading TEXT NOT NULL,
                pos TEXT,
                frequency INTEGER DEFAULT 0,
                translation TEXT
            )
        ''')
        self.cursor.execute('''
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
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS glosses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sense_id INTEGER NOT NULL REFERENCES senses(id),
                gloss TEXT NOT NULL,
                position INTEGER NOT NULL DEFAULT 0
            )
        ''')
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_sense_term ON senses(term)')
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_sense_reading ON senses(reading)')
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_sense_sequence ON senses(sequence)')
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_gloss_text ON glosses(gloss COLLATE NOCASE)')
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_gloss_sense ON glosses(sense_id)')
        self.conn.commit()
        print("Database tables created.")

    def create_db_connection(self):
        """Create a connection to the SQLite database."""
        self.conn = sqlite3.connect(self.db_file)
        self.cursor = self.conn.cursor()

    def cleanup(self):
        # Remove extracted files and directories
        print(f"Cleaning up extracted files from {self.extract_dir}")
        if os.path.exists(self.extract_dir):
            for root, dirs, files in os.walk(self.extract_dir, topdown=False):
                for file in files:
                    os.remove(os.path.join(root, file))
                for directory in dirs:
                    os.rmdir(os.path.join(root, directory))
            os.rmdir(self.extract_dir)

        # Remove the downloaded file
        if os.path.exists(self.downloaded_file):
            os.remove(self.downloaded_file)
            print(f"Removed downloaded file: {self.downloaded_file}")
        else:
            print(f"Downloaded file {self.downloaded_file} not found.")

        print("Cleanup complete.")

    def run(self):
        """Main execution flow with customizable steps."""
        self.setup()
        for step in self.steps:
            step()
        self.create_db_connection()
        self.create_tables()
        self.populate_db(self.cursor, self.conn)
        self.cleanup()

    def populate_db(self, cursor, conn):
        """Placeholder for populate_db method."""
        raise NotImplementedError("Subclasses must implement this method.")

    def extract_files(self):
        """Placeholder for extract_files method."""
        raise NotImplementedError("Subclasses must implement this method.")
