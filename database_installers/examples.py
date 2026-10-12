import bz2
import re
import tarfile

# Headword runs until the first of ( [ { or ~ , the markers for reading, sense,
# surface form, and the good-example flag respectively.
_HEADWORD = re.compile(r"^([^(\[{~]+)")


def create_tables(cursor, conn):
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sentences (
            id INTEGER PRIMARY KEY,
            jp TEXT NOT NULL,
            en TEXT NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS word_examples (
            base_form TEXT NOT NULL,
            sentence_id INTEGER NOT NULL REFERENCES sentences(id),
            is_good INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (base_form, sentence_id)
        )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_we_base ON word_examples(base_form)')
    conn.commit()
    print("Examples tables created.")


def parse_index_line(text):
    """Parse a jpn_indices index line into a list of (base_form, is_good).

    Tokens are space-separated: headword(reading)[sense]{surface}~.
    Only the headword and a trailing ~ matter; reading, sense, and surface are
    stripped. A trailing ~ marks the sentence as a good example of that word.
    """
    result = []
    for token in text.split():
        match = _HEADWORD.match(token)
        if not match:
            continue
        headword = match.group(1)
        result.append((headword, "~" in token))
    return result


def _read_index_csv(indices_tar):
    """Return the decoded jpn_indices.csv text from the .tar.bz2 archive."""
    with tarfile.open(indices_tar, "r:bz2") as tar:
        member = next(m for m in tar.getmembers() if m.name.endswith("jpn_indices.csv"))
        with tar.extractfile(member) as f:
            return f.read().decode("utf-8")


def _iter_index_rows(indices_tar):
    """Yield (jp_id, en_id, index_text) per jpn_indices row.

    Rows with a non-numeric id column are skipped rather than aborting the build.
    """
    for line in _read_index_csv(indices_tar).splitlines():
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        try:
            yield int(parts[0]), int(parts[1]), parts[2]
        except ValueError:
            continue


def _load_jp_sentences(path):
    """id -> JP text, from the bz2 jpn_sentences tsv (id, lang, text)."""
    mapping = {}
    with bz2.open(path, "rt", encoding="utf-8") as f:
        for line in f:
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 3:
                continue
            try:
                mapping[int(parts[0])] = parts[2]
            except ValueError:
                continue
    return mapping


def _needed_en_ids(indices_tar):
    """Set of EN sentence ids referenced by jpn_indices."""
    return {en_id for _, en_id, _ in _iter_index_rows(indices_tar)}


def _load_en_sentences(path, wanted_ids):
    """id -> EN text, keeping only ids in wanted_ids, from the bz2 eng tsv."""
    mapping = {}
    with bz2.open(path, "rt", encoding="utf-8") as f:
        for line in f:
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 3:
                continue
            try:
                sid = int(parts[0])
            except ValueError:
                continue
            if sid in wanted_ids:
                mapping[sid] = parts[2]
    return mapping


def extract_and_populate(indices_tar, jpn_tsv, eng_tsv, cursor, conn):
    """Build sentences + word_examples from the three Tatoeba sources."""
    print("  Loading JP sentences...")
    jp_map = _load_jp_sentences(jpn_tsv)
    print(f"  JP sentences: {len(jp_map)}")

    print("  Collecting referenced EN ids...")
    en_ids = _needed_en_ids(indices_tar)
    print("  Loading EN sentences...")
    en_map = _load_en_sentences(eng_tsv, en_ids)
    print(f"  EN sentences: {len(en_map)}")

    print("  Indexing sentences by base form...")
    sentence_rows = 0
    example_rows = 0
    for jp_id, en_id, index_text in _iter_index_rows(indices_tar):
        jp = jp_map.get(jp_id)
        en = en_map.get(en_id)
        # An index row is only useful when both sides of the pair resolve.
        if jp is None or en is None:
            continue
        cursor.execute(
            "INSERT OR IGNORE INTO sentences (id, jp, en) VALUES (?, ?, ?)",
            (jp_id, jp, en),
        )
        sentence_rows += 1
        for base_form, is_good in parse_index_line(index_text):
            cursor.execute(
                "INSERT OR IGNORE INTO word_examples (base_form, sentence_id, is_good) "
                "VALUES (?, ?, ?)",
                (base_form, jp_id, 1 if is_good else 0),
            )
            example_rows += 1

    conn.commit()
    print(f"  Inserted {sentence_rows} sentences, {example_rows} word-example rows.")
