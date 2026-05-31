import os
import time
import sys

# --- Configuration ---

# Sysfs paths for Hardware PWM0 (Mapped to GPIO 18)
PWM_DIR = "/sys/class/pwm/pwmchip0"
PWM0_DIR = f"{PWM_DIR}/pwm0"

# Servo timing in nanoseconds (The kernel requires nanoseconds, not microseconds)
PERIOD_NS = 20_000_000       # 20ms standard servo cycle
MIN_PULSE_NS =   500_000     # 0.5ms (usually 0 degrees)
MAX_PULSE_NS = 2_500_000     # 2.5ms (usually 180 degrees)

def export_pwm():
    """Tells the kernel we want to use PWM Channel 0."""
    if not os.path.exists(PWM0_DIR):
        try:
            with open(f"{PWM_DIR}/export", "w") as f:
                f.write("0")
            time.sleep(0.5) # Give the OS a moment to generate the virtual files
        except PermissionError:
            print("Error: Permission denied. Run this script with 'sudo'.")

def set_angle(angle):
    """Calculates the pulse width and triggers the hardware PWM."""
    # Constrain angle between 0 and 180
    angle = max(0, min(180, angle))

    # Map angle to duty cycle in nanoseconds
    duty_cycle_ns = int(MIN_PULSE_NS + (angle / 180.0) * (MAX_PULSE_NS - MIN_PULSE_NS))

    # 1. Set the period (must be configured before the duty cycle)
    with open(f"{PWM0_DIR}/period", "w") as f:
        f.write(str(PERIOD_NS))

    # 2. Set the duty cycle (the actual pulse width that dictates the angle)
    with open(f"{PWM0_DIR}/duty_cycle", "w") as f:
        f.write(str(duty_cycle_ns))

    # 3. Enable the hardware signal
    with open(f"{PWM0_DIR}/enable", "w") as f:
        f.write("1")

def stop_servo():
    """Cuts the PWM signal entirely to eliminate jitter."""
    with open(f"{PWM0_DIR}/enable", "w") as f:
        f.write("0")

def move(angle):
    # Verify the dtoverlay was actually loaded in config.txt
    if not os.path.exists(PWM_DIR):
        print(f"Error: Hardware PWM not found at {PWM_DIR}.")
        print("Did you add 'dtoverlay=pwm-2chan' to config.txt and reboot?")

    try:
        export_pwm()
        set_angle(angle)

        # Wait for the mechanical arm to physically reach the destination
        time.sleep(1.0)

    finally:
        # THE JITTER KILLER
        if os.path.exists(PWM0_DIR):
            stop_servo()

