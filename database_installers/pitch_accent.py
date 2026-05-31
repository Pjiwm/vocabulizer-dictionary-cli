import fugashi


def populate_pitch_accent(cursor, conn):
    """Extract pitch accent data from UniDic and update senses table."""
    print("  Loading UniDic tagger for pitch accent...")
    try:
        tagger = fugashi.Tagger()
    except Exception as e:
        print(f"  ERROR: Could not load UniDic. Run: python -m unidic download")
        print(f"  {e}")
        return

    # Get all distinct (term, reading) pairs
    cursor.execute('SELECT DISTINCT term, reading FROM senses')
    pairs = cursor.fetchall()
    print(f"  Processing {len(pairs)} unique (term, reading) pairs...")

    matched = 0
    unmatched = 0

    for term, reading in pairs:
        accent = _extract_accent(tagger, term)
        if accent is not None:
            cursor.execute(
                'UPDATE senses SET pitch_accent = ? WHERE term = ? AND reading = ?',
                (accent, term, reading)
            )
            matched += 1
        else:
            unmatched += 1

    conn.commit()
    print(f"  Pitch accent: {matched} matched, {unmatched} unmatched")


def _extract_accent(tagger, term):
    """Tokenize a term and extract the aType (accent type) from UniDic.

    Returns the accent value as a string, or None if unavailable.
    For single-token terms, returns aType directly.
    For multi-token terms, returns the aType of the first content morpheme.
    """
    words = tagger(term)
    if not words:
        return None

    # Single token - take its accent directly
    if len(words) == 1:
        return _get_atype(words[0])

    # Multi-token - find first content morpheme (not a particle/auxiliary/suffix)
    # UniDic POS field: feature.pos1
    for word in words:
        pos1 = word.feature.pos1 if hasattr(word.feature, 'pos1') else ''
        if pos1 in ('助詞', '助動詞', '接尾辞', '記号', '補助記号', '空白'):
            continue
        accent = _get_atype(word)
        if accent is not None:
            return accent

    # Fallback: try the first token
    return _get_atype(words[0])


def _get_atype(word):
    """Extract aType from a fugashi word node. Returns string or None."""
    if hasattr(word.feature, 'aType'):
        val = word.feature.aType
        if val and val != '*':
            return val
    return None
