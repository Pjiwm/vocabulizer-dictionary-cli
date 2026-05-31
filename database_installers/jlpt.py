import csv
import io
import re
import requests


JLPT_CSV_URLS = {
    5: "https://raw.githubusercontent.com/jamsinclair/open-anki-jlpt-decks/main/src/n5.csv",
    4: "https://raw.githubusercontent.com/jamsinclair/open-anki-jlpt-decks/main/src/n4.csv",
    3: "https://raw.githubusercontent.com/jamsinclair/open-anki-jlpt-decks/main/src/n3.csv",
    2: "https://raw.githubusercontent.com/jamsinclair/open-anki-jlpt-decks/main/src/n2.csv",
    1: "https://raw.githubusercontent.com/jamsinclair/open-anki-jlpt-decks/main/src/n1.csv",
}

# Extract the canonical JLPT level from the tags field.
# Tags contain entries like "JLPT_N5", "JLPT_N4", "JLPT_5", "JLPT_4" etc.
_JLPT_TAG_RE = re.compile(r'JLPT_N?(\d)')


def _parse_jlpt_level_from_tags(tags):
    """Extract the JLPT level from the tags string. Returns int 1-5 or None."""
    matches = _JLPT_TAG_RE.findall(tags)
    if not matches:
        return None
    # If multiple levels, pick the highest N-number (easiest level, most specific)
    # e.g. "JLPT_3 JLPT_5 JLPT_N5" → N5 is the canonical level for this word
    return max(int(m) for m in matches)


def _find_sequence(cursor, expression, reading):
    """Match a JLPT word to a JMdict sequence using 3-tier matching."""
    exprs = [e.strip() for e in expression.replace('～', '').replace('~', '').split(';') if e.strip()]
    readings = [r.strip() for r in reading.split(';') if r.strip()]

    # Tier 1: exact term + reading
    for expr in exprs:
        for rd in readings:
            cursor.execute(
                'SELECT DISTINCT sequence FROM senses WHERE term = ? AND reading = ? LIMIT 1',
                (expr, rd)
            )
            row = cursor.fetchone()
            if row:
                return row[0]

    # Tier 2: term only
    for expr in exprs:
        cursor.execute('SELECT DISTINCT sequence FROM senses WHERE term = ? LIMIT 1', (expr,))
        row = cursor.fetchone()
        if row:
            return row[0]

    # Tier 3: reading only (for kana words stored with kanji terms in JMdict)
    for rd in readings:
        cursor.execute('SELECT DISTINCT sequence FROM senses WHERE reading = ? LIMIT 1', (rd,))
        row = cursor.fetchone()
        if row:
            return row[0]

    return None


def populate_word_jlpt(cursor, conn):
    """Download JLPT word lists and set jlpt_level on the words table."""
    print("  Downloading JLPT word lists...")

    total_matched = 0
    total_unmatched = 0

    for level in [5, 4, 3, 2, 1]:
        url = JLPT_CSV_URLS[level]
        response = requests.get(url)
        response.raise_for_status()

        reader = csv.DictReader(io.StringIO(response.text))
        matched = 0
        unmatched = 0

        for row in reader:
            expression = row['expression'].strip()
            reading = row['reading'].strip()
            jlpt = _parse_jlpt_level_from_tags(row['tags'])
            if jlpt is None:
                jlpt = level  # fallback to file-level

            seq = _find_sequence(cursor, expression, reading)
            if seq:
                # Only set if not already set to a harder level (lower number = harder)
                cursor.execute(
                    'UPDATE words SET jlpt_level = ? WHERE sequence = ? AND (jlpt_level IS NULL OR jlpt_level > ?)',
                    (jlpt, seq, jlpt)
                )
                matched += 1
            else:
                unmatched += 1

        total_matched += matched
        total_unmatched += unmatched
        print(f"    N{level}: {matched} matched, {unmatched} unmatched")

    conn.commit()
    print(f"  JLPT word data: {total_matched} matched, {total_unmatched} unmatched")
