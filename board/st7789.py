# st7789.py – small ST7789V2 display driver with a full-screen framebuffer.
#
# RadZilla – external display for RadiaCode
# Copyright (c) 2026 Shimizilla – licensed under CC BY-NC 4.0 (see LICENSE.md)
#
# Panel: 240 x 280 pixels, RGB565. The controller RAM is 240 x 320, the
# visible area starts at row 20 (Y_OFF). Drawing happens in RAM via
# MicroPython's framebuf; show() sends the whole buffer over SPI (~30 ms).
import time
import framebuf
from machine import Pin, PWM


def color565(r, g, b):
    """RGB888 -> RGB565 with swapped bytes (framebuf stores little-endian,
    the ST7789 expects big-endian)."""
    c = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
    return ((c & 0xFF) << 8) | (c >> 8)


BLACK = color565(0, 0, 0)
WHITE = color565(255, 255, 255)
GREY = color565(120, 120, 120)
RED = color565(255, 0, 0)
GREEN = color565(0, 200, 0)
BLUE = color565(0, 80, 255)
YELLOW = color565(255, 220, 0)


class ST7789:
    WIDTH = 240
    HEIGHT = 280
    X_OFF = 0
    Y_OFF = 20

    def __init__(self, spi, cs, dc, rst, bl, bl_freq=1000, brightness=200):
        self.spi = spi
        self.cs = Pin(cs, Pin.OUT, value=1)
        self.dc = Pin(dc, Pin.OUT, value=0)
        self.rst = Pin(rst, Pin.OUT, value=1)
        self._bl = PWM(Pin(bl), freq=bl_freq, duty_u16=0)
        self._level = brightness

        # Framebuffer for the whole screen (~134 KB, lives in PSRAM)
        self.buf = bytearray(self.WIDTH * self.HEIGHT * 2)
        self.fb = framebuf.FrameBuffer(self.buf, self.WIDTH, self.HEIGHT,
                                       framebuf.RGB565)
        # Scratch buffer for scaled text (one 8x8 character)
        self._cbuf = bytearray(8)
        self._cfb = framebuf.FrameBuffer(self._cbuf, 8, 8, framebuf.MONO_HLSB)

        self._reset()
        self._init()
        self.fb.fill(BLACK)
        self.show()
        self.brightness(brightness)

    # ---------- low level ----------
    def _cmd(self, c, data=None):
        self.cs(0)
        self.dc(0)
        self.spi.write(bytes((c,)))
        if data is not None:
            self.dc(1)
            self.spi.write(data)
        self.cs(1)

    def _reset(self):
        self.rst(1)
        time.sleep_ms(10)
        self.rst(0)
        time.sleep_ms(10)
        self.rst(1)
        time.sleep_ms(120)

    def _init(self):
        self._cmd(0x01)              # software reset
        time.sleep_ms(150)
        self._cmd(0x11)              # sleep out
        time.sleep_ms(120)
        self._cmd(0x3A, b"\x55")     # 16 bit/pixel (RGB565)
        self._cmd(0x36, b"\x00")     # MADCTL: portrait
        self._cmd(0x21)              # inversion on (required by this IPS panel)
        self._cmd(0x13)              # normal display mode
        self._cmd(0x29)              # display on
        time.sleep_ms(20)

    def _window(self, x0, y0, x1, y1):
        x0 += self.X_OFF
        x1 += self.X_OFF
        y0 += self.Y_OFF
        y1 += self.Y_OFF
        self._cmd(0x2A, bytes((x0 >> 8, x0 & 0xFF, x1 >> 8, x1 & 0xFF)))
        self._cmd(0x2B, bytes((y0 >> 8, y0 & 0xFF, y1 >> 8, y1 & 0xFF)))

    # ---------- output ----------
    def show(self):
        """Send the complete framebuffer to the display."""
        self._window(0, 0, self.WIDTH - 1, self.HEIGHT - 1)
        self.cs(0)
        self.dc(0)
        self.spi.write(b"\x2C")      # memory write
        self.dc(1)
        self.spi.write(self.buf)
        self.cs(1)

    def brightness(self, level):
        """Backlight 0..255."""
        level = max(0, min(255, int(level)))
        self._level = level
        self._bl.duty_u16(level * 257)

    def off(self):
        self._bl.duty_u16(0)
        self._cmd(0x28)              # display off
        self._cmd(0x10)              # sleep in

    def wake(self):
        self._cmd(0x11)
        time.sleep_ms(120)
        self._cmd(0x29)
        self.brightness(self._level)

    # ---------- text (built-in 8x8 font, optionally scaled) ----------
    def text(self, s, x, y, color, scale=1):
        if scale == 1:
            self.fb.text(s, x, y, color)
            return
        fb = self.fb
        cfb = self._cfb
        for ch in s:
            cfb.fill(0)
            cfb.text(ch, 0, 0, 1)
            for row in range(8):
                for col in range(8):
                    if cfb.pixel(col, row):
                        fb.fill_rect(x + col * scale, y + row * scale,
                                     scale, scale, color)
            x += 8 * scale

    def text_center(self, s, y, color, scale=1):
        x = (self.WIDTH - len(s) * 8 * scale) // 2
        self.text(s, x, y, color, scale)
