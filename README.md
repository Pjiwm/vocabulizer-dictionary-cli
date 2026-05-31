# Vocabulizer Dictionary CLI

CLI tool for building Japanese dictionary SQLite databases from JMdict/KANJIDIC source data.

## Setup

```bash
git clone https://github.com/Pjiwm/vocabulizer-dictionary-cli.git
cd vocabulizer-dictionary-cli
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Usage

```bash
python src/main.py
```

This downloads the source dictionary files and builds the SQLite .db files into `dictionary_builders/db_files/`.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## Data Attribution

The dictionary databases built by this tool use data from the
[Electronic Dictionary Research and Development Group](https://www.edrdg.org/)
(EDRDG). The JMdict/EDICT and KANJIDIC2 files are licensed under
[CC BY-SA 3.0](https://creativecommons.org/licenses/by-sa/3.0/).
The generated .db files are derivative works and inherit this license.

See [THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md) for full details.

## License

Source code is licensed under the [MIT License](LICENSE).
Dictionary data has its own licensing - see above.
