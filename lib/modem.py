import subprocess
import json
import serial
import time
import sys
from gpiozero import OutputDevice 

def get_modem_list():
    """Returns a list of modem indices found on the system."""
    try:
        result = subprocess.check_output(["mmcli", "-L", "-J"], stderr=subprocess.STDOUT)
        data = json.loads(result)
        # Extract indices from the 'modem-list' array
        return [m.split('/')[-1] for m in data.get("modem-list", [])]
    except Exception as e:
        print(f"Error listing modems: {e}")
        return []

def get_modem_details(index):
    """Fetches and parses specific details for a given modem index."""
    try:
        result = subprocess.check_output(["mmcli", "-m", index, "-J"], stderr=subprocess.STDOUT)
        data = json.loads(result)
        modem = data.get("modem", {})

        # Extracting the specific fields you requested
        details = {
            "index": index,
            "status": modem.get("generic", {}).get("state"),
            "imei": modem.get("3gpp", {}).get("imei"),
            "signal_quality": int(modem.get("generic", {}).get("signal-quality", {}).get("value")),
            "operator_name": modem.get("3gpp", {}).get("operator-name"),
            "signal_level": 0,
        }

        if details["signal_quality"] > 0:
            result = subprocess.check_output(["mmcli", "-m", index, "--signal-setup=15"], stderr=subprocess.STDOUT)
            result = subprocess.check_output(["mmcli", "-m", index, "--signal-get", "-J"], stderr=subprocess.STDOUT)
            data = json.loads(result)
            modem = data.get("modem", {})

            if modem:
                rssi = modem.get("signal", {}).get("lte", {}).get("rssi")

                if rssi:
                    details["signal_level"] = round(2 * (float(rssi) + 100), 0)

        return details
    except Exception as e:
        print(f"Error getting details for modem {index}: {e}")
        return None

def run_gps_service():
    index, at_port, gps_port = parse_modem_info()

    if not at_port or not gps_port:
        print(f"Required ports not found. AT: {at_port}, GPS: {gps_port}")
        return

    print(f"Found Modem {index}. AT Port: {at_port}, GPS Port: {gps_port}")

    # Initialize GPS via AT Command
    try:
        with serial.Serial(at_port, 115200, timeout=1) as ser:
            ser.write(b'AT+CGPS=1\r\n')
            time.sleep(1)
            response = ser.read_all().decode()
            print(f"GPS Start Command Sent. Response: {response.strip()}")
    except Exception as e:
        print(f"Error connecting to AT port: {e}")
        return

    # Main Loop
    while True:
        try:
            with serial.Serial(gps_port, 9600, timeout=2) as gps_ser:
                # Read for a short burst to find the GPGGA string
                start_time = time.time()
                while time.time() - start_time < 5: 
                    line = gps_ser.readline().decode('ascii', errors='replace').strip()

                    if line.startswith('$GPGGA'):
                        parts = line.split(',')
                        print(parts)
                        # Index 2: Lat, 3: N/S, 4: Lon, 5: E/W
                        if len(parts) > 5 and parts[2] and parts[4]:
                            lat = dm_to_decimal(parts[2], parts[3])
                            lon = dm_to_decimal(parts[4], parts[5])

                            with open('/dev/shm/gps.dat', 'w') as f:
                                f.write(f"{lat:.6f}, {lon:.6f}\n")

                            print(f"Updated GPS: {lat:.6f} [{parts[2]} {parts[3]}], {lon:.6f} [{parts[4]} {parts[5]}]")
                            break # Found our sentence, break to wait for next interval

        except Exception as e:
            print(f"Error reading GPS port: {e}")

        time.sleep(15)

def dm_to_decimal(value, direction):
    if not value:
        return 0.0
    # Format: DDMM.MMMM
    dot_index = value.find('.')
    degrees = float(value[:dot_index-2])
    minutes = float(value[dot_index-2:])
    decimal = degrees + (minutes / 60)

    if direction in ['S', 'W']:
        decimal *= -1

    return round(decimal, 8)


def modem_power(status, usb=0):
    if status:
        if usb:
            # Bind
            with open('/sys/bus/pci/drivers/xhci_hcd/bind', 'w') as f:
                f.write('0000:01:00.0')
        else:
            # Initialize the pin device
            pin = OutputDevice(6)
            pin.on()
            time.sleep(2)
            pin.off()
            pin.close()
                
        time.sleep(20)
        print(f"Cell modem ON.")
        subprocess.run(['/usr/bin/systemctl', 'start', 'modem_checker'], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        subprocess.run(['/usr/bin/systemctl', 'stop', 'modem_checker'], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        if usb:
            # Unbind
            with open('/sys/bus/pci/drivers/xhci_hcd/unbind', 'w') as f:
                f.write('0000:01:00.0')
        else:
            # Initialize the pin device
            pin = OutputDevice(6)
            pin.on()
            time.sleep(3)
            pin.off()
            pin.close()
            time.sleep(20)

        print(f"Cell modem OFF.")
