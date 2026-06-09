#!/app/orion_env/bin/python3

import sys
import argparse
from pathlib import Path

sys.path.insert(0, Path(__file__).parent.resolve().as_posix() + "/../lib")
import orion_modem


# Set up argument parser
parser = argparse.ArgumentParser(
    description="CLI utility to control cellular modem."
)

# Force the user to choose exactly one action
group = parser.add_mutually_exclusive_group(required=True)
group.add_argument('--on', action='store_true', help='Turn modem ON')
group.add_argument('--off', action='store_true', help='Turn modem OFF')
parser.add_argument('--usb', action='store_true', help='Disable USB driver')

args = parser.parse_args()

orion_modem.modem_power(True if args.on else False, args.usb)
