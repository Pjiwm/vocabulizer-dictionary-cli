import json
import sys
from dictionaryinstaller import DictionaryInstaller


class JMdictInstaller(DictionaryInstaller):
    def populate_db(self, cursor, conn):
        print(f"Populating database from {self.downloaded_file}")
        with open(self.downloaded_file, 'r', encoding='utf-8') as f:
            entry_count = 0
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    term = entry.get("word", "")
                    pos = entry.get("pos", "")
                    frequency = 1
                    reading = entry.get("sounds", [{}])[0].get(
                        "ipa", "")

                    gloss_list = []
                    for sense in entry.get("senses", []):
                        gloss_list.extend(sense.get("glosses", []))

                    translation = ', '.join(gloss_list) if gloss_list else None
                    additional_info = entry.get("etymology_text", "")
                    if " " in term:
                        print(f"Skipping multi-word term: {term}")
                        continue

                    if term and pos and translation:
                        cursor.execute(
                            '''
                            INSERT INTO entries (term, reading, pos, frequency, translation, additional_info)
                            VALUES (?, ?, ?, ?, ?, ?)
                            ''',
                            (term, reading, pos, frequency,
                             translation, additional_info)
                        )
                        entry_count += 1
                except Exception:
                    print("Skipped entry due to missing fields")

        conn.commit()
        print(f"Database populated with {entry_count} entries.")


if __name__ == "__main__":
    if len(sys.argv) == 3:
        downloaded_file = sys.argv[1]
        db_file_name = sys.argv[2]
        installer = JMdictInstaller(downloaded_file, db_file_name)
        installer.run()
    else:
        print("Usage: python kaikki_french.py <downloaded_file> <db_file_name>")
