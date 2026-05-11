import json
import os
import sys
import zipfile
from dictionaryinstaller import DictionaryInstaller


class JMdictInstaller(DictionaryInstaller):
    def extract_files(self):
        print(f"Extracting {self.downloaded_file} to {self.extract_dir}")
        with zipfile.ZipFile(self.downloaded_file, 'r') as zip_ref:
            zip_ref.extractall(self.extract_dir)
        print("Extraction complete.")

    def populate_db(self, cursor, conn):
        print(f"Populating database from {self.extract_dir}")
        for json_file in sorted(os.listdir(self.extract_dir)):
            if json_file.startswith('term_bank_') and json_file.endswith('.json'):
                file_path = os.path.join(self.extract_dir, json_file)
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    print(f"Loaded {len(data)} entries from {json_file}")

                    for entry in data:
                        if len(entry) >= 8:
                            term = entry[0]
                            reading = entry[1]
                            pos = entry[2]
                            frequency = entry[4]
                            gloss_list = entry[5]
                            sequence = entry[6]

                            cursor.execute(
                                'INSERT OR IGNORE INTO words (sequence) VALUES (?)',
                                (sequence,)
                            )

                            translation = ', '.join(gloss_list)

                            cursor.execute(
                                '''
                                INSERT INTO senses (sequence, term, reading, pos, frequency, translation)
                                VALUES (?, ?, ?, ?, ?, ?)
                                ''',
                                (sequence, term, reading, pos, frequency, translation)
                            )
                            sense_id = cursor.lastrowid
                            for gpos, gloss in enumerate(gloss_list):
                                cursor.execute(
                                    'INSERT INTO glosses (sense_id, gloss, position) VALUES (?, ?, ?)',
                                    (sense_id, gloss, gpos)
                                )
                        else:
                            print(f"Skipping malformed entry: {entry}")

        conn.commit()
        print("Database populated.")


if __name__ == "__main__":
    if len(sys.argv) == 3:
        downloaded_file = sys.argv[1]
        db_file_name = sys.argv[2]
        installer = JMdictInstaller(downloaded_file, db_file_name)
        installer.steps = [installer.extract_files]
        installer.run()
    else:
        print("Usage: python jmdict.py <downloaded_file> <db_file_name>")
