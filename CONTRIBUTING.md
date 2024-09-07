# Contributing to vocabulizer-dictionary-cli

## Guidelines

1. **Adding New Language Support**

   To add support for a new language, follow these steps:

   - **Create a New Installer Script**: Implement a new script in the `db_installers` directory. This script should:
     - Inherit from `DictionaryInstaller`.
     - Implement the `populate_db` method to handle database population.
     - Ensure the database schema matches the existing one.

   - **Update `src/links.json`**:
     - Add an entry for the new language in `links.json`. The entry should follow this format:
       ```json
       {
           "name": "Name of the Language (Base Language)",
           "url": "URL to the downloaded file",
           "fileName": "name_of_file.zip",
           "dbFileName": "BaseLang_TargetLang.db",
           "script": "db_installers/your_script.py"
       }
       ```
     - **`fileName`**: The name of the downloaded file.
     - **`dbFileName`**: The name of the database file to be created.
     - **`script`**: The path to your newly created installer script.

2. **Bug Fixes and Code Improvements**

   - **Bug Fixes**: If you find a bug, please provide a clear description and a solution in your pull request.
   - **Code Style**: Ensure that your code adheres to the project's coding style.

## Development Guide

1. **Setting Up Your Development Environment**

   - **Create and Activate a Virtual Environment**:
     ```bash
     python -m venv venv
     source venv/bin/activate  # On Windows use `venv\Scripts\activate`
     ```

   - **Install Dependencies**:
     ```bash
     pip install -r requirements.txt
     ```

2. **Adding a New Language Script**

   - **Implement the Installer**:
     Create a new Python script in `db_installers`. This script should implement the `DictionaryInstaller` class with methods for file extraction and database population. Refer to existing scripts for structure and conventions.

   - **Update Links JSON**:
     Add an entry to `src/links.json` as described in the Guidelines section.

   - **Testing**:
     Ensure your new installer script is tested. Test thoroughly to verify that the new language data is extracted and inserted into the database correctly.

3. **Submitting Your Contribution**

   - **Create a Pull Request**: Once your changes are complete, push them to your fork and create a pull request against the main repository.
   - **Describe Your Changes**: Provide a clear description of the changes, including any new language support or bug fixes.
