import shutil
import subprocess
import re
import glob
import os

def get_uptime():
    """
    Returns the Raspberry Pi's system uptime in minutes.
    """
    try:
        with open('/proc/uptime', 'r') as f:
            # /proc/uptime contains system uptime in seconds, followed by idle time
            uptime_seconds = float(f.readline().split()[0])
            return uptime_seconds / 60
    except IOError:
        print("Could not read system uptime.")
        return 0.0

def get_cpu_temp():
    """
    Reads the Raspberry Pi CPU temperature directly from the system files.
    Returns the temperature in Celsius.
    """
    try:
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
            # The file returns a string like '45123' (which means 45.123°C)
            temp_raw = f.read()
            return float(temp_raw) / 1000.0
    except FileNotFoundError:
        print("Thermal zone file not found. Ensure this is running on a Linux/Raspberry Pi system.")
        return 0.0

def get_free_space_gb(path):
    """
    Returns the free space left on a specified drive/path in Gigabytes (GB).

    :param path: The mount point or directory (e.g., '/', '/data', '/media/pi/USB')
    :return: Free space in GB as a float
    """
    try:
        # shutil.disk_usage returns a named tuple: (total, used, free) in bytes
        usage = shutil.disk_usage(path)

        # Convert bytes to Gigabytes (1 GB = 1024^3 bytes)
        free_gb = usage.free / (1024 ** 3)
        return free_gb

    except FileNotFoundError:
        print(f"Error: The path '{path}' does not exist or is not mounted.")
        return 0.0
    except Exception as e:
        print(f"An error occurred while checking '{path}': {e}")
        return 0.0

def get_modem_signal_level():
    """
    Detects an attached modem via mmcli and returns its signal level percentage.
    Returns None if no modem is found or if the signal cannot be read.
    """
    try:
        # Step 1: Detect the modem index using 'mmcli -L'
        list_result = subprocess.run(
            ['mmcli', '-L'], 
            capture_output=True, 
            text=True, 
            check=True
        )

        # Search for the modem index (e.g., /org/freedesktop/ModemManager1/Modem/0)
        modem_match = re.search(r'/Modem/(\d+)', list_result.stdout)
        if not modem_match:
            print("No modem detected by ModemManager.")
            return None

        modem_index = modem_match.group(1)

        # Step 2: Query the specific modem using 'mmcli -m <index>'
        modem_result = subprocess.run(
            ['mmcli', '-m', modem_index], 
            capture_output=True, 
            text=True, 
            check=True
        )

        # Search for the 'signal quality' line (e.g., "signal quality: 78% (recent)")
        signal_match = re.search(r'signal quality:\s*(\d+)%', modem_result.stdout)
        if signal_match:
            return int(signal_match.group(1))

        print(f"Modem found at index {modem_index}, but signal quality is unavailable.")
        return None

    except FileNotFoundError:
        print("Error: 'mmcli' command not found. Is ModemManager installed?")
        return None
    except subprocess.CalledProcessError as e:
        print(f"Error executing mmcli command: {e}")
        return None

def set_powersave_governor(state):
    """
    Sets the CPU governor to 'powersave' for all available CPU cores.
    Requires root privileges (sudo) to execute successfully.
    """
    # Find the scaling_governor file path for every CPU core
    governor_paths = glob.glob('/sys/devices/system/cpu/cpu*/cpufreq/scaling_governor')

    if not governor_paths:
        print("Error: Could not find CPU scaling governor files. Are you running on Linux?")
        return False

    try:
        # Write 'powersave' to each core's governor file
        for path in governor_paths:
            with open(path, 'w') as file:
                file.write(state)
        return True

    except PermissionError:
        print("Permission Denied: You must run this script with root privileges (sudo).")
        return False
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return False
