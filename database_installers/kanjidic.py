import json
import os
import zipfile


def extract_and_populate(zip_path, extract_dir, cursor, conn):
    """Extract KANJIDIC Yomitan zip and populate the kanji table.

    Yomitan kanji_bank format (per entry):
        [0] character    - Kanji character (e.g. "食")
        [1] onyomi       - Space-separated on'yomi readings
        [2] kunyomi      - Space-separated kun'yomi readings
        [3] tags         - Space-separated tags
        [4] meanings     - Array of meaning strings
        [5] stats        - Object with stroke_count, grade, jlpt, freq, etc.
    """
    print(f"Extracting {zip_path} to {extract_dir}")
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_dir)
    print("Extraction complete.")

    print(f"Populating KANJIDIC data from {extract_dir}")
    count = 0
    for json_file in sorted(os.listdir(extract_dir)):
        if json_file.startswith('kanji_bank_') and json_file.endswith('.json'):
            file_path = os.path.join(extract_dir, json_file)
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                print(f"  {json_file}: {len(data)} entries")

                for entry in data:
                    if len(entry) < 6:
                        continue

                    character = entry[0]
                    readings_on = entry[1]   # space-separated
                    readings_kun = entry[2]  # space-separated
                    # entry[3] = tags (not stored separately)
                    meanings_list = entry[4]  # array of strings
                    stats = entry[5]          # dict with stroke_count, grade, jlpt, freq

                    meanings = ', '.join(meanings_list) if meanings_list else ''

                    # Extract stats — keys vary but common ones are:
                    # "strokes", "grade", "jlpt", "freq"
                    stroke_count = None
                    grade = None
                    jlpt_level = None

                    if isinstance(stats, dict):
                        # Try common key names
                        for key in ('strokes', 'stroke_count'):
                            if key in stats:
                                try:
                                    stroke_count = int(stats[key])
                                except (ValueError, TypeError):
                                    pass
                                break
                        for key in ('grade',):
                            if key in stats:
                                try:
                                    grade = int(stats[key])
                                except (ValueError, TypeError):
                                    pass
                                break
                        for key in ('jlpt', 'jlpt_level'):
                            if key in stats:
                                try:
                                    jlpt_level = int(stats[key])
                                except (ValueError, TypeError):
                                    pass
                                break

                    cursor.execute(
                        '''
                        INSERT OR REPLACE INTO kanji
                        (character, stroke_count, grade, jlpt_level, meanings, readings_on, readings_kun)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        ''',
                        (character, stroke_count, grade, jlpt_level, meanings, readings_on, readings_kun)
                    )
                    count += 1

    conn.commit()
    print(f"KANJIDIC data populated: {count} kanji entries.")
