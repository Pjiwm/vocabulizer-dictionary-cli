import os
import sys
import json
import logging
import requests
import subprocess
from InquirerPy import inquirer
from pathlib import Path
from tqdm import tqdm  # For progress bar

required_dir = "dictionary_builders"
current_dir = os.path.basename(os.getcwd())

if current_dir != required_dir:
    print(
        f"Error: You must run this script from the '{required_dir}' directory.")
    print(f"Current directory: {os.getcwd()}")
    print(
        f"Please navigate to the '{required_dir}' directory and run the script using 'python3 src/main.py'.")
    sys.exit(1)


# Set up logging
logging.basicConfig(filename="download.log", level=logging.INFO,
                    format="%(asctime)s - %(message)s")

# Load links from the JSON file
with open("src/links.json", "r") as f:
    data = json.load(f)

# Create downloads directory if it doesn't exist
downloads_dir = Path("downloads")
downloads_dir.mkdir(exist_ok=True)


def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")


def download_file(name, url, destination, original_filename):
    try:
        logging.info(f"Starting download for: {name}")
        response = requests.get(url, stream=True)
        response.raise_for_status()
        file_size = int(response.headers.get('content-length', 0))
        dest_file = destination / original_filename

        # Use tqdm for progress bar
        with open(dest_file, "wb") as f, tqdm(
            desc=name,
            total=file_size,
            unit='B',
            unit_scale=True,
            unit_divisor=1024,
        ) as bar:
            for chunk in response.iter_content(1024):
                f.write(chunk)
                bar.update(len(chunk))

        logging.info(f"Successfully downloaded: {name}")
        return dest_file
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to download {name}: {e}")
        return None


def main():
    while True:
        clear_screen()

        # Prompt user to select which file to download or to exit
        choices = [dictionary["name"] for dictionary in data["dictionaries"]]
        choices.append("Exit")  # Add the Exit option at the end

        selected = inquirer.select(
            message="Select a file to download or choose 'Exit' to quit:",
            choices=choices
        ).execute()

        if selected == "Exit":
            logging.info("User exited the program.")
            break

        # Get the selected dictionary info
        selected_dictionary = next(
            item for item in data["dictionaries"] if item["name"] == selected)
        name = selected_dictionary["name"]
        url = selected_dictionary["url"]
        original_filename = selected_dictionary["fileName"]
        db_file_name = selected_dictionary["dbFileName"]
        script_path = selected_dictionary.get("script")

        # Confirm before downloading
        confirm = inquirer.confirm(
            message=f"Do you want to download {name}?"
        ).execute()

        if confirm:
            downloaded_file = download_file(
                name, url, downloads_dir, original_filename)

            if downloaded_file:
                logging.info(f"Downloaded and saved as: {original_filename}")
                print(f"Downloaded and saved as: {original_filename}")

                if script_path:
                    logging.info(
                        f"Running the installation script: {script_path}")
                    subprocess.run(
                        ["python", script_path, downloaded_file, db_file_name])
                else:
                    logging.warning(
                        f"No installation script specified for {name}.")

        else:
            logging.info(f"Download of {name} was canceled by the user.")

        inquirer.select("Press enter to continue",
                        choices=["Continue"]).execute()


if __name__ == "__main__":
    main()
