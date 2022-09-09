# SPDX-FileCopyrightText: 2017 Scott Shawcroft, written for Adafruit Industries
# SPDX-FileCopyrightText: Copyright (c) 2022 Cyril Stoller
#
# SPDX-License-Identifier: MIT
"""
`adafruit_tmf8821`
================================================================================


.. todo:: Describe what the library does.


* Author(s): Cyril Stoller

Implementation Notes
--------------------

**Hardware:**

.. todo:: Add links to any specific hardware product page(s), or category page(s).
  Use unordered list & hyperlink rST inline format: "* `Link Text <url>`_"

**Software and Dependencies:**

* Adafruit CircuitPython firmware for the supported boards:
  https://circuitpython.org/downloads

.. todo:: Uncomment or remove the Bus Device and/or the Register library dependencies
  based on the library's use of either.

# * Adafruit's Bus Device library: https://github.com/adafruit/Adafruit_CircuitPython_BusDevice
# * Adafruit's Register library: https://github.com/adafruit/Adafruit_CircuitPython_Register
"""

# imports

__version__ = "0.0.0+auto.0"
__repo__ = "https://github.com/stocyr/Adafruit_CircuitPython_TMF8821.git"

from micropython import const

from adafruit_bus_device import i2c_device
from tof_image import _tof_image

try:
    from typing import Optional, List
except ImportError:
    pass
from busio import I2C

# Registers:

# For any appid, any cid_rid – Registers always available
_TMF882X_REG_APPID = const(0x00)  # appid
_TMF882X_REG_MINOR = const(0x01)  # minor
_TMF882X_REG_ENABLE = const(0xE0)  # 0 cpu_ready powerup_select pon
_TMF882X_REG_INT_STATUS = const(0xE1)  # 0 int7 int6 0 int4 0 int2 0
_TMF882X_REG_INT_ENAB = const(0xE2)  # 0 int7_enable int6_enable 0 int4_enable 0 int2_enable 0
_TMF882X_REG_ID = const(0xE3)  # Chip ID, reads 08h – do not rely on register bits 6 and 7 of this register.

# If appid=0x03, any cid_rid, the following describe Main Application Register
_TMF882X_REG_PATCH = const(0x02)  # patch
_TMF882X_REG_BUILD_TYPE = const(0x03)  # build
_TMF882X_REG_APPLICATION_STATUS = const(0x04)  # app_status
_TMF882X_REG_MEASURE_STATUS = const(0x05)  # measure_status
_TMF882X_REG_ALGORITHM_STATUS = const(0x06)  # alg_status
_TMF882X_REG_CALIBRATION_STATUS = const(0x07)  # fc_status
_TMF882X_REG_CMD_STAT = const(0x08)  # cmd_stat
_TMF882X_REG_PREV_CMD = const(0x09)  # prev_cmd
_TMF8828_REG_MODE = const(0x10)  # (TMF8828 ONLY) mode
_TMF882X_REG_LIVE_BEAT = const(0x0A)  # live_beat
_TMF882X_REG_LIVE_GPIO = const(0x0B)  # live_gpio1 live_gpio0
_TMF882X_REG_SERIAL_NUMBER_0 = const(0x1C)  # serial_number[7:0]
_TMF882X_REG_SERIAL_NUMBER_1 = const(0x1D)  # serial_number[15:8]
_TMF882X_REG_SERIAL_NUMBER_2 = const(0x1E)  # serial_number[23:16]
_TMF882X_REG_SERIAL_NUMBER_3 = const(0x1F)  # serial_number[31:24]
_TMF882X_REG_CONFIG_RESULT = const(0x20)  # cid_rid
_TMF882X_REG_TID = const(0x21)  # tid
_TMF882X_REG_SIZE_LSB = const(0x22)  # size[7:0]
_TMF882X_REG_SIZE_MSB = const(0x23)  # size[15:8]

# If appid=0x03, cid_rid=0x10, the following describe Measurement Results
_TMF882X_REG_RESULT_NUMBER = const(0x24)  # number
_TMF882X_REG_TEMPERATURE = const(0x25)  # temperature
_TMF882X_REG_NUMBER_VALID_RESULTS = const(0x26)  # valid_results
_TMF882X_REG_AMBIENT_LIGHT_0 = const(0x28)  # ambient[7:0]
_TMF882X_REG_AMBIENT_LIGHT_1 = const(0x29)  # ambient[15:8]
_TMF882X_REG_AMBIENT_LIGHT_2 = const(0x2A)  # ambient[23:16]
_TMF882X_REG_AMBIENT_LIGHT_3 = const(0x2B)  # ambient[31:24]
_TMF882X_REG_PHOTON_COUNT_0 = const(0x2C)  # photon_count[7:0]
_TMF882X_REG_PHOTON_COUNT_1 = const(0x2D)  # photon_count[15:8]
_TMF882X_REG_PHOTON_COUNT_2 = const(0x2E)  # photon_count[23:16]
_TMF882X_REG_PHOTON_COUNT_3 = const(0x2F)  # photon_count[31:24]
_TMF882X_REG_REFERENCE_COUNT_0 = const(0x30)  # reference_count[7:0]
_TMF882X_REG_REFERENCE_COUNT_1 = const(0x31)  # reference_count[15:8]
_TMF882X_REG_REFERENCE_COUNT_2 = const(0x32)  # reference_count[23:16]
_TMF882X_REG_REFERENCE_COUNT_3 = const(0x33)  # reference_count[31:24]
_TMF882X_REG_SYS_TICK_0 = const(0x34)  # sys_tick[7:0]
_TMF882X_REG_SYS_TICK_1 = const(0x35)  # sys_tick[15:8]
_TMF882X_REG_SYS_TICK_2 = const(0x36)  # sys_tick[23:16]
_TMF882X_REG_SYS_TICK_3 = const(0x37)  # sys_tick[31:24]
_TMF882X_REG_RES_CONFIDENCE_i = list(range(0x38, 0xA1 + 1, 3))  # confidence[i]
_TMF882X_REG_RES_DISTANCE_i_LSB = list(range(0x39, 0xA2 + 1, 3))  # distance[i][7:0]
_TMF882X_REG_RES_DISTANCE_i_MSB = list(range(0x3A, 0xA3 + 1, 3))  # distance[i][15:8]

# If appid=0x03, cid_rid=0x16, the following describe Configuration Page
_TMF882X_REG_PERIOD_MS_LSB = const(0x24)  # period[7:0]
_TMF882X_REG_PERIOD_MS_MSB = const(0x25)  # period[15:8]
_TMF882X_REG_KILO_ITERATIONS_LSB = const(0x26)  # iterations[7:0]
_TMF882X_REG_KILO_ITERATIONS_MSB = const(0x27)  # iterations[15:8]
_TMF882X_REG_INT_THRESHOLD_LOW_LSB = const(0x28)  # int_threshold_low[7:0]
_TMF882X_REG_INT_THRESHOLD_LOW_MSB = const(0x29)  # int_threshold_low[15:8]
_TMF882X_REG_INT_THRESHOLD_HIGH_LSB = const(0x2A)  # int_threshold_high[7:0]
_TMF882X_REG_INT_THRESHOLD_HIGH_MSB = const(0x2B)  # int_threshold_high[15:8]
_TMF882X_REG_INT_ZONE_MASK_0 = const(0x2C)  # int_zone_mask[7:0]
_TMF882X_REG_INT_ZONE_MASK_1 = const(0x2D)  # int_zone_mask[15:8]
_TMF882X_REG_INT_ZONE_MASK_2 = const(0x2E)  # int_zone_mask[17:16]
_TMF882X_REG_INT_PERSISTENCE = const(0x2F)  # int_persistence
_TMF882X_REG_CONFIDENCE_THRESHOLD = const(0x30)  # confidence_threshold
_TMF882X_REG_GPIO_0 = const(0x31)  # driver_strength0 pre_delay0 gpio0
_TMF882X_REG_GPIO_1 = const(0x32)  # driver_strength1 pre_delay1 gpio1
_TMF882X_REG_POWER_CFG = const(
    0x33)  # goto_standby_timed low_power_osc_on keep_pll_running allow_osc_retrim pulse_interrupt
_TMF882X_REG_SPAD_MAP_ID = const(0x34)  # spad_map_id
_TMF882X_REG_ALG_SETTING_0 = const(0x35)  # logarithmic_confidence distance_mode distances
# _TMF882X_REG_Reserved = const(0x38)  # – keep at 0
_TMF882X_REG_HIST_DUMP = const(0x39)  # histogram
# _TMF882X_REG_Reserved = const(0x3A)  # – keep at 0
_TMF882X_REG_I2C_SLAVE_ADDRESS = const(0x3B)  # 7bit_slave_address 0
_TMF882X_REG_OSC_TRIM_VALUE_LSB = const(0x3C)  # osc_trim_value[7:0]
_TMF882X_REG_OSC_TRIM_VALUE_MSB = const(0x3D)  # osc_trim_value[8]
_TMF882X_REG_I2C_ADDR_CHANGE = const(0x3E)  # gpio_change_mask gpio_change_value

# If appid=0x03, cid_rid=0x17/0x18, the following describe User defined SPAD Configuration
_TMF882X_REG_SPAD_ENABLE_FIRST = const(0x24)  # spad_enable_first
_TMF882X_REG_SPAD_ENABLE_LAST = const(0x41)  # spad_enable_last
_TMF882X_REG_SPAD_TDC_FIRST = const(0x42)  # spad_tdc_first
_TMF882X_REG_SPAD_TDC_LAST = const(0x8C)  # spad_tdc_last
_TMF882X_REG_SPAD_X_OFFSET_2 = const(0x8D)  # x_offset_2
_TMF882X_REG_SPAD_Y_OFFSET_2 = const(0x8E)  # y_offset_2
_TMF882X_REG_SPAD_X_SIZE = const(0x8F)  # x_size
_TMF882X_REG_SPAD_Y_SIZE = const(0x90)  # y_size

# If appid=0x03, cid_rid=0x19, the following describe Factory Calibration
_TMF882X_REG_FACTORY_CALIBRATION_FIRST = const(0x24)  # factory_calibration_first – see section 7.3
_TMF882X_REG_CROSSTALK_ZONE_i = [list(range(0x60 + 4 * i, 0x060 + 4 * (i + 1))) for i in
                                 range(36)]  # crosstalk_amplitude_zone[i], 32-bit value, LSB first (little-endian)
_TMF882X_REG_CROSSTALK_ZONE_i_TMUX = [list(range(0xB8 + 4 * i, 0xB8 + 4 * (i + 1))) for i in range(
    36)]  # crosstalk_amplitude_zone[i] time muxed, 32-bit value, LSB first (little-endian) – for 4x4 mode this represents the zone 10 as described in section 7.4.3
_TMF882X_REG_CALIBRATION_STATUS_FC = const(
    0xDC)  # fc_status_during_cal - calibration status during factory calibration – copy of register 0x07 – 0x00 success, all other values are reporting an error during calibration
_TMF882X_REG_FACTORY_CALIBRATION_LAST = const(0xDF)  # factory_calibration_last

# If appid=0x03, cid_rid=0x81, the following describe Raw data Histogram
_TMF882X_REG_SUBPACKET_NUMBER = const(0x24)  # subpacket_number
_TMF882X_REG_SUBPACKET_PAYLOAD = const(0x25)  # subpacket_payload
_TMF882X_REG_SUBPACKET_CONFIG = const(0x26)  # subpacket_config
_TMF882X_REG_SUBPACKET_DATA_i = list(range(0x27, 0xA6 + 1))  # subpacket_data[i]

# If appid=0x80, the following describe Bootloader Registers
_TMF882X_REG_BL_ROM_VERSION = const(0x01)  # bootloader revision (aka ROM version) -> 0x26 = v1, 0x29 = v2
_TMF882X_REG_BL_CMD_STAT = const(0x08)  # bl_cmd_stat
_TMF882X_REG_BL_SIZE = const(0x09)  # bl_size
_TMF882X_REG_BL_DATA_START = const(
    0x0A)  # bl_data0 … bl_data127 - size depends on bl_cmd_stat – can be from 0 to 128. The checksum BL_CSUM is right after data

# Internal constants:
_TMF882X_DEFAULT_I2C_ADDR = const(0x41)

_TMF882X_MODE_BOOTLOADER = const(0x80)
_TMF882X_MODE_APP = const(0x03)
_app_id_name = {_TMF882X_MODE_BOOTLOADER: 'BTL', _TMF882X_MODE_APP: 'APP'}

_TMF882X_CHIP_ID = const(0x08)
_TMF882X_CHIP_ID_VALID_MASK = const(0x3F)
_TMF882X_ROM_V2 = const(0x29)

_TMF882X_DOWNLOAD_INIT = const(0x14)
_TMF882X_SET_ADDR = const(0x43)
_TMF882X_W_RAM = const(0x41)
_TMF882X_RAMREMAP_RESET = const(0x11)
_TMF882X_STAT_OK = const(0x00)
_TMF882X_STAT_ACCEPTED = const(0x01)

_TMF882X_FW_ADDR = const(0x20000000)  # Note, only the last 16 bit are respected
_TMF882X_MAX_DATA = const(100)


# User-facing constants:


class TMF8821:
    def __init__(self, i2c: I2C, address: int = _TMF882X_DEFAULT_I2C_ADDR) -> None:
        self._device = i2c_device.I2CDevice(i2c, address)
        self._sample_delay_ms = 0

        # Check if chip is responding and ID matches datasheet
        if self._read_byte(_TMF882X_REG_ID) & _TMF882X_CHIP_ID_VALID_MASK != _TMF882X_CHIP_ID:
            raise Exception('TMF882X chip ID doesn''t match!')

        # Power up the device
        en_reg = self._read_byte(_TMF882X_REG_ENABLE)
        # print(f'Enable register reads back as 0b{en_reg:08b}')
        i_timeout = 0
        while en_reg & 0x41 != 0x41:
            print(f'Waiting for start up, enable register = 0b{en_reg:08b}')
            print(f'lower nibble: 0b{en_reg & 0x0F:04b}')
            # Wait for CPU to start up
            if en_reg & 0x0F == 0b0001:
                # CPU is currently in the process of initializing HW and SW
                continue
            elif en_reg & 0x0F == 0b0010:
                # Device is in STANDBY mode
                self._write_byte(_TMF882X_REG_ENABLE, en_reg | 0x01)  # set bit 0, leave the rest
            elif en_reg & 0x0F == 0b0110:
                # Device is in STANDBY_TIMED mode and will wake up due to the measurement timer expires
                # or the host can force the device to wake-up
                self._write_byte(_TMF882X_REG_CMD_STAT, 0xFF)  # Send stop command to interrupt measurement and go IDLE
            en_reg = self._read_byte(_TMF882X_REG_ENABLE)
            i += 1
            if i > 20:
                raise Exception('Timeout while waiting for startup')

        # CPU is ready to communicate. First ask about the state (bootloader / app)
        self.app_id = self._read_byte(_TMF882X_REG_APPID)

        # If the application is already running, skip firmware download
        if self.app_id == _TMF882X_MODE_APP:
            minor, patch = self._read_bytes(_TMF882X_REG_MINOR, 2)
            print(f'App v{minor}.{patch} running.')
            return

        # If bootloader is running, verify ROM v2
        _, rom_version = self._read_bytes(_TMF882X_REG_APPID, 2)
        if rom_version != _TMF882X_ROM_V2:
            raise Exception(f'TMF882X ROM version != 2! Register reads {rom_version:#0x}')

        # Download firmware

        # Initiate firmware reception
        self._write_command(_TMF882X_DOWNLOAD_INIT, bytes(b"\x29"))
        self._wait_for_bl_ready()
        # Set destination write address
        self._write_command(_TMF882X_SET_ADDR, bytes([(_TMF882X_FW_ADDR >> 8) & 0xFF, _TMF882X_FW_ADDR & 0xFF]))
        self._wait_for_bl_ready()

        num_downloaded = 0
        print('Downloading firmware: [', end='')
        while num_downloaded < len(_tof_image):
            chunk_bytes = min(_TMF882X_MAX_DATA, len(_tof_image) - num_downloaded)
            data = _tof_image[num_downloaded:num_downloaded + chunk_bytes]
            self._write_command(_TMF882X_W_RAM, data)
            self._wait_for_bl_ready()
            num_downloaded += chunk_bytes
            print('=>\b', end='')
        print('] Done.')

        # Set powerup select to run from RAM
        self._write_byte(_TMF882X_REG_ENABLE, 0x21)  # set bit 0 (general enable) and bit 5 (run from RAM)
        self._write_command(_TMF882X_RAMREMAP_RESET, bytes())  # Instruct device to run firmware

        self.app_id = self._read_byte(_TMF882X_REG_APPID)
        if self.app_id == _TMF882X_MODE_APP:
            minor, patch = self._read_bytes(_TMF882X_REG_MINOR, 2)
            print(f'App v{minor}.{patch} running.')
        else:
            raise Exception('Device is still in bootloader mode after downloading firmware!')


    def _write_command(self, cmd: int, data: bytes, dryrun=False):
        checksum = ((cmd + len(data) + sum(data)) & 0x000000FF) ^ 0xFF
        if dryrun:
            print(f'Writing command:', ' '.join(map(hex, bytes([cmd, len(data)]) + data + bytes([checksum]))))
        else:
            self._write_bytes(_TMF882X_REG_BL_CMD_STAT, bytes([cmd, len(data)]) + data + bytes([checksum]))


    def _wait_for_bl_ready(self, verbose=False):
        while True:
            status = self._read_bytes(_TMF882X_REG_BL_CMD_STAT, 3)
            if verbose:
                print(f'Checking status:', " ".join(map(hex, status)))
            if status[0] == _TMF882X_STAT_OK:
                break
            if status[0] == _TMF882X_STAT_ACCEPTED:
                continue
            else:
                raise Exception(f'TMF882X returned erroneous status {" ".join(map(hex, status))}!')


    @property
    def sample_delay(self):
        return self._sample_delay_ms


    @sample_delay.setter
    def sample_delay(self, sample_delay_ms: int) -> None:
        # self._write_8(_VL6180X_REG_SYSRANGE_PART_TO_PART_RANGE_OFFSET, struct.pack("b", offset)[0])
        self._sample_delay_ms = sample_delay_ms


    def _read_byte(self, address: int) -> int:
        # Read and return a byte from the specified register address.
        with self._device as i2c:
            result = bytearray(1)
            i2c.write_then_readinto(bytes([address]), result)
            return result[0]


    def _read_bytes(self, address: int, length: int) -> bytes:
        # Read and return multiple bytes from the specified register address.
        with self._device as i2c:
            result = bytearray(length)
            i2c.write_then_readinto(bytes([address]), result)
            return result


    def _write_byte(self, address: int, data: int) -> None:
        # Write 1 byte of data from the specified 8-bit register address.
        with self._device as i2c:
            i2c.write(bytes([address, data]))


    def _write_bytes(self, address: int, data) -> None:
        # Write multiple bytes of data from the specified 8-bit register address.
        if type(data) is list:
            with self._device as i2c:
                i2c.write(bytes([address] + data))
        elif type(data) is bytes:
            with self._device as i2c:
                i2c.write(bytes([address]) + data)
