array_devices
=========

Python Interface to currently only the Array 3710A DC Electronic Load
This load is also sold under Gossen, Tekpower, Circuit Specialists with same 3710A model number.

All capabilities in programming data sheet are supported.  

This has been developed in Python 2.7 32-bit and Python 3.3 32-bit 
on Windows 7 64-bit.  I will try to test on Linux, but don't expect issues.  

## Possible Program Mode Timing Issues
Note: When using program mode, I have noticed on both of my TekPower 3710A 
loads that programs run in a little less than 70% of expected time.  A 10 second
step is completing in just under 7 seconds.  I do not plan to use program mode, as
I will be scripting the program in Python.  

## Baud Rate
The only baud rates I can recommend are 9600 and 4800.  I have not been able to 
achieve 100% reliable communication at 19200 baud.  38400 baud often gives me more
failures than successes.  I have two loads on the same TTL line and running 9600 baud
as fast as I can send commands for over 5000 commands without a failure.

My best guess is that it is a consumption data rate issue.  Once a load is in failure,
if the packet storm is not paused, it will not recover.  When I'm talking to multiple
loads on a single TTL serial bus, all loads must parse all messages to read if their
address is included.  So even if the load is spread around multiple loads, the speed
of parsing does not change for an individual load.  It makes sense to build in some
slight pauses between communication to allow recovery points.

## pySerial

While not required in the array3710.py code itself, pySerial is required to open the
USB serial connection that you provide to initialize the Array3710 object.  

## Simple Example

See [simple_example.py](https://github.com/sacherjj/array_devices/blob/master/simple_example.py) for doing basic interfacing with load.

## Programming Load

See [programming_example.py](https://github.com/sacherjj/array_devices/blob/master/programming_example.py) for sending a program to the load and running it.

## Multiple Loads with Single USB Port
The DB9 cable from the Load to the 3312 TTL Serial to USB adaptor has the following pinout:

1. 3.3V
2. TX (from Computer)
3. RX (from Load)
5. GND

All other pins are not connected.

3.3V power must be supplied from a single load to the 3312 adaptor, because it powers the 
circuitry on the TTL side of the optoisolators.  However, if multiple loads are connected
to this 3.3V line, there IS back feed into other loads.  If you power up a single load and
connect it to another with a standard Y-cable, the micro-controller will power up and 
begin displaying characters on the LCD.  The load will not function and the LCD backlight
will be off, because the higher power circuits are not on.  This is a potentially damaging
situation for the loads.  

To daisy chain loads on the TTL side, you need to make a custom splitter.  The primary
load will provide power for the 3312 adaptor, and MUST be on to communicate to any of the
other loads.  Pinout for this connection is the full 4 connections:

1. 3.3V
2. TX
3. RX
5. GND

All secondary loads connected should use this:

1. NOT CONNECTED
2. TX
3. RX
5. GND

I only have 2 loads connected in this manner, but you should be able to connect as many
as you want, until you reach a noise threshold due to cable lengths.  Just make sure to 
set the addresses to unique values.

Note: I am seeing some backfeeding from the pull up on the signal lines.  This is causing
the beeper on the secondary load to stay beeping when turned off.  This is not a problem if
all loads are powered around the same time.  The best method to join loads would be multiple
optoisolator pairs from one USB to RS232 TLL board.

## Talking to Multiple Loads

See [multiple_loads_example.py](https://github.com/sacherjj/array_devices/blob/master/multiple_loads_example.py) for talking with multiple loads on one USB port.