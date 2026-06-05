#!/usr/bin/env python3

import subprocess
import time

# Configuration
CHECK_INTERVAL = 1  # Seconds
USB_PORT = "4"      # Usually port 2 on RPi 4/5, use 'uhubctl' to verify

def is_modem_present():
    try:
        # Run mmcli -L and capture output
        result = subprocess.run(['/usr/bin/mmcli', '-L'], capture_output=True, text=True)
        # If "No modems were found" is in output or it's empty, it's missing
        if "No modems were found" in result.stdout or not result.stdout.strip():
            return False
        return True
    except Exception as e:
        print(f"Error checking modem: {e}")
        return False

def reset_usb_power():
    print("Modem missing! Resetting USB power...")
    try:
        # Turn off power
        subprocess.run(['/usr/sbin/uhubctl', '-l', '1-1', '-p', USB_PORT, '-a', '0'], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # Give it a moment to fully discharge
        time.sleep(3)

        # Turn on power
        subprocess.run(['/usr/sbin/uhubctl', '-l', '1-1', '-p', USB_PORT, '-a', '1'], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # Wait for the modem to boot before checking again
        print("Power cycled. Waiting for modem to initialize...")
        time.sleep(30)
    except Exception as e:
        print(f"Failed to reset USB: {e}")

def main():
    print("Starting Modem Watchdog...")
    retry_count = 0

    while True:
        if not is_modem_present():
            reset_usb_power()
            retry_count += 1

            if retry_count > 10:
                subprocess.run(['/usr/sbin/reboot'])
        else:
            retry_count = 0
            pass

        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
