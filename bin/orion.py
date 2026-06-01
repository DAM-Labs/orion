import os
import sys
import time
import subprocess
import glob
import re
import json
import random
import argparse
import numpy as np
import cv2
from zoneinfo import ZoneInfo
from timezonefinder import TimezoneFinder
from datetime import datetime, timedelta, timezone
from astral import LocationInfo
from astral.sun import sun
from pathlib import Path

sys.path.insert(0, Path(__file__).parent.resolve().as_posix() + "/../lib")
import orion_splash
import orion_servo

# ================= Configuration =================

CONFIG_FILE = Path(__file__).parent.resolve().as_posix() + "/../conf/config.json"
LOG_FILE = "/var/log/orion.log"
config = {}

# =================================================

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
                log_message(f"Error: Invalid config format. Top-level structure in '{filepath}' must be a JSON object.", to_file=True)
                return {}

            return config

    except FileNotFoundError:
        log_message(f"Error: Configuration file not found: '{filepath}'", to_file=True)
    except json.JSONDecodeError as e:
        log_message(f"Error: JSON decoding error in '{filepath}': {e}", to_file=True)
    except PermissionError:
        log_message(f"Error: Permission denied when trying to read '{filepath}'", to_file=True)
    except Exception as e:
        log_message(f"Error: An unexpected error occurred while reading '{filepath}': {e}", to_file=True)

    return {}

def log_message(message, end="\n", to_file=False):
    """
    Logs messages to screen and file.

    Args:
        message (str): Message to log
        end (char): Add new line or not
        to_file (bool): Write the message to the log file in addition to the screen
    """
    now = datetime.now()
    print(f"{now} > {message}", end=end)

    if to_file:
       # Strip color codes
       ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
       with open(LOG_FILE, "a") as file:
           file.write(ansi_escape.sub('', message) + end)

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

        log_message(f"Camera: \033[34mDetected\033[0m", to_file=config["log_to_file"])

        # Regex to parse the main device block e.g., "0 : imx708 [4608x2592 10-bit RGGB] (...)"
        camera_match = re.search(r"\d+\s*:\s*([\w\-]+)\s*\[(\d+x\d+)\s+([^\]]+)\]", output)

        if camera_match:
            model = camera_match.group(1)
            max_res = camera_match.group(2)
            bit_depth = camera_match.group(3)

            log_message(f"Camera Model: \033[34m{model}\033[0m", to_file=config["log_to_file"])
            log_message(f"Max Resolution: \033[34m{max_res} pixels\033[0m", to_file=config["log_to_file"])
            log_message(f"Sensor Format: \033[34m{bit_depth}\033[0m", to_file=config["log_to_file"])

        # Regex to find the path inside the device tree mapping
        bus_match = re.search(r"\(([^)]+)\)", output)
        if bus_match:
            log_message(f"Hardware Path: \033[34m{bus_match.group(1)}\033[0m", to_file=config["log_to_file"])

        # Extract individual hardware sensor modes supported directly by the module
        modes_block = re.findall(r"(\d+x\d+)\s*\[([\d.]+)\s*fps[^\]]*\]", output)
        if modes_block:
            modes = []
            for mode in modes_block:
                modes.append(f"\033[34m{mode[0]} @ {mode[1]} FPS\033[0m")

            log_message(f"Supported Hardware Modes: {",".join(modes)}", to_file=config["log_to_file"])
        return True

    except FileNotFoundError:
        log_message("\033[31mError:\033[0m 'rpicam-still' utility not found. Ensure rpicam-apps package is installed.", to_file=config["log_to_file"])
        return False
    except subprocess.TimeoutExpired:
        log_message("\033[31mError:\033[0m Camera query timed out. The hardware bus might be frozen.", to_file=config["log_to_file"])
        return False
    except Exception as e:
        log_message(f"\033[31mUnexpected error checking camera status: {e}\033[0m", to_file=config["log_to_file"])
        return False

def get_capture_window(lat, lon):
    """
    Calculate the start and end times for the current/next night's capture.

    Args:
        lat (float): Latitude
        lon (float): Longitude

    Returns:
        start_window (date): Sunset plus the buffer time
        end_window (date): Sunrise the next day minus the buffer time
        timezone_name (str): Name of the timezone which the [lat,lon] belong to
    """

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

    start_window = s_today['sunset'] + timedelta(minutes=config["minutes_delay"])
    end_window = s_tomorrow['sunrise'] - timedelta(minutes=config["minutes_delay"])

    # If we are already past the current window, calculate for the next evening
    if now > end_window:
        s_next = sun(loc.observer, date=now.date() + timedelta(days=1))
        s_next_morning = sun(loc.observer, date=now.date() + timedelta(days=2))
        start_window = s_next['sunset'] + timedelta(minutes=config["minutes_delay"])
        end_window = s_next_morning['sunrise'] - timedelta(minutes=config["minutes_delay"])

    return start_window, end_window, timezone_name

def stack_and_clean(image_dir, final_output_path):
    """Stack images using Maximum Pixel blending and delete originals."""
    search_path = os.path.join(image_dir, "frame_*.jpg")
    image_paths = sorted(glob.glob(search_path))

    if not image_paths:
        log_message("\033[31mNo images found to stack.\033[0m", to_file=config["log_to_file"])
        return

    log_message(f"\033[33mStacking {len(image_paths)} images...\033[0m", to_file=config["log_to_file"])

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
    log_message(f"Stacked image saved to \033[34m{final_output_path}\033[0m", to_file=config["log_to_file"])

    # Clean up individual frames
    clean_old_images(image_dir)

def clean_old_images(image_dir):
    search_path = os.path.join(image_dir, "frame_*.jpg")
    image_paths = sorted(glob.glob(search_path))
    count = 0

    log_message(f"\033[33mCleaning up individual frames in\033[0m \033[34m{image_dir}\033[0m", to_file=config["log_to_file"])
    for path in image_paths:
        os.remove(path)
        count += 1

    log_message(f"Deleted \033[34m{count}\033[0m files", to_file=config["log_to_file"])

def main():
    # Application-wide configuration
    global config, CONFIG_FILE

    # Parse command line args
    parser = argparse.ArgumentParser(
        description="ORION - automated sky capture and stacking application"
    )

    parser.add_argument(
        "--no_splash",
        action="store_true",
        help="Hide opening ORION animation on application startup"
    )

    parser.add_argument(
        "-c", "--config",
        type=str,
        default=CONFIG_FILE,
        help=f"Path to configuration JSON file (default: {CONFIG_FILE})"
    )

    args = parser.parse_args()

    # Process supplied args
    if args.config:
        CONFIG_FILE = args.config

    # Show intro
    if not args.no_splash:
        orion_splash.animated_starfield()

    # Read config JSON into global var
    log_message(f"\033[33mReading configuration from\033[0m \033[34m{CONFIG_FILE}\033[0m", to_file=True)
    config = load_json_config(CONFIG_FILE);
    if not config:
        log_message(f"No config file found at {CONFIG_FILE}. \033[31mExiting...\033[0m", to_file=True)
        sys.exit(-1)
    else:
        log_message(f"Using configuration: \033[34m{config}\033[0m", to_file=config["log_to_file"])

    # Make sure the servo iris is closed
    log_message(f"\033[33mClosing iris...\033[0m", to_file=config["log_to_file"])
    orion_servo.move(0)

    # Check that we have a camera connected
    # Exit if no camera found
    if not check_pi_camera():
        log_message("No camera found. \033[31mExiting...\033[0m", to_file=config["log_to_file"])
        sys.exit(-1)

    # Create temp dir
    if not os.path.exists(config["temp_image_dir"]):
        log_message(f"\033[33mCreating temporary dir\033[0m \033[34m{config["temp_image_dir"]}\033[0m", to_file=config["log_to_file"])
        os.makedirs(config["temp_image_dir"])

    # Create final dir
    if not os.path.exists(config["final_image_dir"]):
        log_message(f"\033[33mCreating final dir\033[0m \033[34m{config["final_image_dir"]}\033[0m", to_file=config["log_to_file"])
        os.makedirs(config["final_image_dir"])

    # Make sure we have coordinates
    # Exit if no coordinates configured
    if not config["latitude"] or not config["longitude"]:
        log_message("No coordinates found. \033[31mExiting...\033[0m", to_file=config["log_to_file"])
        sys.exit(-1)

    log_message(f"Loaded coordinates: \033[34m[{config["latitude"]}, {config["longitude"]}]\033[0m", to_file=config["log_to_file"])

    # Enter main waiting loop
    while True:
        start_time, end_time, timezone_name = get_capture_window(config["latitude"], config["longitude"])
        now = datetime.now(ZoneInfo(timezone_name))
        log_message(f"Time zone: \033[34m{timezone_name}\033[0m", to_file=config["log_to_file"])
        log_message(f"Current Time: \033[34m{now.strftime('%Y-%m-%d %H:%M:%S %Z')}\033[0m", to_file=config["log_to_file"])
        log_message(f"Capture delay: \033[34m{config["minutes_delay"]} minutes\033[0m", to_file=config["log_to_file"])
        log_message(f"Next capture window: \033[34m{start_time.strftime('%Y-%m-%d %H:%M:%S %Z')} to {end_time.strftime('%Y-%m-%d %H:%M:%S %Z')}\033[0m", to_file=config["log_to_file"])

        # Wait until the start of the window
        if now < start_time:
            # Removed old images if any
            clean_old_images(config["temp_image_dir"])

            # Wait till the next sunset
            sleep_seconds = (start_time - now).total_seconds()
            log_message(f"\033[33mWaiting {sleep_seconds / 3600:.2f} hours until sunset + {config["minutes_delay"]} minutes...\033[0m", to_file=config["log_to_file"])
            time.sleep(sleep_seconds)

        # Open camera to the sky
        log_message(f"\033[33mOpening iris...\033[0m", to_file=config["log_to_file"])
        orion_servo.move(90)

        log_message("Capture window active. \033[32mStarting collection...\033[0m", to_file=config["log_to_file"])
        log_message(f"Collection interval: \033[34m{config["imaging_interval"]} s\033[0m", to_file=config["log_to_file"])
        log_message(f"Camera shutter: \033[34m{config["camera_shutter"]} us\033[0m", to_file=config["log_to_file"])

        frame_count = 0

        # Capture loop
        while datetime.now(timezone.utc) < end_time:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.join(config["temp_image_dir"], f"frame_{timestamp}.jpg")

            cmd = [
                "/usr/bin/rpicam-still",
                "-n",
                "--immediate",
                "--shutter", str(config["camera_shutter"]),
                "--gain", "1",
                "--awbgains", "1,1",
                "-o", filename
            ]

            capture_start_time = time.perf_counter()
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            capture_end_time = time.perf_counter()
            capture_duration = capture_end_time - capture_start_time

            frame_count += 1
            log_message(f"Captured frame #{frame_count} \033[34m{filename}\033[0m", to_file=config["log_to_file"])
            log_message(f"Capturing took \033[34m{capture_duration:.2f}\033[0m seconds", to_file=config["log_to_file"])

            # Sleep until the next interval, breaking early if the window ends

            if capture_duration < config["imaging_interval"]:
                time.sleep(config["imaging_interval"] - capture_duration)

        log_message("Capture window ended. \033[32mInitiating stacking sequence...\033[0m", to_file=config["log_to_file"])

        # Close iris
        log_message(f"\033[33mClosing iris...\033[0m", to_file=config["log_to_file"])
        orion_servo.move(0)

        # Format the final stacked image name with today's date
        date_str = datetime.now().strftime("%Y-%m-%d")
        final_image_path = os.path.join(config["final_image_dir"], f"{date_str}_stacked.jpg")

        stack_and_clean(config["temp_image_dir"], final_image_path)

        # Loop restarts to wait for the next night

if __name__ == "__main__":
    main()
