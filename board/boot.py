# boot.py – runs before main.py, as early as possible after power-up.
#
# RadZilla – external display for RadiaCode
# Copyright (c) 2026 Shimizilla – licensed under CC BY-NC 4.0 (see LICENSE.md)
#
# Two pins must be set immediately, before anything else is imported:
#   * SYS_EN (GPIO41) HIGH keeps the battery supply switched on after the
#     PWR button has been released (self-holding power latch).
#   * BUZZER (GPIO42) LOW, otherwise the passive buzzer draws current
#     continuously and heats up the voltage regulator.
from machine import Pin

Pin(41, Pin.OUT, value=1)   # SYS_EN  – keep power on
Pin(42, Pin.OUT, value=0)   # BUZZER  – silent
