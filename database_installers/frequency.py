import csv
import gzip


JITEN_CSV = "jiten_freq_global.csv.gz"

# The app samples assessment bands and breaks search ties from this rank; past ~30k
# words the gains are negligible and every ranked row costs bytes in the shipped DB.
MAX_RANK = 30000


def _hiragana_to_katakana(text):
    return ''.join(chr(ord(c) + 0x60) if 'ぁ' <= c <= 'ゖ' else c for c in text)


def _is_kana(text):
    return all('ぁ' <= c <= 'ゖ' or 'ァ' <= c <= 'ヺ' or c == 'ー' for c in text)


def _load_entry_index(cursor):
    """Index senses by (term, reading) and usually-kana senses by reading, with JMdict priority.

    Priority is taken per matched pair, not per entry: 彼方 is common as かなた, which
    must not make it outrank 貴方 for the reading あなた.
    """
    entries = {}
    by_reading = {}
    cursor.execute('SELECT sequence, term, reading, pos, frequency FROM senses')
    for sequence, term, reading, pos, jmdict_priority in cursor.fetchall():
        indexes = [entries.setdefault((term, reading), {})]
        if 'uk' in (pos or '').split():
            indexes.append(by_reading.setdefault(reading, {}))
        for candidates in indexes:
            candidates[sequence] = max(candidates.get(sequence, 0), jmdict_priority or 0)
    return entries, by_reading


def _resolve(index, word, form):
    entries, by_reading = index
    # Jiten writes readings in hiragana; JMdict keeps loanword-style readings in
    # katakana (眼鏡/メガネ).
    candidates = entries.get((word, form)) or entries.get((word, _hiragana_to_katakana(form)))
    # Words usually written in kana (ある, ところ) sit under a kanji headword in
    # JMdict, so a kana-only word may match on reading, but only senses tagged `uk`:
    # かみ alone could be 紙, 神 or 髪, and those rank through their kanji rows anyway.
    # A kanji word never falls back: at this list's depth a term-only match hands
    # ranks to the wrong homograph.
    if not candidates and _is_kana(word):
        candidates = by_reading.get(word)
    if not candidates:
        return None
    return max(candidates, key=lambda sequence: (candidates[sequence], -sequence))


def best_rank_per_sequence(rows, index):
    """Collapse Jiten rows onto JMdict sequences; alternate spellings keep their best rank."""
    best = {}
    unmatched = 0
    for row in rows:
        sequence = _resolve(index, row['Word'], row['Form'])
        if sequence is None:
            unmatched += 1
            continue
        rank = int(row['Rank'])
        if rank < best.get(sequence, rank + 1):
            best[sequence] = rank
    return best, unmatched


def dense_ranks(best, limit=MAX_RANK):
    """Renumber 1..limit over our entries so a band of N ranks is N dictionary entries."""
    ordered = sorted(best.items(), key=lambda item: (item[1], item[0]))[:limit]
    return [(position, sequence) for position, (sequence, _) in enumerate(ordered, start=1)]


def populate_word_frequency(cursor, conn, csv_path):
    """Set words.freq_rank from the bundled Jiten global frequency list."""
    print("  Loading Jiten frequency list...")
    index = _load_entry_index(cursor)
    with gzip.open(csv_path, 'rt', encoding='utf-8', newline='') as f:
        best, unmatched = best_rank_per_sequence(csv.DictReader(f), index)

    ranks = dense_ranks(best)
    cursor.executemany('UPDATE words SET freq_rank = ? WHERE sequence = ?', ranks)
    conn.commit()
    print(f"  Frequency: {len(best)} entries matched, {unmatched} rows unmatched, top {len(ranks)} ranked")
