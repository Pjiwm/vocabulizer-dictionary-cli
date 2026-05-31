# Contributing

## Setup

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Dictionary builders

Dictionary builders live in `dictionary_builders/`. Each builder inherits from `DictionaryInstaller` and implements `populate_db` to parse a source file and insert entries into the SQLite database.

To modify or fix the Japanese dictionary build, edit the relevant builder script. Refer to the existing builders for the expected schema and conventions.

## Submitting changes

Fork the repo, make your changes, and open a pull request with a clear description.
