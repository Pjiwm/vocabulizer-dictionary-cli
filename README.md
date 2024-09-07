# Vocabulizer Dictionary CLI

**Vocabulizer Dictionary CLI** is a tool for creating and managing dictionary databases with a generic schema. This CLI tool is designed to handle various dictionary formats and is ideal for building custom dictionary databases.

## Features

- **Generic DB Schema:** Provides a consistent schema for different dictionaries.
- **Support for Multiple Dictionary Formats:** Allow custom implementations to parse different file types.
- **Extensible:** Easy to add support for new dictionary formats and languages.

## Requirements

- Python 3.7 or later
- A virtual environment (venv)

## Installation

1. **Clone the Repository:**

    ```bash
    git clone https://github.com/yourusername/vocabulizer-dictionary-cli.git
    cd vocabulizer-dictionary-cli
    ```

2. **Create and Activate a Virtual Environment:**

    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    ```

3. **Install Required Packages:**

    ```bash
    pip install -r requirements.txt
    ```

4. **Run the CLI Tool:**

    ```bash
    python src/main.py
    ```

## Usage

The CLI tool is used to create and manage dictionary databases. You can customize it by adding new dictionary formats or languages. For more details on usage, refer to the documentation within the `src` directory.

## Contribution

contributions to **Vocabulizer Dictionary CLI** are welcome. If you’d like to help, here are a few ways you can contribute:

- **Add Support for More Languages:** Extend the tool to handle dictionaries in additional languages.
- **Submit Bug Reports and Feature Requests:** Report any bugs or suggest new features.

To contribute, please fork the repository, make your changes, and submit a pull request. 

[Contributing guide](CONTRIBUTING.md). 

## License

This project is licensed under the [MIT License](LICENSE). 
