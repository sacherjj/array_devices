__author__ = 'Joe Sacher'

try:
    import serial
except ImportError as err:
    import sys
    sys.exit("ImportError: {}.\nIs pySerial package installed?".format(err))

from array_devices import array3710
import time

# Note: Only new introduced functionality has comments.
# Look at simple_example.py first if you have questions
# about the following code.

# This is designed to use two loads connected on the TTL
# side of the 3312 TTL to USB bridge.  Loads are setup with
# addresses of 0 and 1
# See README.md for details on this connection.

print("Opening serial connection.")
serial_conn = serial.Serial('COM4', 9600, timeout=1)

# Using same serial connection for both loads.
# All packets have address number.  This is how
# loads know that we are talking with them.

print("Creating load object for address 0.")
load0 = array3710.Load(0, serial_conn)
print("Creating load object for address 1.")
load1 = array3710.Load(1, serial_conn)

# Nothing below is new, just being done on multiple objects.

print("Querying status 0.")
load0.update_status()
print("Status returned voltage 0: {}".format(load0.voltage))

print("Querying status 1.")
load1.update_status()
print("Status returned voltage 1: {}".format(load1.voltage))

print("Enabling remote control on both.")
load0.remote_control = True
load1.remote_control = True

print("Set to CC mode with 0.1 Amps on load 0.")
load0.set_load_current(0.1)
print("Set to CR mode with 450 Ohms on load 1.")
load1.set_load_resistance(450)
time.sleep(2)  # 2 second delay to allow you to see changes on load

print("Turning on load 0.")
load0.load_on = True
time.sleep(2)

print("Turning on load 1.")
load1.load_on = True
time.sleep(2)

print("Turning off load 0.")
load0.load_on = False
time.sleep(2)

print("Turning off load 1.")
load1.load_on = False
time.sleep(2)

print("Disabling remote control on both.")
load0.remote_control = False
load1.remote_control = False

serial_conn.close()
