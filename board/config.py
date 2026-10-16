# config.py – settings of the base system (display, power, clock, time sync).
#
# RadZilla – external display for RadiaCode
# Copyright (c) 2026 Shimizilla – licensed under CC BY-NC 4.0 (see LICENSE.md)
#
# RadiaCode-related settings (alarms, log, trend ...) are in rc_config.py.
# WiFi credentials are in secrets.py (not in git, see secrets_example.py).

VERSION = "1.2.0"

# --- Diagnostics -------------------------------------------------------------
DIAG = False              # True: print a status line to the shell every 5 s

# --- UART on the 12-pin header (UART1 on GPIO43 TX / GPIO44 RX) --------------
UART_ID = 1
SERIAL_BAUD = 115200

# --- PWR button ---------------------------------------------------------------
LONG_PRESS_MS = 2000      # long press -> shut down (battery operation only)
DOUBLE_CLICK_MS = 400     # max. gap between two clicks of a double click
DEBOUNCE_MS = 30
BUTTON_POLL_MS = 10

# --- Buzzer -------------------------------------------------------------------
BEEP_ON_SHUTDOWN = True
BEEP_FREQ_HZ = 2000
BEEP_MS = 100

# --- Display ------------------------------------------------------------------
BACKLIGHT = 200           # brightness 0..255
BACKLIGHT_PWM_HZ = 1000
SPI_BAUD = 40_000_000

# --- Board battery measurement (GPIO1) ---------------------------------------
BAT_INTERVAL_MS = 5000
BAT_DIVIDER = 3.0         # on-board voltage divider 200 kΩ / 100 kΩ
BAT_SAMPLES = 16          # average over n ADC readings

# --- I2C bus (QMI8658 IMU, PCF85063 RTC, own sensors) ------------------------
I2C_FREQ = 400_000

# --- Clock --------------------------------------------------------------------
CLOCK_INTERVAL_MS = 1000

# --- Time sync (NTP, PTB atomic clock) ----------------------------------------
WIFI_TIMEOUT_MS = 15000   # give up if no connection within this time
NTP_SERVERS = ("ptbtime1.ptb.de", "ptbtime2.ptb.de")
NTP_AUTO_ON_BOOT = True   # sync at start-up if the RTC has no valid time
