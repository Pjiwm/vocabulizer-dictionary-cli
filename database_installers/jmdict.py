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


_FORM_MARKERS = {'★', 'Ⓡ', '\U0001f141', '㊒', '⛬', '⚠', '∅'}

def _is_form_annotation(text):
    """Check if a gloss is actually a form annotation (not a real meaning).
    Yomitan uses various markers: ★ (common), Ⓡ/🅁 (rare), ㊒ ⛬ ⚠ ∅ etc."""
    return bool(text and any(m in text for m in _FORM_MARKERS))


def _extract_glosses(gloss_list_raw):
    """Extract individual gloss strings from Yomitan structured content.

    The new Yomitan format wraps glosses in structured-content dicts with
    nested ul > li tags. Each li is one meaning. We extract each li separately
    to maintain individual gloss entries for search.
    """
    glosses = []

    for item in gloss_list_raw:
        if isinstance(item, str):
            text = item.strip()
            if text and not _is_form_annotation(text):
                glosses.append(text)
            continue

        if not isinstance(item, dict):
            continue

        # Try to find li items (individual meanings) in the structure
        li_items = []
        _find_li_items(item, li_items)

        if li_items:
            for li in li_items:
                text = _extract_text(li).strip()
                if text and not _is_form_annotation(text):
                    glosses.append(text)
        else:
            # Fallback: extract all text as one gloss
            text = _extract_text(item).strip()
            if text and not _is_form_annotation(text):
                glosses.append(text)

    return glosses


def _find_li_items(obj, results):
    """Recursively find all li-tagged content nodes."""
    if isinstance(obj, dict):
        if obj.get('tag') == 'li' and 'content' in obj:
            results.append(obj['content'])
            return
        if 'content' in obj:
            _find_li_items(obj['content'], results)
    elif isinstance(obj, list):
        for item in obj:
            _find_li_items(item, results)


def extract_and_populate(zip_path, extract_dir, cursor, conn):
    """Extract JMdict Yomitan zip and populate the words/senses/glosses tables."""
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

                    glosses = _extract_glosses(gloss_list_raw)

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
