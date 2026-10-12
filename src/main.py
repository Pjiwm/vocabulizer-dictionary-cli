import os
import sys
import json
import logging
import sqlite3
import requests
from InquirerPy import inquirer
from pathlib import Path
from tqdm import tqdm

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))
from database_installers.dictionaryinstaller import DictionaryInstaller
from database_installers import jmdict, kanjidic, jlpt, pitch_accent

DOWNLOADS_DIR = ROOT_DIR / "downloads"
DB_DIR = ROOT_DIR / "db_files"
EXTRACT_DIR = ROOT_DIR / "extracted_files"

logging.basicConfig(
    filename=str(ROOT_DIR / "download.log"),
    level=logging.INFO,
    format="%(asctime)s - %(message)s",
)

with open(ROOT_DIR / "src" / "links.json", "r") as f:
    data = json.load(f)

DOWNLOADS_DIR.mkdir(exist_ok=True)


def download_file(name, url, filename):
    try:
        logging.info(f"Starting download for: {name}")
        response = requests.get(url, stream=True)
        response.raise_for_status()
        file_size = int(response.headers.get("content-length", 0))
        dest_file = DOWNLOADS_DIR / filename

        with open(dest_file, "wb") as f, tqdm(
            desc=name, total=file_size, unit="B", unit_scale=True, unit_divisor=1024
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

    jmdict_file = download_file(
        f"{name} (JMdict)", dictionary["jmdict_url"], dictionary["jmdict_file"]
    )
    if not jmdict_file:
        print(f"Failed to download JMdict for {name}. Skipping.")
        return

    kanjidic_file = download_file(
        f"{name} (KANJIDIC)", dictionary["kanjidic_url"], dictionary["kanjidic_file"]
    )
    if not kanjidic_file:
        print(f"Failed to download KANJIDIC for {name}. Skipping.")
        return

    installer = DictionaryInstaller(db_file_name)
    installer.db_dir = DB_DIR
    installer.extract_dir = str(EXTRACT_DIR)
    installer.db_file = DB_DIR / db_file_name
    installer.setup()

    conn = sqlite3.connect(installer.db_file)
    cursor = conn.cursor()
    installer.create_tables(cursor, conn)

    jmdict_extract = str(EXTRACT_DIR / "jmdict")
    os.makedirs(jmdict_extract, exist_ok=True)
    jmdict.extract_and_populate(jmdict_file, jmdict_extract, cursor, conn)

    kanjidic_extract = str(EXTRACT_DIR / "kanjidic")
    os.makedirs(kanjidic_extract, exist_ok=True)
    kanjidic.extract_and_populate(kanjidic_file, kanjidic_extract, cursor, conn)

    print("  Building kanji_word_map...")
    cursor.execute("""
        INSERT OR IGNORE INTO kanji_word_map (character, sequence)
        SELECT DISTINCT k.character, s.sequence
        FROM kanji k
        INNER JOIN senses s ON INSTR(s.term, k.character) > 0
    """)
    conn.commit()
    cursor.execute("SELECT COUNT(*) FROM kanji_word_map")
    print(f"  kanji_word_map: {cursor.fetchone()[0]} entries")

    print("  Backfilling N5 kanji (grade 1)...")
    cursor.execute("UPDATE kanji SET jlpt_level = 5 WHERE grade = 1")
    n5_backfilled = cursor.rowcount
    conn.commit()
    print(f"  N5 kanji backfilled: {n5_backfilled}")

    jlpt.populate_word_jlpt(cursor, conn)
    pitch_accent.populate_pitch_accent(cursor, conn)

    cursor.execute("SELECT COUNT(*) FROM words")
    word_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM senses")
    sense_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM kanji")
    kanji_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM words WHERE jlpt_level IS NOT NULL")
    jlpt_count = cursor.fetchone()[0]
    cursor.execute(
        "SELECT COUNT(DISTINCT term || reading) FROM senses WHERE pitch_accent IS NOT NULL"
    )
    pitch_count = cursor.fetchone()[0]
    print(f"\n  Database: {db_file_name}")
    print(f"  Words: {word_count}, Senses: {sense_count}, Kanji: {kanji_count}")
    print(f"  Words with JLPT: {jlpt_count}, With pitch accent: {pitch_count}\n")

    conn.close()
    installer.cleanup()

    os.remove(jmdict_file)
    os.remove(kanjidic_file)

    print(f"=== {name} complete ===\n")


def main():
    while True:
        os.system("cls" if os.name == "nt" else "clear")

        choices = [d["name"] for d in data["dictionaries"]]
        choices.append("Build All")
        choices.append("Exit")

        selected = inquirer.select(
            message="Select a dictionary to build:", choices=choices
        ).execute()

        if selected == "Exit":
            break

        if selected == "Build All":
            if inquirer.confirm(message="Build all dictionaries?").execute():
                for dictionary in data["dictionaries"]:
                    build_dictionary(dictionary)
        else:
            dictionary = next(
                d for d in data["dictionaries"] if d["name"] == selected
            )
            if inquirer.confirm(message=f"Build {dictionary['name']}?").execute():
                build_dictionary(dictionary)

        inquirer.select("Press enter to continue", choices=["Continue"]).execute()


if __name__ == "__main__":
    main()
