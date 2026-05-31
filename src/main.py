import os
import sys
import json
import logging
import sqlite3
import requests
from InquirerPy import inquirer
from pathlib import Path
from tqdm import tqdm

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from database_installers.dictionaryinstaller import DictionaryInstaller
from database_installers import jmdict, kanjidic, jlpt, pitch_accent

required_dir = "dictionary_builders"
current_dir = os.path.basename(os.getcwd())

if current_dir != required_dir:
    print(
        f"Error: You must run this script from the '{required_dir}' directory.")
    print(f"Current directory: {os.getcwd()}")
    print(
        f"Please navigate to the '{required_dir}' directory and run the script using 'python3 src/main.py'.")
    sys.exit(1)


# Set up logging
logging.basicConfig(filename="download.log", level=logging.INFO,
                    format="%(asctime)s - %(message)s")

# Load links from the JSON file
with open("src/links.json", "r") as f:
    data = json.load(f)

# Create downloads directory if it doesn't exist
downloads_dir = Path("downloads")
downloads_dir.mkdir(exist_ok=True)

extract_dir = './extracted_files'


def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")


def download_file(name, url, destination, filename):
    try:
        logging.info(f"Starting download for: {name}")
        response = requests.get(url, stream=True)
        response.raise_for_status()
        file_size = int(response.headers.get('content-length', 0))
        dest_file = destination / filename

        with open(dest_file, "wb") as f, tqdm(
            desc=name,
            total=file_size,
            unit='B',
            unit_scale=True,
            unit_divisor=1024,
        ) as bar:
            for chunk in response.iter_content(1024):
                f.write(chunk)
                bar.update(len(chunk))

        logging.info(f"Successfully downloaded: {name}")
        return dest_file
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to download {name}: {e}")
        print(f"Error downloading {name}: {e}")
        return None


def build_dictionary(dictionary):
    """Download JMdict + KANJIDIC and build a single SQLite database."""
    name = dictionary["name"]
    db_file_name = dictionary["dbFileName"]

    print(f"\n=== Building {name} ===\n")

    # Download JMdict
    jmdict_file = download_file(
        f"{name} (JMdict)",
        dictionary["jmdict_url"],
        downloads_dir,
        dictionary["jmdict_file"]
    )
    if not jmdict_file:
        print(f"Failed to download JMdict for {name}. Skipping.")
        return

    # Download KANJIDIC
    kanjidic_file = download_file(
        f"{name} (KANJIDIC)",
        dictionary["kanjidic_url"],
        downloads_dir,
        dictionary["kanjidic_file"]
    )
    if not kanjidic_file:
        print(f"Failed to download KANJIDIC for {name}. Skipping.")
        return

    # Set up database
    installer = DictionaryInstaller(db_file_name)
    installer.setup()

    conn = sqlite3.connect(installer.db_file)
    cursor = conn.cursor()
    installer.create_tables(cursor, conn)

    # Populate JMdict data
    jmdict_extract = os.path.join(extract_dir, 'jmdict')
    os.makedirs(jmdict_extract, exist_ok=True)
    jmdict.extract_and_populate(jmdict_file, jmdict_extract, cursor, conn)

    # Populate KANJIDIC data
    kanjidic_extract = os.path.join(extract_dir, 'kanjidic')
    os.makedirs(kanjidic_extract, exist_ok=True)
    kanjidic.extract_and_populate(kanjidic_file, kanjidic_extract, cursor, conn)

    # Build kanji-word lookup table for fast cross-referencing
    print("  Building kanji_word_map...")
    cursor.execute('''
        INSERT OR IGNORE INTO kanji_word_map (character, sequence)
        SELECT DISTINCT k.character, s.sequence
        FROM kanji k
        INNER JOIN senses s ON INSTR(s.term, k.character) > 0
    ''')
    conn.commit()
    cursor.execute('SELECT COUNT(*) FROM kanji_word_map')
    kwm_count = cursor.fetchone()[0]
    print(f"  kanji_word_map: {kwm_count} entries")

    # Backfill N5 kanji from grade 1 (KANJIDIC uses old JLPT 1-4, no N5)
    print("  Backfilling N5 kanji (grade 1)...")
    cursor.execute('''
        UPDATE kanji SET jlpt_level = 5
        WHERE grade = 1
    ''')
    n5_backfilled = cursor.rowcount
    conn.commit()
    print(f"  N5 kanji backfilled: {n5_backfilled}")

    # Populate word-level JLPT data from external lists
    jlpt.populate_word_jlpt(cursor, conn)

    # Populate pitch accent from UniDic
    pitch_accent.populate_pitch_accent(cursor, conn)

    # Print stats
    cursor.execute('SELECT COUNT(*) FROM words')
    word_count = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM senses')
    sense_count = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM kanji')
    kanji_count = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM words WHERE jlpt_level IS NOT NULL')
    jlpt_count = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(DISTINCT term || reading) FROM senses WHERE pitch_accent IS NOT NULL')
    pitch_count = cursor.fetchone()[0]
    print(f"\n  Database: {db_file_name}")
    print(f"  Words: {word_count}, Senses: {sense_count}, Kanji: {kanji_count}")
    print(f"  Words with JLPT: {jlpt_count}, With pitch accent: {pitch_count}\n")

    conn.close()
    installer.cleanup()

    # Clean up downloaded zips
    os.remove(jmdict_file)
    os.remove(kanjidic_file)

    print(f"=== {name} complete ===\n")


def main():
    while True:
        clear_screen()

        choices = [d["name"] for d in data["dictionaries"]]
        choices.append("Build All")
        choices.append("Exit")

        selected = inquirer.select(
            message="Select a dictionary to build or choose an option:",
            choices=choices
        ).execute()

        if selected == "Exit":
            logging.info("User exited the program.")
            break

        if selected == "Build All":
            confirm = inquirer.confirm(
                message="Build all dictionaries? This will download and process all sources."
            ).execute()
            if confirm:
                for dictionary in data["dictionaries"]:
                    build_dictionary(dictionary)
        else:
            dictionary = next(
                d for d in data["dictionaries"] if d["name"] == selected)
            confirm = inquirer.confirm(
                message=f"Build {dictionary['name']}?"
            ).execute()
            if confirm:
                build_dictionary(dictionary)

        inquirer.select("Press enter to continue",
                        choices=["Continue"]).execute()


if __name__ == "__main__":
    main()
