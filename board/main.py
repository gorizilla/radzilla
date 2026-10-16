# main.py – RadZilla base system for the Waveshare ESP32-S3-LCD-1.69 V2.
#
# RadZilla – external display for RadiaCode
# Copyright (c) 2026 Shimizilla – licensed under CC BY-NC 4.0 (see LICENSE.md)
#
# Runs automatically after boot.py. Provides the status bar (clock, board
# battery), the PWR button, time sync and the display loop, and starts the
# application in app.py (RadiaCode display).
#
# PWR button:  short  -> app.on_short()
#              double -> time sync with the PTB atomic clock
#              long   -> beep and switch off (battery operation only)
#
# All parts run as cooperative asyncio tasks – nothing may block for long.
# WiFi and Bluetooth stay off unless a feature switches them on.
import asyncio
import time
from machine import Pin, SPI, I2C, UART

import config
import pins
import app
import ntp
from power import Power, Buzzer, Button
from st7789 import ST7789, WHITE, GREY, BLACK, YELLOW
from pcf85063 import PCF85063
from battery import Battery

try:
    from secrets import WIFI_NETWORKS        # not in git, see secrets_example.py
except ImportError:
    WIFI_NETWORKS = []


class Context:
    """Shared state handed to the application (see app.py)."""
    pass


CTX = None


def build():
    ctx = Context()
    ctx.power = Power(pins.SYS_EN)
    ctx.buzzer = Buzzer(pins.BUZZER)

    spi = SPI(1, baudrate=config.SPI_BAUD, polarity=0, phase=0,
              sck=Pin(pins.LCD_SCLK), mosi=Pin(pins.LCD_MOSI), miso=None)
    ctx.lcd = ST7789(spi, pins.LCD_CS, pins.LCD_DC, pins.LCD_RST,
                     pins.LCD_BL, config.BACKLIGHT_PWM_HZ, config.BACKLIGHT)

    ctx.i2c = I2C(0, scl=Pin(pins.I2C_SCL), sda=Pin(pins.I2C_SDA),
                  freq=config.I2C_FREQ)
    ctx.rtc = PCF85063(ctx.i2c, pins.ADDR_PCF85063)
    ctx.battery = Battery(pins.BAT_ADC, config.BAT_DIVIDER,
                          config.BAT_SAMPLES)
    ctx.uart = UART(config.UART_ID, baudrate=config.SERIAL_BAUD,
                    tx=pins.UART_TX, rx=pins.UART_RX)

    ctx.vbat = None
    ctx.time_str = "--:--:--"
    ctx.notice = None              # short message in the app area
    ctx.notice_until = 0
    ctx.syncing = False
    ctx.dirty = True               # True -> redraw the screen
    return ctx


def notify(ctx, text, ms=3000):
    """Show a short message in the middle of the screen."""
    ctx.notice = text
    ctx.notice_until = time.ticks_add(time.ticks_ms(), ms)
    ctx.dirty = True


# ---------- time sync -----------------------------------------------------------
async def time_sync_task(ctx):
    ctx.syncing = True
    notify(ctx, "Time sync ...", config.WIFI_TIMEOUT_MS * 2 + 10000)
    try:
        ok, res = await ntp.sync(ctx.rtc, WIFI_NETWORKS, config.NTP_SERVERS,
                                 config.WIFI_TIMEOUT_MS)
    except Exception as e:
        ok, res = False, "error"
        print("Time sync error:", e)
    if ok:
        print("Time set: %04d-%02d-%02d %02d:%02d:%02d" % res[:6])
        notify(ctx, "Time OK")
    else:
        print("Time sync failed:", res)
        notify(ctx, "Sync: " + res)
    ctx.syncing = False


def start_time_sync(ctx):
    if not ctx.syncing:
        asyncio.create_task(time_sync_task(ctx))


def rtc_valid(ctx):
    try:
        return ctx.rtc.datetime()[1]
    except OSError:
        return False


# ---------- shut-down -------------------------------------------------------------
def save_app_data(ctx):
    """Let the application save its data (e.g. log buffer)."""
    if ctx is not None and hasattr(app, "on_shutdown"):
        try:
            app.on_shutdown(ctx)
        except Exception as e:
            print("on_shutdown:", e)


def shutdown(ctx):
    print("PWR long press -> switching off")
    save_app_data(ctx)
    if config.BEEP_ON_SHUTDOWN:
        ctx.buzzer.beep(config.BEEP_FREQ_HZ, config.BEEP_MS)
    ctx.lcd.fb.fill(BLACK)
    ctx.lcd.text_center("Off", 128, WHITE, 3)
    ctx.lcd.show()
    time.sleep_ms(300)
    ctx.lcd.off()
    ctx.power.release()
    time.sleep_ms(1000)
    # Still running? Then the board is powered via USB and cannot switch off.
    ctx.power.hold()
    ctx.lcd.wake()
    notify(ctx, "USB power")
    print("Switching off only works on battery")


# ---------- screen ------------------------------------------------------------------
def draw(ctx):
    lcd = ctx.lcd
    lcd.fb.fill(BLACK)
    # status bar
    lcd.text_center(ctx.time_str, 18, WHITE, 2)
    bat = "Batt: --" if ctx.vbat is None else "Batt: %.2f V" % ctx.vbat
    lcd.text_center(bat, 40, GREY, 1)
    lcd.fb.hline(20, 54, 200, GREY)
    # application area (y >= 60) or a notice
    if ctx.notice and time.ticks_diff(ctx.notice_until, time.ticks_ms()) > 0:
        scale = 2 if len(ctx.notice) * 16 <= 224 else 1
        lcd.text_center(ctx.notice, 150, YELLOW, scale)
    else:
        ctx.notice = None
        app.draw(ctx)
    lcd.show()


# ---------- tasks ---------------------------------------------------------------------
async def button_task(btn):
    while True:
        btn.poll()
        await asyncio.sleep_ms(config.BUTTON_POLL_MS)


async def battery_task(ctx):
    while True:
        ctx.vbat = ctx.battery.voltage()
        ctx.dirty = True
        await asyncio.sleep_ms(config.BAT_INTERVAL_MS)


async def clock_task(ctx):
    while True:
        try:
            t, valid = ctx.rtc.datetime()
            ctx.time_str = "%02d:%02d:%02d" % t[3:6] if valid else "--:--:--"
        except OSError:
            ctx.time_str = "RTC ?"
        ctx.dirty = True
        await asyncio.sleep_ms(config.CLOCK_INTERVAL_MS)


DIAG = {"draws": 0, "last_ms": 0, "max_ms": 0}


async def display_task(ctx):
    import sys
    while True:
        # a notice has expired -> redraw once
        if ctx.notice and time.ticks_diff(ctx.notice_until, time.ticks_ms()) <= 0:
            ctx.dirty = True
        if ctx.dirty:
            ctx.dirty = False
            t0 = time.ticks_ms()
            try:
                draw(ctx)
            except Exception as e:           # keep the display alive
                print("Draw error:")
                sys.print_exception(e)
            dt = time.ticks_diff(time.ticks_ms(), t0)
            DIAG["draws"] += 1
            DIAG["last_ms"] = dt
            DIAG["max_ms"] = max(DIAG["max_ms"], dt)
        await asyncio.sleep_ms(50)


async def diag_task(ctx):
    """Status line in the shell every 5 s (config.DIAG = True)."""
    import gc
    while True:
        await asyncio.sleep_ms(5000)
        try:
            t, v = ctx.rtc.datetime()
            rtc = "%02d:%02d:%02d" % t[3:6]
        except Exception as e:
            rtc = "error " + repr(e)
        usv = getattr(getattr(app, "S", None), "usv", None)
        print("DIAG rtc=%s shown=%s draws=%d draw=%dms (max %d) usv=%s free=%dKB"
              % (rtc, ctx.time_str, DIAG["draws"], DIAG["last_ms"], DIAG["max_ms"],
                 usv, gc.mem_free() // 1024))
        DIAG["max_ms"] = 0


async def main():
    global CTX
    ctx = CTX = build()
    btn = Button(pins.SYS_OUT, config.LONG_PRESS_MS, config.DOUBLE_CLICK_MS,
                 config.DEBOUNCE_MS,
                 on_short=lambda: app.on_short(ctx),
                 on_double=lambda: start_time_sync(ctx),
                 on_long=lambda: shutdown(ctx))
    app.setup(ctx)
    print("RadZilla v%s started" % config.VERSION)

    asyncio.create_task(button_task(btn))
    asyncio.create_task(battery_task(ctx))
    asyncio.create_task(clock_task(ctx))
    asyncio.create_task(display_task(ctx))
    if config.DIAG:
        asyncio.create_task(diag_task(ctx))
    if config.NTP_AUTO_ON_BOOT and not rtc_valid(ctx):
        start_time_sync(ctx)
    await app.loop(ctx)


try:
    asyncio.run(main())
except KeyboardInterrupt:
    # Stop button / Ctrl+C in Thonny: save data before the program ends
    save_app_data(CTX)
    print("Stopped")
finally:
    asyncio.new_event_loop()
