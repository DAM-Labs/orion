import requests

def get_cloud_coverage(latitude: float, longitude: float) -> int | None:
    """
    Given GPS coordinates, returns the current sky cloud coverage as a percentage (0-100%).
    Returns None if the API request fails.
    """
    # Open-Meteo free forecasting API endpoint
    url = "https://api.open-meteo.com/v1/forecast"
    
    # Query parameters specifying the location and requested data (cloud_cover)
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": "cloud_cover"
    }
    
    try:
        # Fetch the weather data
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()  # Raise an error for bad HTTP status codes
        
        # Parse the JSON response
        data = response.json()
        
        # Extract cloud cover percentage from the 'current' data block
        cloud_percentage = data["current"]["cloud_cover"]
        return int(cloud_percentage)
        
    except requests.exceptions.RequestException as e:
        print(f"Network or API Error: {e}")
        return None
    except KeyError:
        print("Error: Unexpected data format received from the weather API.")
        return None
