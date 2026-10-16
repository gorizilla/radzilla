# rc_config.py – settings of the RadiaCode application (app.py).
#
# RadZilla – external display for RadiaCode
# Copyright (c) 2026 Shimizilla – licensed under CC BY-NC 4.0 (see LICENSE.md)
#
# All values can be changed freely. Upload the file and press RST afterwards.
# ⚠ Experimental: thresholds and conversion factor are not calibrated –
#   see NOTICE.md.

# --- Device -------------------------------------------------------------------
# Empty = first device whose name starts with RC_NAME_PREFIX.
# Fixed name e.g. "RadiaCode-102#RC-102-012345"
RC_NAME = ""
RC_NAME_PREFIX = "RadiaCode"

RC_SCAN_MS = 5000          # scan time per attempt
RC_RECONNECT_MS = 5000     # pause before the next attempt
RC_POLL_MS = 1000          # read interval
RC_STALE_MS = 5000         # no new values for this long -> show "--"

# Conversion raw dose rate -> µSv/h (compare with the RadiaCode display!)
RC_DOSE_FACTOR = 10000.0

# --- CSV log --------------------------------------------------------------------
# Format: Time;uSv/h;CPS;Alarm;Dose15
#   Alarm  0 = none, 1 = HIGH, 2 = DANGER, 3 = DOSE (the alarm shown, by priority)
#   Dose15 dose in µSv accumulated within the dose window (DOSE_WINDOW_MIN)
# Semicolon + decimal comma -> opens directly in German Numbers/Excel.
LOG_ON = True
LOG_DIR = "/logs"
LOG_INTERVAL_S = 3         # one line every 3 s
LOG_FLUSH_S = 60           # buffered, written to flash every 60 s
LOG_MAX_AGE_H = 24         # older -> deleted; new file after this run time
LOG_MAX_FILES = 10
LOG_MAX_TOTAL_KB = 2048    # all log files together
LOG_MIN_FREE_KB = 1024     # this much flash always stays free
LOG_CHECK_S = 3600         # clean-up at start and then this often

# --- Trend arrow ----------------------------------------------------------------
# Average of the last TREND_WINDOW_S seconds vs. the window before.
# The arrow appears after 2 x TREND_WINDOW_S seconds of data.
TREND_WINDOW_S = 10
TREND_PCT = 0.10           # change of at least ±10 % ...
TREND_MIN_USV = 0.02       # ... and at least this many µSv/h
TREND_MIN_CPS = 1.0        # ... or this many CPS (in CPS view)

# --- Colour levels = alarm thresholds (µSv/h) -----------------------------------
LEVEL1_USV = 0.28          # yellow / alarm 1 (HIGH) – about 2x local background
LEVEL2_USV = 10.0          # red    / alarm 2 (DANGER) – immediate alarm
HYSTERESIS = 0.10          # 10 %: an alarm ends only below threshold x 0.9
                           # (also used for the dose alarm)

# --- Dose alarm (alarm 3) ---------------------------------------------------------
# Triggers when the dose accumulated within the last DOSE_WINDOW_MIN minutes
# exceeds DOSE_LIMIT_USV. The higher the dose rate, the faster it triggers:
# 2.5 µSv / 15 min -> 10 µSv/h after ~15 min, 100 µSv/h after ~1.5 min.
# Counting starts with the connection; gaps without data count as 0.
DOSE_ON = True             # False = dose alarm completely off
DOSE_WINDOW_MIN = 15
DOSE_LIMIT_USV = 2.5

# --- Alarm display ---------------------------------------------------------------
ALARM_BLINK_MS = 500       # on/off period while not acknowledged
ALARM1_TEXT = "HIGH"       # max. 9 characters
ALARM2_TEXT = "DANGER"     # max. 9 characters
ALARM3_TEXT = "DOSE"       # max. 9 characters
ACK_TEXT = "ACK"           # shown after acknowledging (short PWR press)
# Several alarms at once: the frame shows the most important one,
# priority DANGER > DOSE > HIGH. One short PWR press acknowledges all.

# --- Alarm 1 (yellow) ------------------------------------------------------------
ALARM1_ON = True           # False = no beeps (display still shows the level)
ALARM1_FREQ_HZ = 2000
ALARM1_BEEPS = 1           # beeps per trigger
ALARM1_BEEP_MS = 100
ALARM1_PAUSE_MS = 100      # pause between beeps
ALARM1_INTERVAL_MS = 10000 # repeat interval
ALARM1_MAX_REPEAT = 3      # 0 = unlimited

# --- Alarm 2 (red) ------------------------------------------------------------------
ALARM2_ON = True
ALARM2_FREQ_HZ = 3000
ALARM2_BEEPS = 3
ALARM2_BEEP_MS = 100
ALARM2_PAUSE_MS = 100
ALARM2_INTERVAL_MS = 2000
ALARM2_MAX_REPEAT = 0      # 0 = unlimited

# --- Alarm 3 (orange, dose alarm) --------------------------------------------------
ALARM3_ON = True           # beeps only; DOSE_ON switches the whole alarm
ALARM3_FREQ_HZ = 2500
ALARM3_BEEPS = 2
ALARM3_BEEP_MS = 150
ALARM3_PAUSE_MS = 100
ALARM3_INTERVAL_MS = 5000
ALARM3_MAX_REPEAT = 5      # 0 = unlimited
