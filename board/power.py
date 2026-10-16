# power.py – power latch, PWR button and buzzer.
#
# RadZilla – external display for RadiaCode
# Copyright (c) 2026 Shimizilla – licensed under CC BY-NC 4.0 (see LICENSE.md)
#
# Power circuit (board V2): pressing PWR connects the battery. The firmware
# must then keep SYS_EN high; releasing SYS_EN cuts the battery supply.
# While on USB the board keeps running regardless of SYS_EN.
import time
from machine import Pin, PWM


class Power:
    def __init__(self, en_pin):
        self.en = Pin(en_pin, Pin.OUT, value=1)

    def hold(self):
        self.en(1)

    def release(self):
        self.en(0)


class Buzzer:
    """Passive buzzer. Blocking beep – only for short signals (shut-down).
    The application uses its own non-blocking beeps (see app.py)."""

    def __init__(self, pin):
        self.pin_no = pin
        Pin(pin, Pin.OUT, value=0)

    def beep(self, freq=2000, ms=100):
        p = PWM(Pin(self.pin_no), freq=freq, duty_u16=32768)
        time.sleep_ms(ms)
        p.deinit()
        Pin(self.pin_no, Pin.OUT, value=0)    # leave the pin LOW (no current)


class Button:
    """PWR button on SYS_OUT (LOW = pressed).

    Detects short, double and long presses. It only becomes active after the
    first release, so the press that switched the board on is not counted as
    a long press."""

    def __init__(self, pin, long_ms, double_ms, debounce_ms,
                 on_short=None, on_double=None, on_long=None):
        self.pin = Pin(pin, Pin.IN, Pin.PULL_UP)
        self.long_ms = long_ms
        self.double_ms = double_ms
        self.debounce_ms = debounce_ms
        self.on_short = on_short
        self.on_double = on_double
        self.on_long = on_long

        now = time.ticks_ms()
        raw = self._pressed()
        self._last_raw = raw
        self._last_change = now
        self._stable = raw
        self._armed = not raw
        self._down_t = now
        self._long_fired = False
        self._pending = False          # one click seen, waiting for a second
        self._release_t = now

    def _pressed(self):
        return self.pin.value() == 0

    @staticmethod
    def _call(cb):
        if cb:
            cb()

    def poll(self):
        """Call regularly (every ~10 ms)."""
        now = time.ticks_ms()
        raw = self._pressed()

        # debounce
        if raw != self._last_raw:
            self._last_raw = raw
            self._last_change = now
        elif raw != self._stable and \
                time.ticks_diff(now, self._last_change) >= self.debounce_ms:
            self._stable = raw
            self._edge(raw, now)

        if not self._armed:
            return

        # long press fires while still held
        if self._stable and not self._long_fired and \
                time.ticks_diff(now, self._down_t) >= self.long_ms:
            self._long_fired = True
            self._pending = False
            self._call(self.on_long)

        # single click is confirmed when no second click followed in time
        if self._pending and \
                time.ticks_diff(now, self._release_t) > self.double_ms:
            self._pending = False
            self._call(self.on_short)

    def _edge(self, pressed, now):
        if not self._armed:
            if not pressed:
                self._armed = True
            return
        if pressed:
            self._down_t = now
            self._long_fired = False
        else:
            if self._long_fired:
                return
            if self._pending and \
                    time.ticks_diff(now, self._release_t) <= self.double_ms:
                self._pending = False
                self._call(self.on_double)
            else:
                self._pending = True
                self._release_t = now
