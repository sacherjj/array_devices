__author__ = 'Joe Sacher'

try:
    import serial
except ImportError as err:
    import sys
    sys.exit("ImportError: {}.\nIs pySerial package installed?".format(err))


from array_devices import array3710
import time


# See pySerial Documentation for Creating Connection
# http://pyserial.sourceforge.net/
# Use COM? for Windows, /dev/ttyS? for Unix

# Serial Port for 3312 USB to TTL Serial bridge included with 3710A Load
print("Opening serial connection.")
serial_conn = serial.Serial('COM4', 9600, timeout=1)
# Baud is set on Load: Menu -> Baud Rate
# For stability, I recommend 9600 or 4800 only.

# serial connection is created outside of the load object so
# multiple loads can be controlled with a single USB link
# see multiple_loads_example.py

# Address is set on Load: Menu -> Address
address = 0

print("Creating load object.")
load = array3710.Load(address, serial_conn)

# update_status pulls current values of load
# into the Load object.
print("Querying status.")
load.update_status()
# Once update_status is called, properties
# will be read from data retrieved until it is
# called again to refresh.
print("Status returned voltage: {}".format(load.voltage))

# Remote Control must be enabled to do anything to
# the load.
# If you forget this, you will not get errors,
# but the load will silently ignore everything.
#
# Notice above that in a monitoring scenario, it is possible
# to call update_status above WITHOUT having remote_control
# enabled.
print("Enabling remote control.")
load.remote_control = True

# The three set_load_? methods will change the load into the
# appropriate Current, Power, or Resistance mode and set the
# load value in Amps, Watts, or Ohms
print("Set to CC mode with 10 Amps.")
load.set_load_current(10)
time.sleep(2)  # 2 second delay to allow you to see changes on load

print("Set to CP mode with 15 Watts.")
load.set_load_power(15)
time.sleep(2)

print("Set to CR mode with 500 Ohms.")
load.set_load_resistance(500)
time.sleep(2)
# Leaving setting on highest resistance to be easiest on whatever
# You have connected., while turning load on.

print("Is load on? {}".format(load.load_on))
time.sleep(2)

print("Turning load on.")
load.load_on = True
print("Is load on? {}".format(load.load_on))
time.sleep(2)

# Toggling settings and mode while loaded is ok.
print("Switch to CC with 1mA while load is on.")
load.set_load_current(0.001)
time.sleep(2)

# Turn load off
print("Turning load off.")
load.load_on = False
time.sleep(2)

print("Done, but remote contol left enabled for 10 seconds.")
print("Try to use panel buttons...")
time.sleep(10)

# If you forget to disable remote control, you cannot use
# the load via panel buttons without power cycling the load.
load.remote_control = False
print("Remote control disabled.  Panel buttons now available.")
print("Note: If you went crazy with the panel buttons while disabled, you "
      "sometimes need to power cycle the load to get panel control back.")

# Close port
serial_conn.close()
