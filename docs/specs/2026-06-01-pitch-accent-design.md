# Pitch Accent Integration - Design Spec

**Date:** 2026-06-01
**Branch:** feature/pitch-accent (CLI + app)
**Scope:** CLI dictionary build pipeline + app licensing/credits

## Summary

Add pitch accent data to dictionary entries by extracting accent values from UniDic via fugashi at build time. Store the downstep mora position per sense entry. Update licensing in both repos.

## Schema

Add `pitch_accent TEXT` column to the `senses` table in `DictionaryInstaller.create_tables()`.

- Stores the downstep mora position from UniDic's `aType` field
- "0" = heiban (flat), "1" = atamadaka, "2" = nakadaka after 2nd mora, etc.
- Multiple accent variants stored comma-separated (e.g., "0,3")
- NULL = no accent data available

## Pitch Accent Installer

New file: `database_installers/pitch_accent.py`

Function: `populate_pitch_accent(cursor, conn)`

**Flow:**
1. Import fugashi, initialize Tagger with UniDic
2. Check UniDic is installed; print clear error message if not
3. Query all distinct (term, reading) pairs from senses
4. For each pair, tokenize the term with fugashi
5. Read aType from the tokenizer output:
   - Single morpheme: take its aType directly
   - Multiple morphemes: take aType from the first content morpheme
   - Unexpected splits or missing aType: skip (NULL remains)
6. UPDATE senses SET pitch_accent = aType WHERE term = ? AND reading = ?
7. Print stats: total pairs, matched, unmatched

## Pipeline Integration

In `src/main.py`, pitch accent runs after JLPT population, before final stats:

```python
jlpt.populate_word_jlpt(cursor, conn)
pitch_accent.populate_pitch_accent(cursor, conn)
# Print stats...
```

## Dependencies

Add `fugashi[unidic]` to `requirements.txt`.

First-time setup requires: `python -m unidic download` (~500MB).

## Licensing

### CLI repo (vocabulizer-dictionary-cli)

Add UniDic section to `THIRD_PARTY_LICENSES.md`:
- Source: NINJAL (National Institute for Japanese Language and Linguistics)
- License: BSD 3-Clause (elected from GPL/LGPL/BSD triple license)
- Full BSD license text with NINJAL copyright

### App repo (vocab-grinder)

Add same UniDic section to `THIRD_PARTY_LICENSES.md`.

Add Settings credit line:
- JA: ピッチアクセントデータはUniDic (NINJAL) を使用しています
- EN: Pitch accent data from UniDic (NINJAL)

## What stays unchanged

- JMdict installer, KANJIDIC installer, JLPT installer: no changes
- Kanji table: no pitch accent (kanji readings have accent but it's per-word, not per-character)
- App dictionary search/display: separate ticket for showing pitch accent in the UI
