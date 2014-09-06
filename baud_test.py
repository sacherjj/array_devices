from __future__ import division
import serial
import time
from array_devices import array3710

__author__ = 'JoeSacher'

"""
This is a crude script to play with PC baud rates while the load
is set to a fixed baud rate.
"""

load_addr = 1

# This should match load
base_baud_rate = 9600
serial_conn = serial.Serial('COM4', base_baud_rate, timeout=1)
load = array3710.Load(load_addr, serial_conn)
load.remote_control = True
serial_conn.close()


# Set this to sufficient range to get possible valid connections
min_rate = 3500
max_rate = 20000
print("Walking from {} to {} for {}".format(min_rate, max_rate, base_baud_rate))
for baud_rate in xrange(min_rate, max_rate, 100):
    time.sleep(0.1)
    serial_conn = serial.Serial('COM4', baud_rate, timeout=0.5)
    try:
        load = array3710.Load(load_addr, serial_conn, print_errors=False)
    except IOError:
        print("Baud_Rate: {} Error: Can't creating load".format(baud_rate))
    else:
        error_count = 0
        for i in range(10):
            try:
                load.set_load_resistance(baud_rate/1000)
                load.update_status(retry_count=1)
    #            print(load.voltage)
            except IOError:
                error_count += 1
            try:
                load.load_on = True

                load.load_on = False
                time.sleep(0.05)
            except IOError:
                error_count += 1
        print("Baud_Rate: {} - Errors: {}".format(baud_rate, error_count))
    serial_conn.close()

serial_conn = serial.Serial('COM4', base_baud_rate, timeout=1)
load = array3710.Load(load_addr, serial_conn)
load.remote_control = False
serial_conn.close()

"""
Results for both of my loads.
I found the multiple baud responses when the load was set at 9600 very interesting.
When I get time, I want to scope the wild mismatches and see what is going on.

4800(L1): 4700-5200 (All 0 errors)
4800(L2): 4700-5200 (All 0 errors)

9600(L1): 4000-4600, 5300-6400, 7600-12400, 15100-17400  (All 0 errors)
9600(L2): 4000-4600, 5300-6400, 7600-12400, 15100-17400  (All 0 errors)

19200(L1): 17500-24000 (~30% with 1 error, 1 with 2 errors)
19200(L2): 17500-24000 (~20% with 1 error, 5% with 2 errors)

38400(L1): 35900-44200 (Errors of 1-4 throughout range, pretty evenly spread, 20% with 0 errors)
38400(L2): 35900-44200 (same distribution of errors as L1 at this baud rate)
"""