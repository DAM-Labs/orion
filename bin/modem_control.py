#!/app/orion_env/bin/python3

import argparse
import time
import sys
from gpiozero import OutputDevice

GPIO_PIN = 6

def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(
        description="CLI utility to control Raspberry Pi GPIO pins using gpiozero."
    )

    # Force the user to choose exactly one action
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--on', action='store_true', help='Drive the GPIO pin HIGH')
    group.add_argument('--off', action='store_true', help='Drive the GPIO pin LOW')


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
        elif args.off:
            pin.on()
            time.sleep(3)
            pin.off()
            time.sleep(18)
            print(f"Cell modem OFF.")

    except KeyboardInterrupt:
        print("\nExecution interrupted by user.")
    finally:
        # Explicitly clean up or close if logic demands it
        pin.close()

if __name__ == '__main__':
    main()
