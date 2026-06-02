import json
import os

def update_status_file(file_path, new_data):
    """
    Reads a JSON file, updates it with new key-value pairs, 
    and writes it back to the file.

    :param file_path: Path to the JSON file.
    :param new_data: A dictionary containing the key-value pairs to add/update.
    """
    # 1. Read the existing JSON file
    # Check if file exists and is not empty to prevent JSONDecodeError
    if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
        with open(file_path, 'r', encoding='utf-8') as file:
            try:
                data = json.load(file)
            except json.JSONDecodeError:
                print(f"Warning: {file_path} was corrupted. Starting with an empty dictionary.")
                data = {}
    else:
        # If the file doesn't exist or is empty, start with an empty dictionary
        data = {}

    # 2. Update the data with the new key-value pairs
    # .update() modifies existing keys and inserts new ones automatically
    data.update(new_data)

    # 3. Write the updated data back to the file
    with open(file_path, 'w', encoding='utf-8') as file:
        # indent=4 makes the JSON file human-readable
        json.dump(data, file, indent=4, ensure_ascii=False)
