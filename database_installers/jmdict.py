import json
import sqlite3
import os
import zipfile
from pathlib import Path
import sys


def extract_zip(zip_file, extract_dir):
    """Extracts the contents of the ZIP file to the specified directory."""
    print(f"Extracting {zip_file} to {extract_dir}")
    with zipfile.ZipFile(zip_file, 'r') as zip_ref:
        zip_ref.extractall(extract_dir)
    print(f"Extraction complete.")


def create_tables(cursor):
    """Creates the necessary tables in the SQLite database."""
    cursor.execute('''
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


def populate_db(json_dir, cursor, conn):
    """Populates the SQLite database with data from JSON files in the specified directory."""
    print(f"Populating database from {json_dir}")
    for json_file in os.listdir(json_dir):
        if json_file.endswith('.json'):
            with open(os.path.join(json_dir, json_file), 'r', encoding='utf-8') as f:
                data = json.load(f)
                print(f"Loaded {len(data)} entries from {json_file}")

                for entry in data:
                    if len(entry) >= 8:
                        term = entry[0]
                        reading = entry[1]
                        pos = entry[2]
                        frequency = entry[4]
                        gloss_list = entry[5]
                        additional_info = entry[7]

                        cursor.execute('''
                            INSERT INTO entries (term, reading, pos, frequency, translation, additional_info)
                            VALUES (?, ?, ?, ?, ?, ?)
                        ''', (term, reading, pos, frequency, ', '.join(gloss_list), additional_info))
                    else:
                        print(f"Skipping malformed entry: {entry}")

    conn.commit()
    print("Database populated.")


def cleanup(extract_dir, zip_file):
    """Cleans up the extracted files and the downloaded ZIP file."""
    print(f"Cleaning up {extract_dir} and {zip_file}")
    for root, dirs, files in os.walk(extract_dir, topdown=False):
        for file in files:
            os.remove(os.path.join(root, file))
        for directory in dirs:
            os.rmdir(os.path.join(root, directory))
    os.rmdir(extract_dir)
    os.remove(zip_file)
    print("Cleanup complete.")


def main(downloaded_file, db_file_name):
    extract_dir = './extracted_files'
    db_dir = Path("./db_files")
    db_dir.mkdir(exist_ok=True)
    db_file = db_dir / db_file_name

    print(f"Extract directory: {extract_dir}")
    print(f"Database file will be created at: {db_file}")

    extract_zip(downloaded_file, extract_dir)

    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()

    create_tables(cursor)
    populate_db(extract_dir, cursor, conn)

    conn.close()

    cleanup(extract_dir, downloaded_file)

    print(f"Database created at: {db_file}")


if __name__ == "__main__":
    if len(sys.argv) == 3:
        main(sys.argv[1], sys.argv[2])
    else:
        print("Usage: python script.py <downloaded_file> <db_file_name>")
