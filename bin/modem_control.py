#!/app/orion_env/bin/python3

import argparse
import time
import sys
import subprocess
from gpiozero import OutputDevice

GPIO_PIN = 6

def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(
        description="CLI utility to control cellular modem."
    )

    # Force the user to choose exactly one action
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--on', action='store_true', help='Turn modem ON')
    group.add_argument('--off', action='store_true', help='Turn modem OFF')


    args = parser.parse_args()

    # Initialize the pin device
    pin = OutputDevice(GPIO_PIN)

    try:
        if args.on:
            pin.on()
            time.sleep(2)
            pin.off()
            time.sleep(20)
            print(f"Cell modem ON.")
            subprocess.run(['/usr/bin/systemctl', 'start', 'modem_checker'], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        elif args.off:
            subprocess.run(['/usr/bin/systemctl', 'stop', 'modem_checker'], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            pin.on()
            time.sleep(3)
            pin.off()
            time.sleep(20)
            print(f"Cell modem OFF.")

    finally:
        # Explicitly clean up or close if logic demands it
        pin.close()

if __name__ == '__main__':
    main()
