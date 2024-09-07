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
        """Create the necessary tables in the database."""
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS entries (
                id INTEGER PRIMARY KEY,
                term TEXT,
                reading TEXT,
                pos TEXT,
                frequency INTEGER,
                translation TEXT,
                additional_info TEXT
            )
        ''')
        print("Database tables created.")

    def create_db_connection(self):
        """Create a connection to the SQLite database."""
        self.conn = sqlite3.connect(self.db_file)
        self.cursor = self.conn.cursor()

    def cleanup(self):
        """Clean up the extracted files, the downloaded file, and other temporary resources."""
        # Remove extracted files and directories
        print(f"Cleaning up extracted files from {self.extract_dir}")
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
