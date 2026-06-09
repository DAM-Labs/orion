#!/app/orion_env/bin/python3

import argparse

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
group.add_argument('--usb', action='store_true', help='Disable USB driver')

args = parser.parse_args()




