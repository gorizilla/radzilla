# pcf85063.py – minimal driver for the PCF85063A real-time clock (I2C 0x51).
#
# RadZilla – external display for RadiaCode
# Copyright (c) 2026 Shimizilla – licensed under CC BY-NC 4.0 (see LICENSE.md)
#
# Time is stored as local time (CET/CEST), see ntp.py.


def _bcd2dec(b):
    return (b >> 4) * 10 + (b & 0x0F)


def _dec2bcd(d):
    return ((d // 10) << 4) | (d % 10)


class PCF85063:
    REG_SECONDS = 0x04

    def __init__(self, i2c, addr=0x51):
        self.i2c = i2c
        self.addr = addr

    def datetime(self):
        """Return ((year, month, day, hour, minute, second), valid).
        valid is False if the oscillator had stopped (time unknown)."""
        d = self.i2c.readfrom_mem(self.addr, self.REG_SECONDS, 7)
        valid = not (d[0] & 0x80)          # OS flag (oscillator stop)
        sec = _bcd2dec(d[0] & 0x7F)
        minute = _bcd2dec(d[1] & 0x7F)
        hour = _bcd2dec(d[2] & 0x3F)
        day = _bcd2dec(d[3] & 0x3F)
        month = _bcd2dec(d[5] & 0x1F)
        year = 2000 + _bcd2dec(d[6])
        return (year, month, day, hour, minute, sec), valid

    def set_datetime(self, year, month, day, hour, minute, second, weekday=0):
        """Set the clock (weekday 0 = Sunday). Also clears the OS flag."""
        data = bytes((
            _dec2bcd(second) & 0x7F,
            _dec2bcd(minute),
            _dec2bcd(hour),
            _dec2bcd(day),
            weekday & 0x07,
            _dec2bcd(month),
            _dec2bcd(year - 2000),
        ))
        self.i2c.writeto_mem(self.addr, self.REG_SECONDS, data)
