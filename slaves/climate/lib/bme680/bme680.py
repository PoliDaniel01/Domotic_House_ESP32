import time
import struct
from micropython import const

_BME680_CHIPID = const(0x61)
_BME680_REG_CHIPID = const(0xD0)
_BME680_BME680_COEFF_ADDR1 = const(0x89)
_BME680_BME680_COEFF_ADDR2 = const(0xE1)
_BME680_BME680_RES_HEAT_0 = const(0x5A)
_BME680_BME680_GAS_WAIT_0 = const(0x64)
_BME680_REG_SOFTRESET = const(0xE0)
_BME680_REG_CTRL_GAS = const(0x71)
_BME680_REG_CTRL_MEAS = const(0x74)
_BME680_REG_CONFIG = const(0x75)
_BME680_REG_MEAS_STATUS = const(0x1D)
_BME680_SAMPLERATES = (0, 1, 2, 4, 8, 16)

def _read24(arr):
    ret = 0.0
    for b in arr:
        ret *= 256.0
        ret += float(b & 0xFF)
    return ret

class Adafruit_BME680:
    def __init__(self, *, refresh_rate=10):
        self._write(_BME680_REG_SOFTRESET, [0xB6])
        time.sleep(0.005)
        chip_id = self._read_byte(_BME680_REG_CHIPID)
        if chip_id != _BME680_CHIPID:
            raise RuntimeError("Failed 0x%x" % chip_id)
        self._read_calibration()
        self._write(_BME680_BME680_RES_HEAT_0, [0x73])
        self._write(_BME680_BME680_GAS_WAIT_0, [0x65])
        self._temp_oversample = 0b100
        self._filter = 0b010
        self._adc_temp = None
        self._t_fine = None
        self._last_reading = 0
        self._min_refresh_time = 1000 / refresh_rate

    @property
    def temperature(self):
        self._perform_reading()
        calc_temp = (((self._t_fine * 5) + 128) / 256)
        return calc_temp / 100

    def _perform_reading(self):
        if time.ticks_diff(time.ticks_ms(), self._last_reading) < self._min_refresh_time:
            return
        self._write(_BME680_REG_CONFIG, [self._filter << 2])
        self._write(_BME680_REG_CTRL_MEAS, [(self._temp_oversample << 5)])
        self._write(_BME680_REG_CTRL_GAS, [0x10])
        ctrl = self._read_byte(_BME680_REG_CTRL_MEAS)
        ctrl = (ctrl & 0xFC) | 0x01
        self._write(_BME680_REG_CTRL_MEAS, [ctrl])
        new_data = False
        while not new_data:
            data = self._read(_BME680_REG_MEAS_STATUS, 15)
            new_data = data[0] & 0x80 != 0
            time.sleep(0.005)
        self._last_reading = time.ticks_ms()
        self._adc_temp = _read24(data[5:8]) / 16
        var1 = (self._adc_temp / 8) - (self._temp_calibration[0] * 2)
        var2 = (var1 * self._temp_calibration[1]) / 2048
        var3 = ((var1 / 2) * (var1 / 2)) / 4096
        var3 = (var3 * self._temp_calibration[2] * 16) / 16384
        self._t_fine = int(var2 + var3)

    def _read_calibration(self):
        coeff = self._read(_BME680_BME680_COEFF_ADDR1, 25)
        coeff += self._read(_BME680_BME680_COEFF_ADDR2, 16)
        coeff = list(struct.unpack('<hbBHhbBhhbbHhhBBBHbbbBbHhbb', bytes(coeff[1:39])))
        coeff = [float(i) for i in coeff]
        self._temp_calibration = [coeff[x] for x in [23, 0, 1]]

    def _read_byte(self, register):
        return self._read(register, 1)[0]

    def _read(self, register, length):
        raise NotImplementedError()

    def _write(self, register, values):
        raise NotImplementedError()

class BME680_I2C(Adafruit_BME680):
    def __init__(self, i2c, address=0x77, debug=False, *, refresh_rate=10):
        self._i2c = i2c
        self._address = address
        self._debug = debug
        super().__init__(refresh_rate=refresh_rate)

    def _read(self, register, length):
        result = bytearray(length)
        self._i2c.readfrom_mem_into(self._address, register & 0xff, result)
        if self._debug:
            print("\t${:x} read ".format(register), " ".join(["{:02x}".format(i) for i in result]))
        return result

    def _write(self, register, values):
        if self._debug:
            print("\t${:x} write".format(register), " ".join(["{:02x}".format(i) for i in values]))
        self._i2c.writeto_mem(self._address, register, bytes(values))
