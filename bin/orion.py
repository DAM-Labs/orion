import os
import sys
import time
import subprocess
import glob
import re
import json
import random
from zoneinfo import ZoneInfo
from timezonefinder import TimezoneFinder
from datetime import datetime, timedelta, timezone
import numpy as np
import cv2
from astral import LocationInfo
from astral.sun import sun
from gpiozero import AngularServo
from time import sleep
from pathlib import Path

# ================= Configuration =================
CONFIG_FILE = Path(__file__).parent.resolve().as_posix() + "/../conf/config.json"
INTERVAL_SECONDS = 60  # Time between shots
# Night sky needs long exposures. 15000000 microseconds = 15 seconds.
# Adjust shutter and gain based on your specific camera module and light pollution.
CAMERA_CMD = [
    "rpicam-still",
    "-n", "--immediate",
    "--shutter", "15000000",
    "--gain", "12",
    "-o"
]

servo = AngularServo(18, min_angle=0, max_angle=180, min_pulse_width=0.0005, max_pulse_width=0.0025)
# =================================================

def orion_starfield():
    try: cols, rows = os.get_terminal_size()
    except OSError: cols, rows = 80, 24

    # Expanded ASCII art using solid blocks and pipe/box characters
    logo = [
        " ██████╗ ██████╗ ██╗ ██████╗ ███╗   ██╗",
        "██╔═══██╗██╔══██╗██║██╔═══██╗████╗  ██║",
        "██║   ██║██████╔╝██║██║   ██║██╔██╗ ██║",
        "██║   ██║██╔══██╗██║██║   ██║██║╚██╗██║",
        "╚██████╔╝██║  ██║██║╚██████╔╝██║ ╚████║",
        " ╚═════╝ ╚═╝  ╚═╝╚═╝ ╚═════╝ ╚═╝  ╚═══╝"
    ]

    # Calculate dimensions to dynamically center the larger art
    lw, lh = len(logo[0]), len(logo)
    oy, ox = (rows - lh) // 2, (cols - lw) // 2
    os.system('cls' if os.name == 'nt' else 'clear')

    for y in range(rows - 1):
        line = []
        for x in range(cols):
            # Check if current coordinate hits a block/pipe in the logo
            if oy <= y < oy + lh and ox <= x < ox + lw and logo[y-oy][x-ox] != ' ':
                line.append(f"\033[1;33m{logo[y-oy][x-ox]}\033[0m") # Bright yellow
            else:
                line.append(random.choice(['.', '+', '*', ' ', '♦', '\033[1;33m+\033[0m', '\033[1;34m*\033[0m']) if random.random() < 0.04 else " ")
        print("".join(line))

    sleep(5)
    os.system('clear')

def load_json_config(filepath):
    """
    Reads a JSON configuration file and parses the settings into a dictionary.

    Args:
        filepath (str): The path to the JSON configuration file.

    Returns:
        Dict[str, Any]: A dictionary containing the parsed configuration settings.
                        Returns an empty dictionary if an error occurs.
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as file:
            config = json.load(file)

            # Ensure the top-level JSON structure is an object (dictionary in Python)
            if not isinstance(config, dict):
                log_message(f"Invalid config format: Top-level structure in '{filepath}' must be a JSON object.")
                return {}

            return config

    except FileNotFoundError:
        log_message(f"Configuration file not found: '{filepath}'")
    except json.JSONDecodeError as e:
        log_message(f"JSON decoding error in '{filepath}': {e}")
    except PermissionError:
        log_message(f"Permission denied when trying to read '{filepath}'")
    except Exception as e:
        log_message(f"An unexpected error occurred while reading '{filepath}': {e}")

    return {}

def log_message(message, end="\n", to_file=False):
    now = datetime.now()
    print(f"{now} > {message}", end=end)

def move_servo(target_degrees):
    """
    Moves a servo connected to GPIO 18 to the specified angle.
    """
    if 0 <= target_degrees <= 180:
        log_message(f"Moving servo to {target_degrees} degrees...")
        servo.angle = target_degrees

        # Give the physical motor time to reach the position before the script continues
        sleep(0.5)
    else:
        log_message("Error: Please supply an angle between 0 and 180 degrees.")

def check_pi_camera():
    """
    Checks if a Raspberry Pi native camera is attached and working under OS Trixie.
    Parses and prints the camera model, primary resolution, and available sensor modes.
    """
    try:
        # Run rpicam command to query available hardware modules
        result = subprocess.run(
            ["rpicam-still", "--list-cameras"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=5
        )

        # Combinations of stdout and stderr are handled because rpicam-apps output destinations 
        # can vary depending on driver logging levels.
        output = result.stdout + result.stderr

        if "No cameras available" in output or not output.strip():
            return False

        log_message(f"Camera: \033[34mDetected\033[0m")

        # Regex to parse the main device block e.g., "0 : imx708 [4608x2592 10-bit RGGB] (...)"
        camera_match = re.search(r"\d+\s*:\s*([\w\-]+)\s*\[(\d+x\d+)\s+([^\]]+)\]", output)

        if camera_match:
            model = camera_match.group(1)
            max_res = camera_match.group(2)
            bit_depth = camera_match.group(3)

            log_message(f"Camera Model: \033[34m{model}\033[0m")
            log_message(f"Max Resolution: \033[34m{max_res} pixels\033[0m")
            log_message(f"Sensor Format: \033[34m{bit_depth}\033[0m")

        # Regex to find the path inside the device tree mapping
        bus_match = re.search(r"\(([^)]+)\)", output)
        if bus_match:
            log_message(f"Hardware Path: \033[34m{bus_match.group(1)}\033[0m")

        # Extract individual hardware sensor modes supported directly by the module
        modes_block = re.findall(r"(\d+x\d+)\s*\[([\d.]+)\s*fps[^\]]*\]", output)
        if modes_block:
            modes = ""
            for mode in modes_block:
                modes += f"\033[34m{mode[0]} @ {mode[1]} FPS\033[0m,"

            log_message(f"Supported Hardware Modes: {modes}")
        return True

    except FileNotFoundError:
        log_message("\033[31mError:\033[0m 'rpicam-still' utility not found. Ensure rpicam-apps package is installed.")
        return False
    except subprocess.TimeoutExpired:
        log_message("\033[31mError:\033[0m Camera query timed out. The hardware bus might be frozen.")
        return False
    except Exception as e:
        log_message(f"\033[31mUnexpected error checking camera status: {e}\033[0m")
        return False

def read_coords(filepath):
    """Read latitude and longitude from a text file."""
    if os.path.exists(filepath):
        with open(filepath, 'r') as f:
            lat, lon = map(float, f.read().strip().split(','))
        return lat, lon

    return ()

def get_capture_window(lat, lon):
    """Calculate the start and end times for the current/next night's capture."""

    # Get timezone
    tf = TimezoneFinder()
    timezone_name = tf.timezone_at(lng=lon, lat=lat)

    # Get current time in the timezone
    now = datetime.now(ZoneInfo(timezone_name))

    # Astral requires a LocationInfo object. City/Region names are arbitrary here.
    loc = LocationInfo("Pi", "Earth", timezone_name, lat, lon)

    # Calculate for today and tomorrow
    s_today = sun(loc.observer, date=now.date(), tzinfo=ZoneInfo(timezone_name))
    s_tomorrow = sun(loc.observer, date=now.date() + timedelta(days=1), tzinfo=ZoneInfo(timezone_name))

    start_window = s_today['sunset'] + timedelta(hours=1)
    end_window = s_tomorrow['sunrise'] - timedelta(hours=1)

    # If we are already past the current window, calculate for the next evening
    if now > end_window:
        s_next = sun(loc.observer, date=now.date() + timedelta(days=1))
        s_next_morning = sun(loc.observer, date=now.date() + timedelta(days=2))
        start_window = s_next['sunset'] + timedelta(hours=1)
        end_window = s_next_morning['sunrise'] - timedelta(hours=1)

    return start_window, end_window, timezone_name

def stack_and_clean(image_dir, final_output_path):
    """Stack images using Maximum Pixel blending and delete originals."""
    search_path = os.path.join(image_dir, "frame_*.jpg")
    image_paths = sorted(glob.glob(search_path))

    if not image_paths:
        log_message("\033[33mNo images found to stack.\033[0m")
        return

    log_message(f"Stacking {len(image_paths)} images...")

    # Read the first image as the base
    # We process one by one to prevent the Pi from running out of RAM
    stacked = cv2.imread(image_paths[0])

    for path in image_paths[1:]:
        img = cv2.imread(path)
        if img is not None:
            # Maximum blending pulls the brightest pixels (stars) from the dark sky
            # creating star trails and drastically reducing background noise.
            stacked = np.maximum(stacked, img)

    # Save the final enhanced image
    cv2.imwrite(final_output_path, stacked)
    log_message(f"Stacked image saved to \033[34m{final_output_path}\033[0m")

    # Clean up individual frames
    clean_old_images(image_dir)

def clean_old_images(image_dir):
    search_path = os.path.join(image_dir, "frame_*.jpg")
    image_paths = sorted(glob.glob(search_path))
    count = 0

    log_message(f"\033[33mCleaning up individual frames in\033[0m \033[34m{image_dir}\033[0m")
    for path in image_paths:
        os.remove(path)
        count += 1

    log_message(f"Deleted {count} files")

def main():
    # Show intro
    orion_starfield()

    # Read config JSON
    log_message(f"\033[33mReading configuration from\033[0m \033[34m{CONFIG_FILE}\033[0m")
    config = load_json_config(CONFIG_FILE);
    if not config:
        log_message(f"No config file found at {CONFIG_FILE}. \033[31mExiting...\033[0m")
        sys.exit(-1)
    else:
        log_message(f"Using configuration: \033[34m{config}\033[0m")

    # Check that we have a camera connected
    if not check_pi_camera():
        log_message("No camera found. \033[31mExiting...\033[0m")
        sys.exit(-1)

    # Create temp dir
    if not os.path.exists(config["temp_image_dir"]):
        log_message(f"\033[33mCreating temporary dir\033[0m \033[34m{config["temp_image_dir"]}\033[0m")
        os.makedirs(config["temp_image_dir"])

    # Create final dir
    if not os.path.exists(config["final_image_dir"]):
        log_message(f"\033[33mCreating final dir\033[0m \033[34m{config["final_image_dir"]}\033[0m")
        os.makedirs(config["final_image_dir"])

    # Make sure we have coordinates
    if not config["latitude"] or not config["longitude"]:
        log_message("No coordinates found. \033[31mExiting...\033[0m")
        sys.exit(-1)

    log_message(f"Loaded coordinates: \033[34m[{config["latitude"]}, {config["longitude"]}]\033[0m")

    # Enter main waiting loop
    while True:
        start_time, end_time, timezone_name = get_capture_window(config["latitude"], config["longitude"])
        now = datetime.now(ZoneInfo(timezone_name))
        log_message(f"Time zone: \033[34m{timezone_name}\033[0m")
        log_message(f"Current Time: \033[34m{now.strftime('%Y-%m-%d %H:%M:%S %Z')}\033[0m")
        log_message(f"Next capture window: \033[34m{start_time.strftime('%Y-%m-%d %H:%M:%S %Z')} to {end_time.strftime('%Y-%m-%d %H:%M:%S %Z')}\033[0m")

        # Wait until the start of the window
        if now < start_time:
            # Removed old images if any
            clean_old_images(config["temp_image_dir"])

            # Wait till the next sunset
            sleep_seconds = (start_time - now).total_seconds()
            log_message(f"\033[33mWaiting {sleep_seconds / 3600:.2f} hours until sunset + 1 hour...\033[0m")
            time.sleep(sleep_seconds)

        # Open camera to the sky
        move_servo(90)

        log_message("Capture window active. \033[32mStarting collection...\033[0m")
        log_message(f"Collection interval: \033[34m{INTERVAL_SECONDS} s\033[0m")
        frame_count = 0

        # Capture loop
        while datetime.now(timezone.utc) < end_time:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.join(OUTPUT_DIR, f"frame_{timestamp}.jpg")

            cmd = CAMERA_CMD + [filename]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            frame_count += 1
            log_message(f"Captured frame #{frame_count} \033[34m{filename}\033[0m")

            # Sleep until the next interval, breaking early if the window ends
            time.sleep(INTERVAL_SECONDS)

        log_message("Capture window ended. \033[32mInitiating stacking sequence...\033[0m")

        move_servo(0)

        # Format the final stacked image name with today's date
        date_str = datetime.now().strftime("%Y-%m-%d")
        final_image_path = os.path.join(OUTPUT_DIR, f"{date_str}_{STACKED_FILENAME}")

        stack_and_clean(OUTPUT_DIR, final_image_path)

        # Loop restarts to wait for the next night

if __name__ == "__main__":
    main()
