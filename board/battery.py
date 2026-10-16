# battery.py – board battery voltage on GPIO1 (on-board divider 200k/100k).
#
# RadZilla – external display for RadiaCode
# Copyright (c) 2026 Shimizilla – licensed under CC BY-NC 4.0 (see LICENSE.md)
#
# Note: without a battery connected, the reading shows the charger output
# voltage (about 4.2 V) while USB is plugged in.
from machine import ADC, Pin


class Battery:
    def __init__(self, pin, divider=3.0, samples=16):
        self.adc = ADC(Pin(pin))
        self.adc.atten(ADC.ATTN_11DB)      # full range up to ~3.1 V at the pin
        self.divider = divider
        self.samples = samples

    def voltage(self):
        """Averaged battery voltage in volts."""
        total = 0
        for _ in range(self.samples):
            total += self.adc.read_uv()
        return total / self.samples / 1_000_000 * self.divider
