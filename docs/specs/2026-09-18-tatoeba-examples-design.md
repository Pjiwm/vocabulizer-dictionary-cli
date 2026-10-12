# Example sentences (Tatoeba) DB builder

Date: 2026-09-18
Status: design, awaiting review

## Goal

Add a build-time data-prep path to this CLI that emits a standalone
`examples.db` of licensed Japanese example sentences with English translations,
indexed by word base form so the app can return N example sentences for a
dictionary entry. Source: Tatoeba / Tanaka corpus (CC BY 2.0 FR).

This repo owns only the build side (ticket chunk 1). The Rust app repo owns the
repo layer, Tauri command, UI, and extension (chunks 2 to 5). This document also
records the app-side lookup contract so that repo has a spec to build against.

## Scope

In scope (this repo):

- Download Tatoeba `jpn_indices`, `jpn_sentences`, `eng_sentences`.
- Build `examples.db`: sentence pairs plus a base-form to sentence index.
- New menu entry and a standalone build path in `main.py` (not inside the
  per-language `build_dictionary` loop).
- Tatoeba attribution in `THIRD_PARTY_LICENSES.md` and `README.md`.

Out of scope (other repo or later):

- Compression to `.zst`. The app's Rust `build.rs` compresses at bundle time, so
  this repo emits a plain `examples.db`.
- The app repo layer, Tauri `get_examples` command, `DictionaryPanel` UI, and
  extension parity.
- Tatoeba audio, sentence mining into cards, non JP/EN language pairs.

## Decisions (resolved)

1. Container: `examples.db` is its own SQLite file, not new tables on the
   per-language `Japanese_*.db`. It is JP/EN only and shared across every
   language pair, so it does not belong in the per-language build loop. This is a
   container-level (C2) decision, called out rather than grown implicitly onto
   the existing installer.
2. Indexing: reuse `jpn_indices.csv`. Our build tokenizer (fugashi) would not
   match the app's Rust lexer, so tokenizing here would not give a single source
   of truth across repos. Tatoeba's precomputed index is the pragmatic choice and
   carries the good-example marker we want (see below).
3. Compression: plain `.db` emitted here; the app's `build.rs` compresses.
4. EN text source: stream `eng_sentences` and keep only the ids referenced by
   `jpn_indices`, rather than holding the full ~1M-row map.

## Source data

Base URL: `https://downloads.tatoeba.org/exports/`

- `jpn_indices.tar.bz2` -> `jpn_indices.csv`. Three tab-separated columns:
  JP sentence id, linked EN sentence id, index text. The exact pairing semantics
  are confirmed against the file during build.
- Per-language exports `per_language/jpn/jpn_sentences.tsv.bz2` and
  `per_language/eng/eng_sentences.tsv.bz2`. Each row is `id<TAB>lang<TAB>text`.

Index text token syntax (EDRDG "Sentence-Dictionary Linking"):

```
headword(reading)[sense]{surface}~
```

- headword: dictionary form. This is our lookup key.
- reading (parentheses): kana, or a numeric JMdict sequence number. Ignored for
  indexing.
- sense (square brackets): two-digit sense number. Ignored.
- surface (curly braces): the inflected form as it appears in the sentence.
  Ignored for indexing.
- trailing `~`: marks that the sentence is a good, checked example of that word's
  usage.

Worked example from the spec page:

```
其の[01]{その} 家(いえ)[01] は 可也{かなり} ぼろ屋[01]~ になる[01]{になっている}
```

License: CC BY 2.0 FR. See `https://tatoeba.org/en/downloads`.

## Architecture

### Container (C2)

A single new SQLite file `examples.db` in `db_files/`, built by a dedicated path
so it stays independent of the per-language dictionaries.

### Components (C3)

- `database_installers/examples.py`: parses the Tatoeba sources and populates the
  `examples.db` tables. Keeps the same seam as its siblings
  (`radkfile.py`, `jmdict.py`): a source-parsing function that writes through a
  `cursor`/`conn`. It differs only in that it owns a dedicated DB and creates its
  own schema, since it does not share `DictionaryInstaller.create_tables`.
- `main.py`: a new `build_examples()` function and a new menu entry
  ("Build Example Sentences"). It downloads the three sources, opens a connection
  to `examples.db`, calls into `examples.py`, prints counts, and cleans up
  downloads. It sits beside `build_dictionary`, not inside it.
- `src/links.json`: a new top-level section for the Tatoeba source URLs, so the
  URLs live with the other source config rather than hard-coded.

### Schema (examples.db)

```sql
CREATE TABLE sentences (
    id  INTEGER PRIMARY KEY,   -- Tatoeba JP sentence id; the app cites this as source_id
    jp  TEXT NOT NULL,
    en  TEXT NOT NULL
);

CREATE TABLE word_examples (
    base_form   TEXT NOT NULL,
    sentence_id INTEGER NOT NULL REFERENCES sentences(id),
    is_good     INTEGER NOT NULL DEFAULT 0,   -- the ~ good-example marker
    PRIMARY KEY (base_form, sentence_id)
);

CREATE INDEX idx_we_base ON word_examples(base_form);
```

`is_good` records the `~` verified-example marker. It is a secondary ranking
signal only: lookups sort by JP sentence length first (shorter is clearer for a
learner) and use `is_good` to break ties.

## App-side lookup contract (design note for the other repo)

The Rust repo layer should expose roughly:

```
examples_for_word(base_form: &str, limit: usize) -> Vec<Example>
Example { jp: String, en: String, source_id: i64 }
```

backed by:

```sql
SELECT s.jp, s.en, s.id
FROM word_examples w
JOIN sentences s ON s.id = w.sentence_id
WHERE w.base_form = ?
ORDER BY LENGTH(s.jp) ASC, w.is_good DESC
LIMIT ?;
```

Ranking rationale: the `~` good-example marker means "verified", not "simple". For
a dictionary example the priority is short and clear, so JP length is the primary
sort and `is_good` only breaks ties. Length is computed at query time; per-word
candidate sets are small enough that no precomputed column or index is needed.

Words with zero examples return an empty list; the UI degrades cleanly.

## Build flow

1. Download `jpn_indices`, `jpn_sentences`, `eng_sentences` via the existing
   `download_file` helper, with new `links.json` entries.
2. Load `jpn_sentences` into an id -> JP text map.
3. First pass over `jpn_indices`: collect the set of referenced EN ids.
4. Stream `eng_sentences`, keeping only text for ids in that set.
5. Second pass over `jpn_indices`: for each row, insert the sentence pair (JP id,
   JP text, EN text) into `sentences`, then parse the index text and insert one
   `word_examples` row per token.
6. Print counts (sentences, distinct base forms, good-example rows) and clean up
   downloads.

## The crux (owned by the developer)

The conceptual heart is the index-line parser, left as a TODO for the developer
to implement:

```python
def parse_index_line(text: str) -> list[tuple[str, bool]]:
    """Parse a jpn_indices index line into (base_form, is_good) per token.

    Tokens are space-separated with syntax headword(reading)[sense]{surface}~.
    Only the headword and the trailing ~ matter here: reading, sense, and
    surface are stripped. A trailing ~ sets is_good True for that token.
    """
    # TODO(developer)
```

## Division of labour

- Assistant: `links.json` entries, `main.py` wiring and `build_examples()`, the
  `examples.db` schema, the sentence loaders (JP map, filtered EN stream), the
  join and insert loop, and the attribution edits.
- Developer: `parse_index_line`, the token parser that decides which words each
  sentence teaches.

Vetoable.

## Attribution

- `THIRD_PARTY_LICENSES.md`: a Tatoeba Project section, CC BY 2.0 FR, with the
  downloads URL, matching the existing sections' shape.
- `README.md`: a short data-attribution line for Tatoeba, no em-dashes.

## Testing (to confirm with the developer)

- Lookup returns sentences for a common word (e.g. 物語), shortest first.
- A word with zero examples returns an empty result.
- Counts are non-zero and plausible after a build.
- `examples.db` size is recorded so the app can judge the mobile budget.

## Open questions

- None blocking. `examples.db` size is measured on first build and fed back into
  the app's mobile size budget.
