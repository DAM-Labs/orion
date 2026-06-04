import json
import os

def deep_merge(source, destination):
    """
    Recursively merges source into destination.
    """
    for key, value in source.items():
        if isinstance(value, dict):
            # If the key is a dict in both source and destination, merge them recursively
            node = destination.setdefault(key, {})
            deep_merge(value, node)
        else:
            # Otherwise, just overwrite or insert the value
            destination[key] = value
    return destination

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
    deep_merge(new_data, data)

    # 3. Write the updated data back to the file
    with open(file_path, 'w', encoding='utf-8') as file:
        # indent=4 makes the JSON file human-readable
        json.dump(data, file, indent=4, ensure_ascii=False)
