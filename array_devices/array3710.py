from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import struct
import ctypes
import binascii
import sys

__author__ = 'Joe Sacher'

# Set flags for Python Major Versions
PY2 = sys.version_info[0] == 2
PY3 = sys.version_info[0] == 3


def byte2int(value):
    """
    Python 3 gets int from bytestring, Python 2 required ord.
    This abstracts that difference away.

    :param value: single value from byte string
    :return: int of value
    """
    if PY2:
        return ord(value)
    return value


class ProgramStep(object):
    """
    Represents a single step in an Array3710Program
    """
    # Max Settings based on PROG_TYPE modes as index
    # 1: 30A, 2: 200W, 3: 500ohms
    MAX_SETTINGS = (0, 30, 200, 500)
    # Display units
    SETTING_UNITS = ('', 'amps', 'watts', 'ohms')
    # Conversions between internal and external representations.
    # 1: 30000 -> 30A, 2: 2000 -> 200W, 3: 50000 -> 500ohms
    SETTING_DIVIDES = (1, 1000, 10, 100)

    def __init__(self, program, setting=0, duration=0):
        self.__program = program
        self._setting = 0
        self._duration = 0
        self.setting = setting
        self.duration = duration

    @property
    def setting(self):
        """
        Load setting (Amps, Watts, or Ohms depending on program mode)
        """
        prog_type = self.__program.program_type
        return self._setting / self.SETTING_DIVIDES[prog_type]

    @setting.setter
    def setting(self, value):
        prog_type = self.__program.program_type
        if 0 <= value <= self.MAX_SETTINGS[prog_type]:
            self._setting = value * self.SETTING_DIVIDES[prog_type]
        else:
            raise ValueError("Setting outside of valid range: 0-{} {}".format(
                self.MAX_SETTINGS[prog_type], self.SETTING_UNITS[prog_type]))

    @property
    def duration(self):
        """
        Duration of program step in seconds
        """
        return self._duration

    @duration.setter
    def duration(self, value):
        if 0 < value <= 60000:
            self._duration = value
        else:
            raise ValueError("Duration should be between 1-60000 seconds")

    @property
    def raw_data(self):
        """
        Raw data from step to be encoded into buffer as 2-byte integers
        """
        return self._setting, self._duration


class Program(object):
    """
    Represents a 10 step program for the load
    """
    PROG_TYPE_CURRENT = 0x01
    PROG_TYPE_POWER = 0x02
    PROG_TYPE_RESISTANCE = 0x03

    RUN_ONCE = 0x00
    RUN_REPEAT = 0x01

    def __init__(self, program_type=0x01, program_mode=0x00):
        if not program_type in (self.PROG_TYPE_CURRENT, self.PROG_TYPE_POWER, self.PROG_TYPE_RESISTANCE):
            raise ValueError("Illegal Program Type")
        self._program_type = program_type
        self._prog_steps = []
        self._program_mode = 0
        self.program_mode = program_mode

    @property
    def program_type(self):
        """
        Type of load control for entire program.

        This is read-only, because valid setting ranges change with
        different types.
        """
        return self._program_type

    @property
    def program_mode(self):
        """
        Sets Run Once or Repeat
        """
        return self._program_mode

    @program_mode.setter
    def program_mode(self, value):
        if not value in (self.RUN_ONCE, self.RUN_REPEAT):
            raise ValueError("Illegal Program Mode")
        self._program_mode = value

    @property
    def steps(self):
        for step in self._prog_steps:
            yield(step)

    def partial_steps_data(self, start=0):
        """
        Iterates 5 steps from start position and
        provides tuple for packing into buffer.

        returns (0, 0) if stpe doesn't exist.

        :param start: Position to start from (typically 0 or 5)
        :yield: (setting, duration)
        """
        cnt = 0
        if len(self._prog_steps) >= start:
            # yields actual steps for encoding
            for step in self._prog_steps[start:start+5]:
                yield((step.raw_data))
                cnt += 1
        while cnt < 5:
            yield((0, 0))
            cnt += 1

    def add_step(self, setting, duration):
        """
        Adds steps to a program.
        :param setting: Current, Wattage or Resistance, depending on program mode.
        :param duration: Length of step in seconds.
        :return: None
        """
        if len(self._prog_steps) < 10:
            self._prog_steps.append(ProgramStep(self, setting, duration))
        else:
            raise IndexError("Maximum of 10 steps are allowed")

    def delete_step(self, position=-1):
        """
        Removes step at position, or -1 to remove last step
        """
        del self._prog_steps[position]

    def load_buffer_one_to_five(self, out_buffer):
        """
        Loads first program buffer (0x93) with everything but
        first three bytes and checksum
        """
        struct.pack_into(b"< 2B", out_buffer, 3, self._program_type, len(self._prog_steps))
        offset = 5
        for ind, step in enumerate(self.partial_steps_data(0)):
            struct.pack_into(b"< 2H", out_buffer, offset + ind*4, step[0], step[1])

    def load_buffer_six_to_ten(self, out_buffer):
        """
        Loads second program buffer (0x94) with everything but
        first three bytes and checksum
        """
        offset = 3
        for ind, step in enumerate(self.partial_steps_data(5)):
            struct.pack_into(b"< 2H", out_buffer, offset + ind*4, step[0], step[1])
        struct.pack_into(b"< B x", out_buffer, 23, self._program_mode)


class Load(object):
    """
    Handles remote control of Array 3710A DC Electronic Load.
    Also sold under Gossen, Tekpower, Circuit Specialists with same 3710A model number.
    """

    DEBUG_MODE = False

    # Packet command values
    CMD_SET_PARAMETERS = 0x90
    CMD_READ_VALUES = 0x91
    CMD_LOAD_STATE = 0x92
    CMD_DEFINE_PROG_1_5 = 0x93
    CMD_DEFINE_PROG_6_10 = 0x94
    CMD_START_PROG = 0x95
    CMD_STOP_PROG = 0x96

    SET_TYPE_CURRENT = 0x01
    SET_TYPE_POWER = 0x02
    SET_TYPE_RESISTANCE = 0x03

    FRAME_LENGTH = 26

    # Description of data structures for various packet types
    STRUCT_FRONT = struct.Struct(b'< 3B 23x')
    STRUCT_SET_PARAMETERS = struct.Struct(b'< 2H 2B H 14x')
    STRUCT_READ_VALUES_OUT = struct.Struct(b'< 22x')
    STRUCT_READ_VALUES_IN = struct.Struct(b'< 3B H I 4H B 7x B')
    STRUCT_LOAD_STATE = struct.Struct(b'< B 21x')
    STRUCT_DEFINE_PROG_LOW = struct.Struct(b'< 2B 10H')
    STRUCT_DEFINE_PROG_HIGH = struct.Struct(b'< 10H B x')
    STRUCT_START_PROGRAM = struct.Struct(b'< 22x')
    STRUCT_STOP_PROGRAM = struct.Struct(b'< 22x')
    STRUCT_CHECKSUM = struct.Struct(b'< B')

    # Offsets for packing partial structs
    OFFSET_FRONT = 0
    OFFSET_PAYLOAD = 3
    OFFSET_CHECKSUM = 25

    def __init__(self, address, serial_connection, print_errors=True):
        """
        Require passing in serial_connection, because multiple Loads can exist
        with different addresses on a single serial port.

        :param address: Load address (0x00-0xFE)
        :param serial_connection: Serial Connection from serial.Serial()
        :return: None
        """
        # Serial Comm Packets are all 26 byte frames.
        # out_buffer for building data to send, in_buffer for consuming responses.
        self.__out_buffer = ctypes.create_string_buffer(self.FRAME_LENGTH)
        self.__in_buffer = ctypes.create_string_buffer(self.FRAME_LENGTH)

        self.address = address
        self.serial = serial_connection

        self._max_current = 30000
        self._max_power = 2000
        self._load_mode = self.SET_TYPE_RESISTANCE
        self._load_value = 500
        self._current = 0
        self._power = 0
        self._voltage = 0
        self._resistance = 0
        self._remote_control = 0
        self._load_on = 0
        self.wrong_polarity = 0
        self.excessive_temp = 0
        self.excessive_voltage = 0
        self.excessive_power = 0
        self.print_errors = print_errors
        self.update_status()

    # Note: Internally, all values are stored as integer values
    # in the format of the load interface.
    #
    # Ex: current is stored in mA, but public IO is Amps
    #     power is stored in tenths of Watts, but public IO is Watts.
    #
    # Conversion is done on getter and setter methods.

    @property
    def max_current(self):
        """
        Max Current (in Amps) allowed to be set by load.
        Rounds to nearest mA.
        """
        return self._max_current / 1000

    @max_current.setter
    def max_current(self, current_amps):
        new_val = int(round(current_amps * 1000, 0))
        if not 0 <= new_val <= 30000:
            raise ValueError("Max Current should be between 0-30A")
        self._max_current = new_val
        self.__set_parameters()

    @property
    def max_power(self):
        """
        Max Power (in Watts) allowed to be set by load.
        Rounds to nearest 0.1W
        """
        return self._max_power / 10

    @max_power.setter
    def max_power(self, power_watts):
        new_val = int(round(power_watts * 10, 0))
        if not 0 <= new_val <= 2000:
            raise ValueError("Max Power should be between 0-200W")
        self._max_power = new_val
        self.__set_parameters()

    def set_load_resistance(self, resistance):
        """
        Changes load to resistance mode and sets resistance value.
        Rounds to nearest 0.01 Ohms

        :param resistance: Load Resistance in Ohms (0-500 ohms)
        :return: None
        """
        new_val = int(round(resistance * 100))
        if not 0 <= new_val <= 50000:
            raise ValueError("Load Resistance should be between 0-500 ohms")
        self._load_mode = self.SET_TYPE_RESISTANCE
        self._load_value = new_val
        self.__set_parameters()

    def set_load_power(self, power_watts):
        """
        Changes load to power mode and sets power value.
        Rounds to nearest 0.1W.

        :param power_watts: Power in Watts (0-200)
        :return:
        """
        new_val = int(round(power_watts * 10))
        if not 0 <= new_val <= 2000:
            raise ValueError("Load Power should be between 0-200 W")
        self._load_mode = self.SET_TYPE_POWER
        self._load_value = new_val
        self.__set_parameters()

    def set_load_current(self, current_amps):
        """
        Changes load to current mode and sets current value.
        Rounds to nearest mA.

        :param current_amps: Current in Amps (0-30A)
        :return: None
        """
        new_val = int(round(current_amps * 1000))
        if not 0 <= new_val <= 30000:
            raise ValueError("Load Current should be between 0-30A")
        self._load_mode = self.SET_TYPE_CURRENT
        self._load_value = new_val
        self.__set_parameters()

    @property
    def current(self):
        """
        Current value (in Amps) obtained during last update_status call.
        """
        return self._current / 1000

    @property
    def power(self):
        """
        Power value (in Watts) obtained during last update_status call.
        """
        return self._power / 10

    @property
    def resistance(self):
        """
        Resistance value (in ohms) obtained during last update_status call.
        """
        return self._resistance / 100

    @property
    def voltage(self):
        """
        Voltage value (in Volts) obtained during last update_status call.
        """
        return self._voltage / 1000

    @property
    def remote_control(self):
        """
        Remote control enabled
        """
        return self._remote_control == 1

    @remote_control.setter
    def remote_control(self, value):
        new_val = 0
        if value:
            new_val = 1
        if new_val != self._remote_control:
            self._remote_control = new_val
            self.__set_load_state()

    @property
    def load_on(self):
        """
        Load enabled state
        """
        return self._load_on == 1

    @load_on.setter
    def load_on(self, value):
        new_val = 0
        if value:
            new_val = 1
        if new_val != self._load_on:
            self._load_on = new_val
            self.__set_load_state()

    def __set_buffer_start(self, command):
        """
        This sets the first three bytes and clears the other 23 bytes.
        :param command: Command Code to set
        :return: None
        """
        self.STRUCT_FRONT.pack_into(self.__out_buffer, self.OFFSET_FRONT, 0xAA, self.address, command)

    @staticmethod
    def __get_checksum(byte_str):
        """
        Calculates checksum of string, excluding last character.
        Checksum is generated by summing all byte values, except last,
        and taking lowest byte of result.

        :param byte_str: string to checksum, plus extra character on end
        :return: checksum value as int
        """
        return sum(byte2int(x) for x in byte_str[:-1]) % 256

    def __set_checksum(self):
        """
        Sets the checksum on the last byte of buffer,
        based on values in the buffer
        :return: None
        """
        checksum = self.__get_checksum(self.__out_buffer.raw)
        self.STRUCT_CHECKSUM.pack_into(self.__out_buffer, self.OFFSET_CHECKSUM, checksum)

    def __is_valid_checksum(self, byte_str):
        """
        Verifies last byte checksum of full packet
        :param byte_str: byte string message
        :return: boolean
        """
        return byte2int(byte_str[-1]) == self.__get_checksum(byte_str)

    def __clear_in_buffer(self):
        """
        Zeros out the in buffer
        :return: None
        """
        self.__in_buffer.value = bytes(b'\0' * len(self.__in_buffer))

    def __send_buffer(self):
        """
        Sends the contents of self.__out_buffer to serial device
        :return: Number of bytes written
        """
        bytes_written = self.serial.write(self.__out_buffer.raw)
        if self.DEBUG_MODE:
            print("Wrote: '{}'".format(binascii.hexlify(self.__out_buffer.raw)))
        if bytes_written != len(self.__out_buffer):
            raise IOError("{} bytes written for output buffer of size {}".format(bytes_written,
                                                                                 len(self.__out_buffer)))
        return bytes_written

    def __send_receive_buffer(self):
        """
        Performs a send of self.__out_buffer and then an immediate read into self.__in_buffer

        :return: None
        """
        self.__clear_in_buffer()
        self.__send_buffer()
        read_string = self.serial.read(len(self.__in_buffer))
        if self.DEBUG_MODE:
            print("Read: '{}'".format(binascii.hexlify(read_string)))
        if len(read_string) != len(self.__in_buffer):
            raise IOError("{} bytes received for input buffer of size {}".format(len(read_string),
                                                                                 len(self.__in_buffer)))
        if not self.__is_valid_checksum(read_string):
            raise IOError("Checksum validation failed on received data")
        self.__in_buffer.value = read_string

    def __set_parameters(self):
        """
        Sets Load Parameters from class values, including:
        Max Current, Max Power, Address, Load Mode, Load Value

        :return: None
        """
        self.__set_buffer_start(self.CMD_SET_PARAMETERS)
        # Can I send 0xFF as address to not change it each time?
        # Worry about writing to EEPROM or Flash with each address change.
        # Would then implement a separate address only change function.
        self.STRUCT_SET_PARAMETERS.pack_into(self.__out_buffer, self.OFFSET_PAYLOAD,
                                             self._max_current, self._max_power, self.address,
                                             self._load_mode, self._load_value)
        self.__set_checksum()
        self.__send_buffer()
        self.update_status()

    def update_status(self, retry_count=2):
        """
        Updates current values from load.
        Must be called to get latest values for the following properties of class:
          current
          voltage
          power
          max current
          max power
          resistance
          local_control
          load_on
          wrong_polarity
          excessive_temp
          excessive_voltage
          excessive_power

        :param retry_count: Number of times to ignore IOErrors and retry update
        :return: None
        """
        # I think retry should be in here.
        # Throw exceptions in __update_status and handle here
        cur_count = max(retry_count, 0)
        while cur_count >= 0:
            try:
                self.__update_status()
            except IOError as err:
                if self.print_errors:
                    print("IOError: {}".format(err))
            else:
                if not self.__is_valid_checksum(self.__in_buffer.raw):
                    if self.print_errors:
                        raise IOError("Checksum validation failed.")
                values = self.STRUCT_READ_VALUES_IN.unpack_from(self.__in_buffer, self.OFFSET_FRONT)
                (self._current,
                 self._voltage,
                 self._power,
                 self._max_current,
                 self._max_power,
                 self._resistance,
                 output_state) = values[3:-1]

                self._remote_control = (output_state & 0b00000001) > 0
                self._load_on = (output_state & 0b00000010) > 0
                self.wrong_polarity = (output_state & 0b00000100) > 0
                self.excessive_temp = (output_state & 0b00001000) > 0
                self.excessive_voltage = (output_state & 0b00010000) > 0
                self.excessive_power = (output_state & 0b00100000) > 0
                return None
            cur_count -= 1
        raise IOError("Retry count exceeded with serial IO.")

    def __update_status(self):
        self.__set_buffer_start(self.CMD_READ_VALUES)
        self.STRUCT_READ_VALUES_OUT.pack_into(self.__out_buffer, 3)
        self.__set_checksum()
        self.__send_receive_buffer()

    def __set_load_state(self):
        # Remote Control is bit 2
        flags = self._remote_control << 1
        # Load On is bit 1
        flags |= self._load_on
        self.__set_buffer_start(self.CMD_LOAD_STATE)
        self.STRUCT_LOAD_STATE.pack_into(self.__out_buffer, self.OFFSET_PAYLOAD, flags)
        self.__set_checksum()
        self.__send_buffer()

    def set_program_sequence(self, array_program):
        """
        Sets program up in load.
        :param array_program: Populated Array3710Program object
        :return: None
        """
        self.__set_buffer_start(self.CMD_DEFINE_PROG_1_5)
        array_program.load_buffer_one_to_five(self.__out_buffer)
        self.__set_checksum()
        self.__send_buffer()

        self.__set_buffer_start(self.CMD_DEFINE_PROG_6_10)
        array_program.load_buffer_six_to_ten(self.__out_buffer)
        self.__set_checksum()
        self.__send_buffer()

    def start_program(self, turn_on_load=True):
        """
        Starts running programmed test sequence
        :return: None
        """
        self.__set_buffer_start(self.CMD_START_PROG)
        self.__set_checksum()
        self.__send_buffer()
        # Turn on Load if not on
        if turn_on_load and not self.load_on:
            self.load_on = True

    def stop_program(self, turn_off_load=True):
        """
        Stops running programmed test sequence
        :return: None
        """
        self.__set_buffer_start(self.CMD_STOP_PROG)
        self.__set_checksum()
        self.__send_buffer()
        if turn_off_load and self.load_on:
            self.load_on = False


class SerialTester(object):
    """
    Simple object to stub the calls I'm using to serial.Serial created
    object, with some packet knowledge to assist in testing.
    """
    def __init__(self, port=None, baudrate=9600, bytesize=8, parity='N',
                 stopbits=1, timeout=None, xonxoff=False, rtscts=False,
                 writeTimeout=None, dsrdtr=False, interCharTimeout=None):
        self.timeout = timeout
        if not timeout:
            self.timeout = 0
        print("Faking Serial")
        print("  port: {}".format(port))
        print("  baudrate: {}".format(baudrate))
        print("  bytesize: {}".format(bytesize))
        print("  parity: {}".format(parity))
        print("  stopbits: {}".format(stopbits))
        print("  timeout: {}".format(timeout))
        print("  xonxoff: {}".format(xonxoff))
        print("  rtscts: {}".format(rtscts))
        print("  writeTimeout: {}".format(writeTimeout))
        print("  dsrdtr: {}".format(dsrdtr))
        print("  interCharTimeout: {}".format(interCharTimeout))
        self.__last_command = 0
        self.__read_buffer = ''

    @staticmethod
    def __decode_message(data_str):
        """
        Unpacks data packet into proper data values
        :param data_str: 26 byte string of packet data
        :return: tuple packed with valid data in string
        """
        structs = {0x90: b"< 3B 2H 2B H 14x B",
                   0x91: b"< 3B 22x B",
                   0x92: b"< 3B B 21x B",
                   0x93: b"< 3B 2B 10H B",
                   0x94: b"< 3B 10H B x B",
                   0x95: b"< 3B 22x B",
                   0x96: b"< 3B 22x B"}
        cmd_code = byte2int(data_str[2])
        return struct.unpack(structs[cmd_code], data_str)

    def write(self, data_str):
        """
        Simulator for serial write.
        Prints data and decoded values.

        :param data_str: string to write
        :return: number of bytes given
        """
        cmd_code = byte2int(data_str[2])
        if cmd_code == 0x91:
            self.__read_buffer = b'\xAA\x00\x91\x00\x00\x00\x00\x00\x00\x00\x00\x30\x75\xD0\x07\x50\xC3\x00\x01\x00\x00\x00\x00\x50\xC3\xDE'
        print("Serial Write: ", binascii.hexlify(data_str))
        print(self.__decode_message(data_str))
        return len(data_str)

    def read(self, length=1):
        """
        Returns hard coded string if a 0x91 command
        was sent to write prior to calling read.

        Otherwise, returns empty string.

        :param length: length to read
        :return: byte_string
        """
        response = ''
        if self.__read_buffer:
            if length <= len(self.__read_buffer):
                response = self.__read_buffer[:length]
                self.__read_buffer = self.__read_buffer[length:]
            else:
                response = self.__read_buffer
                self.__read_buffer = ''
            print("Serial read, hard coded 0x91 data")
            return response
        print("Serial read when no data available, timing out then returning ''")
        time.sleep(self.timeout)
        return response

    def close(self):
        pass

if __name__ == '__main__':

    import time

    serial_conn = SerialTester('COM4', 9600, timeout=1)
    test_load = Load(0, serial_conn)
    test_load.remote_control = True
    test_load.set_load_current(10)
    test_load.set_load_power(20)
    test_load.set_load_resistance(30)
    test_load.update_status()
    test_load.load_on = True
    test_load.load_off = True

    # Enter Program
    prog = Program(Program.PROG_TYPE_RESISTANCE, Program.RUN_ONCE)
    resistances = (500, 450, 400, 350, 300, 250, 200, 150, 100, 50)
    for resist in resistances:
        prog.add_step(resist, 10)
    test_load.set_program_sequence(prog)
    test_load.load_on = True
    test_load.start_program()
    time.sleep(1)
    test_load.stop_program()

    test_load.remote_control = False
    serial_conn.close()