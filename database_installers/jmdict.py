import json
import os
import zipfile


def _extract_text(obj):
    """Recursively extract plain text from Yomitan structured content."""
    if isinstance(obj, str):
        return obj
    if isinstance(obj, list):
        parts = [_extract_text(item) for item in obj]
        return ' '.join(p for p in parts if p).strip()
    if isinstance(obj, dict):
        if 'content' in obj:
            return _extract_text(obj['content'])
    return ''


def extract_and_populate(zip_path, extract_dir, cursor, conn):
    """Extract JMdict Yomitan zip and populate the words/senses/glosses tables.

    Handles both legacy format (glosses as plain strings) and modern
    Yomitan format (glosses as structured content dicts).
    """
    print(f"Extracting {zip_path} to {extract_dir}")
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_dir)
    print("Extraction complete.")

    print(f"Populating JMdict data from {extract_dir}")
    for json_file in sorted(os.listdir(extract_dir)):
        if json_file.startswith('term_bank_') and json_file.endswith('.json'):
            file_path = os.path.join(extract_dir, json_file)
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                print(f"  {json_file}: {len(data)} entries")

                for entry in data:
                    if len(entry) < 7:
                        continue

                    term = entry[0]
                    reading = entry[1]
                    pos = entry[2]
                    frequency = entry[4]
                    gloss_list_raw = entry[5]
                    sequence = entry[6]

                    # Extract plain text from each gloss (may be str or dict)
                    glosses = []
                    for g in gloss_list_raw:
                        if isinstance(g, str):
                            text = g.strip()
                        else:
                            text = _extract_text(g).strip()
                        if text:
                            glosses.append(text)

                    if not glosses:
                        continue

                    cursor.execute(
                        'INSERT OR IGNORE INTO words (sequence) VALUES (?)',
                        (sequence,)
                    )

                    translation = ', '.join(glosses)

                    cursor.execute(
                        '''
                        INSERT INTO senses (sequence, term, reading, pos, frequency, translation)
                        VALUES (?, ?, ?, ?, ?, ?)
                        ''',
                        (sequence, term, reading, pos, frequency, translation)
                    )
                    sense_id = cursor.lastrowid
                    for gpos, gloss in enumerate(glosses):
                        cursor.execute(
                            'INSERT INTO glosses (sense_id, gloss, position) VALUES (?, ?, ?)',
                            (sense_id, gloss, gpos)
                        )

    conn.commit()
    print("JMdict data populated.")
