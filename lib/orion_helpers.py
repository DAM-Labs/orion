import json
import os
import requests
import mimetypes

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

def upload_image_multipart(image_path: str, url: str, extra_params: dict = None):
    """
    Uploads an image to a given URL using a multipart/form-data POST request.
    
    :param image_path: Local path to the image file.
    :param url: The destination endpoint.
    :param extra_params: Dictionary of additional form fields to send with the image.
    :return: The response object if successful, or None on failure.
    """
    if extra_params is None:
        extra_params = {}

    if not os.path.exists(image_path):
        print(f"Error: The file {image_path} does not exist.")
        return None

    # Guess the MIME type based on the file extension (e.g., 'image/jpeg')
    mime_type, _ = mimetypes.guess_type(image_path)
    if mime_type is None:
        mime_type = 'application/octet-stream' # Fallback

    filename = os.path.basename(image_path)

    try:
        # Open the file in binary read mode
        with open(image_path, 'rb') as img_file:
            
            # The 'files' dictionary defines the multipart payload.
            # Format: 'form_field_name': ('filename', file_object, 'mime_type')
            # NOTE: Change 'file' to whatever field name your receiving backend expects.
            files = {
                'file': (filename, img_file, mime_type)
            }
            
            # Execute the POST request
            # data=extra_params sends the additional parameters as standard form fields
            response = requests.post(
                url, 
                data=extra_params, 
                files=files, 
                timeout=30  # Good practice for remote Pi deployments
            )
            
            # Raise an HTTPError if the HTTP request returned an unsuccessful status code
            response.raise_for_status()
            
            print(f"Success: Uploaded {filename} to {url} (Status: {response.status_code})")
            return response

    except requests.exceptions.Timeout:
        print("Error: The upload request timed out.")
    except requests.exceptions.ConnectionError:
        print("Error: Failed to connect to the server. Check the Pi's network connection.")
    except requests.exceptions.HTTPError as err:
        print(f"Error: Server rejected the upload. HTTP Status: {response.status_code}")
        print(f"Server Response: {response.text}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        
    return None
