#!/app/orion_env/bin/python3

import subprocess
import serial
import time
import re

def get_mmcli_output(command):
    try:
        result = subprocess.check_output(command, shell=True).decode('utf-8')
        return result
    except subprocess.CalledProcessError:
        return ""

def parse_modem_info():
    # 1. Get Modem Index
    list_output = get_mmcli_output("mmcli -L")
    modem_match = re.search(r'Modem/(\d+)', list_output)
    if not modem_match:
        print("No modem found.")
        return None, None, None

    index = modem_match.group(1)

    # 2. Get Modem Details
    detail_output = get_mmcli_output(f"mmcli -m {index}")

    # Extract ports (Looking for 'at' and 'gps' types)
    # mmcli output usually lists ports like: ports: ttyUSB0 (at), ttyUSB1 (gps), etc.
    at_port = None
    gps_port = None

    ports_section = re.findall(r'(\w+)\s+\((at|gps|control)\)', detail_output)
    for port_name, port_type in ports_section:
        if port_type == 'at':
            at_port = f"/dev/{port_name}"
        elif port_type == 'gps':
            gps_port = f"/dev/{port_name}"

    return index, at_port, gps_port

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

if __name__ == "__main__":
    run_gps_service()
