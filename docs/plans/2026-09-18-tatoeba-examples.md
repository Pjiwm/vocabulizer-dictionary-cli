# Tatoeba example-sentence builder: implementation plan

Spec: `docs/specs/2026-09-18-tatoeba-examples-design.md`

**Goal:** Emit a standalone `examples.db` of Tatoeba JP/EN sentence pairs indexed
by word base form, built from a new menu path in this CLI.

**Approach:** New standalone container `examples.db`, a new `examples.py`
installer keeping the existing parse-into-cursor seam, and a `build_examples()`
path in `main.py` beside `build_dictionary`. Indexing reuses `jpn_indices`.

**Tech:** Python stdlib only (`sqlite3`, `tarfile`, `bz2`), plus the existing
`requests` / `tqdm` / `InquirerPy`. No new dependencies. No test suite
(verification is by build counts and a sample lookup, per decision).

## Workflow notes

This follows the collaborator workflow, not autonomous execution:

- One chunk at a time, skeleton before fill. Stop after each for review.
- The assistant writes code; the developer runs the build/verify commands and
  implements the crux (`parse_index_line`).
- No commits unless the developer asks, and never with a co-author trailer.
- Each chunk opens with a seam question tying it to the previous piece.

## File map

- `src/links.json`: add a `tatoeba` source block (URLs, filenames). Modify.
- `database_installers/examples.py`: new. Schema + loaders + insert loop +
  the `parse_index_line` crux (developer-owned).
- `src/main.py`: add `build_examples()` and a menu entry. Modify.
- `THIRD_PARTY_LICENSES.md`, `README.md`: Tatoeba attribution. Modify.

## Source files (Tatoeba)

Base: `https://downloads.tatoeba.org/exports/`

- `jpn_indices.tar.bz2` -> extract `jpn_indices.csv`. Columns:
  JP id `\t` EN id `\t` index text.
- `per_language/jpn/jpn_sentences.tsv.bz2` -> rows `id \t lang \t text`.
- `per_language/eng/eng_sentences.tsv.bz2` -> rows `id \t lang \t text`.

`.tar.bz2` needs `tarfile`; `.tsv.bz2` is a plain bzip2 stream needing `bz2`.

---

## Chunk 1: source config in links.json

**Why:** URLs belong with the other source config, not hard-coded in a build
function, matching how the dictionaries are configured. Small, isolated diff.

**Files:** Modify `src/links.json`.

Add a top-level sibling to `dictionaries`:

```json
"tatoeba": {
    "name": "Example Sentences (Tatoeba)",
    "indices_url": "https://downloads.tatoeba.org/exports/jpn_indices.tar.bz2",
    "indices_file": "jpn_indices.tar.bz2",
    "jpn_sentences_url": "https://downloads.tatoeba.org/exports/per_language/jpn/jpn_sentences.tsv.bz2",
    "jpn_sentences_file": "jpn_sentences.tsv.bz2",
    "eng_sentences_url": "https://downloads.tatoeba.org/exports/per_language/eng/eng_sentences.tsv.bz2",
    "eng_sentences_file": "eng_sentences.tsv.bz2",
    "dbFileName": "examples.db"
}
```

**Review checkpoint.** Seam question for next chunk: `main.py` reads
`data["dictionaries"]` today; where does it now read the `tatoeba` block, and who
owns opening the `examples.db` connection, `main.py` or `examples.py`?

---

## Chunk 2: examples.py skeleton (C3)

**Why:** Lock the shape before any bodies. Same seam as `radkfile.py`
(parse source, write through `cursor`/`conn`), but this module owns its schema
because it does not share `DictionaryInstaller.create_tables`. Reviewing the
skeleton alone means the structure is agreed before logic lands.

**Files:** Create `database_installers/examples.py`.

Skeleton (signatures, schema, docstrings; bodies are stubs except the schema):

```python
import bz2
import tarfile


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
    stripped. A trailing ~ sets is_good True for that token.
    """
    raise NotImplementedError  # developer-owned crux, filled in Chunk 5


def _load_jp_sentences(path):
    """id -> JP text, from the bz2 jpn_sentences tsv."""
    raise NotImplementedError


def _needed_en_ids(indices_path):
    """Set of EN sentence ids referenced by jpn_indices."""
    raise NotImplementedError


def _load_en_sentences(path, wanted_ids):
    """id -> EN text, keeping only ids in wanted_ids, from the bz2 eng tsv."""
    raise NotImplementedError


def extract_and_populate(indices_tar, jpn_tsv, eng_tsv, cursor, conn):
    """Build sentences + word_examples from the three Tatoeba sources."""
    raise NotImplementedError
```

**Review checkpoint.** Seam question: `extract_and_populate` takes three source
paths rather than one `extract_dir` like the siblings. Why does that break the
shared signature, and is that the right call?

---

## Chunk 3: main.py wiring (plumbing)

**Why:** The build path is orchestration, parallel to `build_dictionary` but not
inside it (examples are language-independent). Assistant writes this; it is
plumbing, not crux.

**Files:** Modify `src/main.py`.

Add after `build_dictionary`:

```python
def build_examples():
    """Download Tatoeba sources and build the standalone examples.db."""
    cfg = data["tatoeba"]
    print(f"\n=== Building {cfg['name']} ===\n")

    indices = download_file(cfg["name"] + " (indices)", cfg["indices_url"], cfg["indices_file"])
    jpn = download_file(cfg["name"] + " (jpn)", cfg["jpn_sentences_url"], cfg["jpn_sentences_file"])
    eng = download_file(cfg["name"] + " (eng)", cfg["eng_sentences_url"], cfg["eng_sentences_file"])
    if not (indices and jpn and eng):
        print("Failed to download Tatoeba sources. Skipping.")
        return

    db_file = DB_DIR / cfg["dbFileName"]
    DB_DIR.mkdir(exist_ok=True)
    if db_file.exists():
        db_file.unlink()

    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    examples.create_tables(cursor, conn)
    examples.extract_and_populate(indices, jpn, eng, cursor, conn)

    cursor.execute("SELECT COUNT(*) FROM sentences")
    sentence_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(DISTINCT base_form) FROM word_examples")
    base_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM word_examples WHERE is_good = 1")
    good_count = cursor.fetchone()[0]
    print(f"\n  Database: {cfg['dbFileName']}")
    print(f"  Sentences: {sentence_count}, base forms: {base_count}, good examples: {good_count}\n")

    conn.close()
    for f in (indices, jpn, eng):
        os.remove(f)
    print(f"=== {cfg['name']} complete ===\n")
```

Import: add `examples` to the `from database_installers import ...` line.

Menu: insert a `cfg["name"]` choice (Example Sentences (Tatoeba)) into the
`choices` list, and dispatch it to `build_examples()`. Include it in Build All.

**Review checkpoint.** Command for the developer to run once bodies exist
(Chunk 4/5), not yet:
`python src/main.py` then select "Example Sentences (Tatoeba)".

---

## Chunk 4: loaders + insert loop (C4 fill, assistant)

**Why:** Fill the plumbing bodies now that the shape is reviewed. Two-pass over
`jpn_indices` so the EN map holds only referenced ids (decision 4).

**Files:** Modify `database_installers/examples.py`.

`_load_jp_sentences` and `_load_en_sentences` read `id \t lang \t text` from the
bz2 stream; `_needed_en_ids` reads column 2 of `jpn_indices.csv`;
`extract_and_populate` opens the `.tar.bz2`, extracts `jpn_indices.csv`, then runs
the two passes, calling `parse_index_line` per row and inserting with
`INSERT OR IGNORE` into `word_examples`. Full bodies written and shown at
implementation time.

Depends on `parse_index_line`, so this chunk is reviewable but the build only
runs green once Chunk 5 lands. Order 4-before-5 keeps the crux isolated in its
own diff for the developer.

**Review checkpoint.** Seam question: `extract_and_populate` calls
`parse_index_line` for every row; what does it do with a token whose headword is
empty or malformed, and where should that guard live, in the parser or the loop?

---

## Chunk 5: parse_index_line (the crux, developer)

**Why:** This parser is the whole "which words does this sentence teach" logic.
It is the piece worth building by hand.

**Files:** Modify `database_installers/examples.py` (replace the stub).

TODO for the developer:

- Signature: `parse_index_line(text: str) -> list[tuple[str, bool]]`.
- Split `text` on spaces into tokens.
- Per token, syntax is `headword(reading)[sense]{surface}~` with every part after
  the headword optional. Extract the headword (text up to the first of
  `(`, `[`, `{`, or `~`). Detect a trailing `~` for `is_good`.
- Skip empty headwords. Reading may be kana or a numeric JMdict seq; ignore it.
- Return one `(headword, is_good)` per usable token.
- Worked line to reason against:
  `其の[01]{その} 家(いえ)[01] は 可也{かなり} ぼろ屋[01]~ になる[01]{になっている}`
  Expect base forms 其の, 家, は, 可也, ぼろ屋 (good), なる, with ぼろ屋's
  is_good True.
- Watch out for: a bare token with no brackets at all (は), and the `~` sitting
  after a bracketed group (`ぼろ屋[01]~`).

**Review checkpoint.** Then the developer runs the build:
`python src/main.py` -> "Example Sentences (Tatoeba)".

---

## Chunk 6: attribution

**Why:** CC BY 2.0 FR requires crediting the Tatoeba Project, matching the
existing EDRDG/UniDic sections.

**Files:** Modify `THIRD_PARTY_LICENSES.md`, `README.md`.

- `THIRD_PARTY_LICENSES.md`: a "Tatoeba Project / Tanaka Corpus" section, source
  `https://tatoeba.org/en/downloads`, license CC BY 2.0 FR, noting the sentence
  data and the `jpn_indices` word index. No em-dashes.
- `README.md`: one data-attribution line pointing at Tatoeba, CC BY 2.0 FR.

**Review checkpoint.** Done.

---

## Verification (developer-run)

After Chunk 5, build and sanity-check:

```bash
python src/main.py           # select "Example Sentences (Tatoeba)"
ls -lh db_files/examples.db   # record size for the app's mobile budget

sqlite3 db_files/examples.db \
  "SELECT s.jp, s.en FROM word_examples w JOIN sentences s ON s.id=w.sentence_id \
   WHERE w.base_form='物語' ORDER BY LENGTH(s.jp) ASC, w.is_good DESC LIMIT 3;"
```

Expect: non-zero counts printed by the build, `examples.db` present, and the
query returning 物語 sentences shortest-first. A nonsense base form returns nothing.

## Self-review

- Spec coverage: container (Chunk 1-3), schema (Chunk 2), indexing/crux
  (Chunk 5), build flow/loaders (Chunk 4), attribution (Chunk 6), app contract
  (recorded in spec). Covered.
- No new deps: `tarfile`/`bz2` are stdlib; no test dep (no formal tests).
- Type consistency: `create_tables`, `extract_and_populate(indices, jpn, eng,
  cursor, conn)`, `parse_index_line(text) -> list[(str, bool)]` used consistently
  across chunks and matching `main.py` calls.
