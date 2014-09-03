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

print("Opening serial connection.")
serial_conn = serial.Serial('COM4', 9600, timeout=1)

address = 0
print("Creating load object.")
load = array3710.Load(address, serial_conn)
load.remote_control = True

# Create program object
prog = array3710.Program(array3710.Program.PROG_TYPE_RESISTANCE, array3710.Program.RUN_REPEAT)
# Three program types:
#  PROG_TYPE_CURRENT, PROG_TYPE_RESISTANCE, PROG_TYPE_POWER
#
# Two Run Modes: RUN_ONCE, RUN_REPEAT

# Using multiple calls to add_step to create a 10 step program with
# resistances given below.
resistances = (500, 450, 400, 350, 300, 250, 200, 150, 100, 50)
for resist in resistances:
    print("Adding step - Resistance: {}, Time: {}".format(resist, 10))
    prog.add_step(resist, 10)

# Upload the program to the load
load.set_program_sequence(prog)

print('')
print("Running Program - Notice load is NOT ON")
print("Expected 10 second delays and seeing only 7 second delays.")
# Notice the False argument to start_program.  This tells it to
# not automatically turn on load.  Default is to turn on load.
load.start_program(False)
for resist in resistances:
    print("{} ohms".format(resist))
    for i in range(7):
        print(i+1)
        time.sleep(1)
print("Now I'll wait for 5 seconds as the program starts to repeat, before stopping it.")
time.sleep(5)

# Notice the False argument to stop_program.  This tells it to
# not automatically turn off load.  Default is to turn off load.
load.stop_program(False)
print("Program Stopped.")

# New quick program as RUN_ONCE
prog = array3710.Program(array3710.Program.PROG_TYPE_RESISTANCE, array3710.Program.RUN_ONCE)
# 500 ohms for 10 seconds
prog.add_step(123, 10)
# Upload new program
print('')
print("Uploading new program with 123 ohms.")
load.set_program_sequence(prog)
print("Starting program with automatic load on.")
load.start_program()
print("Waiting 7 seconds (10 in program seconds)")
print("Load was automatically turned on.")
time.sleep(7)
print("Program should be finished, notice we are back in non-program mode with load still on.")
print("Load does not automatically turn off at end of program.  Must call stop_program or load_on = False")
time.sleep(5)
print('')
print("Running program again.")
time.sleep(5)
print("Stopping program before finished with auto load off.")
load.stop_program()
print("Load should be off.")

print('')
print("I am not sure why it is occurring, but both of my loads run program steps in 70% of expected time.")
print("This is why the 10 second steps only took 7 seconds.  I'd be interested if others see the same results.")

load.remote_control = False
serial_conn.close()
