import gzip


def extract_and_populate(path, extract_dir, cursor, conn):
    """Parse RADKFILE (EUC-JP, gzipped) into the radical + kanji_radical tables.

    RADKFILE format:
        - Lines starting with "#" are comments.
        - A line "$ <radical> <strokes> [image]" starts a radical block.
        - Subsequent non-comment lines list the kanji that contain that radical.

    extract_dir is accepted to match the other installers' signature but is
    unused: RADKFILE is a single gzipped file, not an archive.
    """
    print(f"Parsing RADKFILE from {path}")

    opener = gzip.open if str(path).endswith(".gz") else open
    with opener(path, "rt", encoding="euc-jp") as f:
        text = f.read()

    radical = None
    radical_count = 0
    pair_count = 0
    for line in text.splitlines():
        if not line or line.startswith("#"):
            continue
        if line.startswith("$"):
            parts = line.split()
            # parts[0] == "$", parts[1] == radical glyph, parts[2] == stroke count
            radical = parts[1]
            strokes = int(parts[2])
            cursor.execute(
                "INSERT OR REPLACE INTO radical (radical, strokes) VALUES (?, ?)",
                (radical, strokes),
            )
            radical_count += 1
        elif radical is not None:
            for ch in line.strip():
                cursor.execute(
                    "INSERT OR IGNORE INTO kanji_radical (character, radical) VALUES (?, ?)",
                    (ch, radical),
                )
                pair_count += 1

    conn.commit()
    print(
        f"RADKFILE data populated: {radical_count} radicals, {pair_count} kanji-radical pairs."
    )
