# Configuration

Change the values, upload the file to the board and press **RST**.

> ⚠ Thresholds and the dose conversion factor are user settings and are not
> calibrated. RadZilla is not a safety device – see [NOTICE.md](../NOTICE.md).

## secrets.py (not in git)

Create it from `secrets_example.py`.

| Setting | Meaning |
|---|---|
| `WIFI_NETWORKS` | list of `("SSID", "password")`. On time sync the board scans and connects to the **strongest known** network; if that fails, it tries the next one. 2.4 GHz only. |

## config.py – base system

| Setting | Default | Meaning |
|---|---|---|
| `VERSION` | `"1.0.0"` | shown in the shell at start-up |
| `DIAG` | `False` | status line in the shell every 5 s |
| `UART_ID`, `SERIAL_BAUD` | `1`, `115200` | UART on header pins 8/9 |
| `LONG_PRESS_MS` | `2000` | long press → switch off |
| `DOUBLE_CLICK_MS` | `400` | max. gap for a double press |
| `DEBOUNCE_MS`, `BUTTON_POLL_MS` | `30`, `10` | button handling |
| `BEEP_ON_SHUTDOWN`, `BEEP_FREQ_HZ`, `BEEP_MS` | `True`, `2000`, `100` | shut-down beep |
| `BACKLIGHT` | `200` | display brightness 0–255 |
| `BACKLIGHT_PWM_HZ` | `1000` | backlight PWM frequency |
| `SPI_BAUD` | `40000000` | display SPI clock |
| `BAT_INTERVAL_MS`, `BAT_DIVIDER`, `BAT_SAMPLES` | `5000`, `3.0`, `16` | board battery measurement |
| `I2C_FREQ` | `400000` | I2C bus clock |
| `CLOCK_INTERVAL_MS` | `1000` | clock refresh |
| `WIFI_TIMEOUT_MS` | `15000` | max. time per WiFi connection attempt |
| `NTP_SERVERS` | `ptbtime1.ptb.de`, `ptbtime2.ptb.de` | time servers, tried in order |
| `NTP_AUTO_ON_BOOT` | `True` | sync at start if the RTC has no valid time |

## rc_config.py – RadiaCode application

### Device

| Setting | Default | Meaning |
|---|---|---|
| `RC_NAME` | `""` | fixed device name, e.g. `"RadiaCode-102#RC-102-012345"`; empty = first match of the prefix |
| `RC_NAME_PREFIX` | `"RadiaCode"` | name prefix for the automatic search |
| `RC_SCAN_MS` | `5000` | scan time per attempt |
| `RC_RECONNECT_MS` | `5000` | pause before reconnecting |
| `RC_POLL_MS` | `1000` | read interval |
| `RC_STALE_MS` | `5000` | without new data the values turn grey "--" |
| `RC_DOSE_FACTOR` | `10000.0` | raw dose rate → µSv/h; **check against the RadiaCode display** |

### Colour levels and alarms

| Setting | Default | Meaning |
|---|---|---|
| `LEVEL1_USV` | `0.30` | yellow / alarm 1 (HIGH) from this µSv/h |
| `LEVEL2_USV` | `1.00` | red / alarm 2 (DANGER) from this µSv/h |
| `HYSTERESIS` | `0.10` | a level ends only below threshold × (1 − 0.10) |
| `ALARM_BLINK_MS` | `500` | blink period of the alarm frame |
| `ALARM1_TEXT`, `ALARM2_TEXT` | `"HIGH"`, `"DANGER"` | alarm texts (max. 9 characters) |
| `ACK_TEXT` | `"ACK"` | shown after acknowledging |

Per alarm level (`ALARM1_…` yellow, `ALARM2_…` red):

| Setting | Alarm 1 | Alarm 2 | Meaning |
|---|---|---|---|
| `_ON` | `True` | `True` | beeps on/off (the display still shows the level) |
| `_FREQ_HZ` | `2000` | `3000` | beep frequency |
| `_BEEPS` | `1` | `3` | beeps per trigger |
| `_BEEP_MS` | `100` | `100` | beep length |
| `_PAUSE_MS` | `100` | `100` | pause between beeps |
| `_INTERVAL_MS` | `10000` | `2000` | repeat interval |
| `_MAX_REPEAT` | `3` | `0` | max. triggers per alarm, `0` = unlimited |

Behaviour:

- The repeat counter restarts when the alarm ends (below the hysteresis
  limit). Escalating from level 1 to 2 starts level 2 with its own counter.
- **Short PWR press** acknowledges: beeping stops, the frame stops blinking
  and shows `ACK_TEXT`, until the alarm ends. Escalation to a higher level
  makes it audible again.

### Trend arrow

| Setting | Default | Meaning |
|---|---|---|
| `TREND_WINDOW_S` | `10` | compare the last 10 s with the 10 s before; arrow appears after 20 s |
| `TREND_PCT` | `0.10` | minimum relative change (±10 %) … |
| `TREND_MIN_USV` | `0.02` | … and minimum absolute change in µSv/h |
| `TREND_MIN_CPS` | `1.0` | … or in CPS (CPS view) |

Arrow colours: ↑ orange · → grey · ↓ green.

### CSV log

| Setting | Default | Meaning |
|---|---|---|
| `LOG_ON` | `True` | logging on/off |
| `LOG_DIR` | `"/logs"` | folder on the board |
| `LOG_INTERVAL_S` | `3` | one line every 3 s |
| `LOG_FLUSH_S` | `60` | buffer is written every 60 s (and on stop / switch-off) |
| `LOG_MAX_AGE_H` | `24` | delete files whose last entry is older; start a new file after this run time |
| `LOG_MAX_FILES` | `10` | max. number of log files |
| `LOG_MAX_TOTAL_KB` | `2048` | max. size of all logs together |
| `LOG_MIN_FREE_KB` | `1024` | flash that always stays free |
| `LOG_CHECK_S` | `3600` | clean-up at start and then every hour |

File format (`rc_YYYY-MM-DD_HHMM.csv`, semicolon, decimal comma):

```
Time;uSv/h;CPS;Alarm
2026-10-16 14:07:03;0,12;8,53;0
```

`Alarm`: `0` = none, `1` = level 1 (HIGH), `2` = level 2 (DANGER) – always
derived from the thresholds configured at that moment (same as the display
colour), independent of whether beeps are enabled.

Logging only runs while the RadiaCode is connected with fresh data and the
RTC has a valid time. About **36 KB per hour**, ~0.9 MB per 24 h.
