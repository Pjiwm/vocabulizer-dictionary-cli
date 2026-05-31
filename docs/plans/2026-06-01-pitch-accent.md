# Pitch Accent Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add pitch accent data (downstep mora position) to dictionary entries by extracting aType values from UniDic via fugashi at build time.

**Architecture:** New `pitch_accent.py` installer module follows the same pattern as `jlpt.py`. It queries all distinct (term, reading) pairs from senses, tokenizes each with fugashi, reads the aType field, and updates a new `pitch_accent` column on the senses table. Licensing updates in both the CLI and app repos.

**Tech Stack:** Python, fugashi, unidic, SQLite

---

## File Structure

| File | Repo | Action | Responsibility |
|------|------|--------|---------------|
| `database_installers/dictionaryinstaller.py` | CLI | Modify | Add `pitch_accent TEXT` column to senses table |
| `database_installers/pitch_accent.py` | CLI | Create | Extract aType from UniDic, update senses |
| `src/main.py` | CLI | Modify | Import and call pitch_accent step, add pitch stat |
| `requirements.txt` | CLI | Modify | Add fugashi[unidic] |
| `THIRD_PARTY_LICENSES.md` | CLI | Create | Add UniDic BSD attribution |
| `THIRD_PARTY_LICENSES.md` | App | Modify | Add UniDic BSD attribution |
| `src/locales/ja.json` | App | Modify | Add credits_unidic key |
| `src/locales/en.json` | App | Modify | Add credits_unidic key |
| `src/components/Settings.jsx` | App | Modify | Add UniDic credits line |

---

### Task 1: Add pitch_accent column to schema

**Files:**
- Modify: `database_installers/dictionaryinstaller.py:29-38`

- [ ] **Step 1: Add pitch_accent column to senses table**

In `create_tables()`, add `pitch_accent TEXT` to the senses CREATE TABLE statement. Change lines 29-38 from:

```python
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS senses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sequence INTEGER NOT NULL REFERENCES words(sequence),
                term TEXT NOT NULL,
                reading TEXT NOT NULL,
                pos TEXT,
                frequency INTEGER DEFAULT 0,
                translation TEXT
            )
        ''')
```

To:

```python
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS senses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sequence INTEGER NOT NULL REFERENCES words(sequence),
                term TEXT NOT NULL,
                reading TEXT NOT NULL,
                pos TEXT,
                frequency INTEGER DEFAULT 0,
                translation TEXT,
                pitch_accent TEXT
            )
        ''')
```

- [ ] **Step 2: Commit**

```bash
git add database_installers/dictionaryinstaller.py
git commit -m "feat: add pitch_accent column to senses table schema"
```

---

### Task 2: Add fugashi dependency

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: Add fugashi[unidic] to requirements.txt**

```
inquirerpy==0.3.4
requests==2.32.3
tqdm==4.66.5
fugashi[unidic]
```

- [ ] **Step 2: Install and download UniDic**

```bash
pip install fugashi[unidic]
python -m unidic download
```

- [ ] **Step 3: Verify fugashi works**

```bash
python -c "import fugashi; tagger = fugashi.Tagger(); print([w.surface for w in tagger('食べる')])"
```

Expected: `['食べる']` (or `['食べ', 'る']` depending on UniDic version)

- [ ] **Step 4: Commit**

```bash
git add requirements.txt
git commit -m "feat: add fugashi[unidic] dependency for pitch accent"
```

---

### Task 3: Create pitch accent installer module

**Files:**
- Create: `database_installers/pitch_accent.py`

- [ ] **Step 1: Create pitch_accent.py**

```python
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

    # Single token — take its accent directly
    if len(words) == 1:
        return _get_atype(words[0])

    # Multi-token — find first content morpheme (not a particle/auxiliary/suffix)
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
```

- [ ] **Step 2: Test the module manually**

```bash
python -c "
import fugashi
t = fugashi.Tagger()
words = t('食べる')
for w in words:
    print(f'{w.surface}: aType={getattr(w.feature, \"aType\", \"N/A\")}')
"
```

This confirms aType is accessible on your UniDic version. Expected output includes an `aType` value (e.g., "2" for 食べる).

- [ ] **Step 3: Commit**

```bash
git add database_installers/pitch_accent.py
git commit -m "feat: create pitch accent installer module"
```

---

### Task 4: Wire pitch accent into build pipeline

**Files:**
- Modify: `src/main.py:13` (imports)
- Modify: `src/main.py:144-157` (pipeline steps + stats)

- [ ] **Step 1: Add import**

At line 13, after the existing installer imports:

```python
from database_installers import jmdict, kanjidic, jlpt
```

Change to:

```python
from database_installers import jmdict, kanjidic, jlpt, pitch_accent
```

- [ ] **Step 2: Add pitch accent step after JLPT**

After line 144 (`jlpt.populate_word_jlpt(cursor, conn)`), add:

```python
    # Populate pitch accent from UniDic
    pitch_accent.populate_pitch_accent(cursor, conn)
```

- [ ] **Step 3: Add pitch accent stat to printout**

After line 154 (`jlpt_count = cursor.fetchone()[0]`), add:

```python
    cursor.execute('SELECT COUNT(DISTINCT term || reading) FROM senses WHERE pitch_accent IS NOT NULL')
    pitch_count = cursor.fetchone()[0]
```

And update the print statements (currently lines 155-157) to include pitch count:

```python
    print(f"\n  Database: {db_file_name}")
    print(f"  Words: {word_count}, Senses: {sense_count}, Kanji: {kanji_count}")
    print(f"  Words with JLPT: {jlpt_count}, With pitch accent: {pitch_count}\n")
```

- [ ] **Step 4: Test full build**

```bash
cd dictionary_builders
python src/main.py
```

Select "Japanese - English" and build. Verify:
- No errors during pitch accent step
- Stats show a non-zero pitch accent count
- Spot-check the DB:

```bash
python -c "
import sqlite3
conn = sqlite3.connect('db_files/Japanese_English.db')
c = conn.cursor()
c.execute('SELECT term, reading, pitch_accent FROM senses WHERE pitch_accent IS NOT NULL LIMIT 10')
for row in c.fetchall():
    print(row)
conn.close()
"
```

- [ ] **Step 5: Commit**

```bash
git add src/main.py
git commit -m "feat: wire pitch accent into dictionary build pipeline"
```

---

### Task 5: Licensing - CLI repo

**Files:**
- Create: `THIRD_PARTY_LICENSES.md`

- [ ] **Step 1: Create THIRD_PARTY_LICENSES.md**

```markdown
# Third-Party Licenses and Attributions

This tool builds dictionary databases from the following third-party data
sources. The output .db files are derivative works of this data and are
subject to their respective licenses.

---

## JMdict / EDICT

**Source:** Electronic Dictionary Research and Development Group (EDRDG)
**URL:** https://www.edrdg.org/jmdict/j_jmdict.html
**License:** Creative Commons Attribution-ShareAlike 3.0 Unported (CC BY-SA 3.0)

This tool uses the JMdict/EDICT dictionary file, which is the property of
the Electronic Dictionary Research and Development Group (EDRDG) and is
used in conformance with the Group's licence.

---

## KANJIDIC2

**Source:** Electronic Dictionary Research and Development Group (EDRDG)
**URL:** https://www.edrdg.org/wiki/index.php/KANJIDIC_Project
**License:** Creative Commons Attribution-ShareAlike 3.0 Unported (CC BY-SA 3.0)

This tool uses the KANJIDIC2 dictionary file, which is the property of
the Electronic Dictionary Research and Development Group (EDRDG) and is
used in conformance with the Group's licence.

---

## UniDic

**Source:** National Institute for Japanese Language and Linguistics (NINJAL)
**URL:** https://clrd.ninjal.ac.jp/unidic/
**License:** BSD 3-Clause (elected from GPL/LGPL/BSD triple license)

Used for pitch accent (aType) data extraction.

Copyright (c) 2011-2021, The UniDic Consortium. All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice,
   this list of conditions and the following disclaimer.
2. Redistributions in binary form must reproduce the above copyright
   notice, this list of conditions and the following disclaimer in the
   documentation and/or other materials provided with the distribution.
3. Neither the name of the copyright holder nor the names of its
   contributors may be used to endorse or promote products derived from
   this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
"AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
```

Note: This file includes the JMdict/KANJIDIC sections from the feature/licensing branch. If that branch has been merged before this task runs, modify the existing file instead of creating it - just add the UniDic section.

- [ ] **Step 2: Commit**

```bash
git add THIRD_PARTY_LICENSES.md
git commit -m "feat: add THIRD_PARTY_LICENSES with UniDic BSD attribution"
```

---

### Task 6: Licensing - App repo

**Files (in /home/pjiwm/dev/vocab-grinder):**
- Modify: `THIRD_PARTY_LICENSES.md`
- Modify: `src/locales/ja.json`
- Modify: `src/locales/en.json`
- Modify: `src/components/Settings.jsx`

- [ ] **Step 1: Add UniDic section to THIRD_PARTY_LICENSES.md**

Append after the IPADIC section:

```markdown

---

## UniDic

**Source:** National Institute for Japanese Language and Linguistics (NINJAL)
**URL:** https://clrd.ninjal.ac.jp/unidic/
**License:** BSD 3-Clause (elected from GPL/LGPL/BSD triple license)

Pitch accent data extracted from UniDic at dictionary build time.

Copyright (c) 2011-2021, The UniDic Consortium. All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice,
   this list of conditions and the following disclaimer.
2. Redistributions in binary form must reproduce the above copyright
   notice, this list of conditions and the following disclaimer in the
   documentation and/or other materials provided with the distribution.
3. Neither the name of the copyright holder nor the names of its
   contributors may be used to endorse or promote products derived from
   this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
"AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
```

- [ ] **Step 2: Add i18n key to ja.json**

After `settings.credits_ipadic` (line 308), add:

```json
	"settings.credits_unidic": "ピッチアクセントデータはUniDic (NINJAL) を使用しています",
```

- [ ] **Step 3: Add i18n key to en.json**

After `settings.credits_ipadic`, add:

```json
	"settings.credits_unidic": "Pitch accent data from UniDic (NINJAL)",
```

- [ ] **Step 4: Add credits line to Settings.jsx**

After the IPADIC credits paragraph (around line 605-607), add:

```jsx
							<p class="mt-1">
								{t("settings.credits_unidic")}
							</p>
```

- [ ] **Step 5: Build app to verify**

```bash
npm run build
```

Expected: Clean build.

- [ ] **Step 6: Commit**

```bash
git add THIRD_PARTY_LICENSES.md src/locales/ja.json src/locales/en.json src/components/Settings.jsx
git commit -m "feat: add UniDic BSD attribution and Settings credit line"
```

---

## Self-Review

- **Spec coverage:** Schema change (Task 1), installer module (Task 3), pipeline integration (Task 4), dependencies (Task 2), CLI licensing (Task 5), app licensing (Task 6) - all spec sections covered.
- **Placeholder scan:** No TBDs. All code blocks are complete. Task 5 has a note about merge order with feature/licensing but provides the full file content either way.
- **Type consistency:** `pitch_accent` column name used consistently across schema (Task 1), installer UPDATE (Task 3), and stats query (Task 4). `populate_pitch_accent(cursor, conn)` signature matches between Task 3 (definition) and Task 4 (call site). `_extract_accent` and `_get_atype` are internal to Task 3.
