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
| `VERSION` | `"1.1.0"` | shown in the shell at start-up |
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

RadZilla has three alarms:

| Code | Alarm | Trigger | Colour |
|---|---|---|---|
| 1 | **HIGH** | dose rate ≥ `LEVEL1_USV` | yellow |
| 2 | **DANGER** | dose rate ≥ `LEVEL2_USV` (immediate) | red |
| 3 | **DOSE** | dose accumulated within `DOSE_WINDOW_MIN` ≥ `DOSE_LIMIT_USV` | orange |

If several are active, the frame shows the most important one:
**DANGER > DOSE > HIGH**. Only the shown alarm beeps.

| Setting | Default | Meaning |
|---|---|---|
| `LEVEL1_USV` | `0.28` | HIGH from this µSv/h – about twice a typical background of 0.12–0.14 µSv/h, i.e. "something radioactive is nearby" |
| `LEVEL2_USV` | `10.0` | DANGER from this µSv/h – clearly above what hobby samples normally reach; move away |
| `HYSTERESIS` | `0.10` | every alarm ends only below threshold × (1 − 0.10) |
| `ALARM_BLINK_MS` | `500` | blink period of the alarm frame |
| `ALARM1_TEXT`, `ALARM2_TEXT`, `ALARM3_TEXT` | `"HIGH"`, `"DANGER"`, `"DOSE"` | alarm texts (max. 9 characters) |
| `ACK_TEXT` | `"ACK"` | shown after acknowledging |

### Dose alarm

| Setting | Default | Meaning |
|---|---|---|
| `DOSE_ON` | `True` | dose alarm on/off completely |
| `DOSE_WINDOW_MIN` | `15` | sliding window in minutes |
| `DOSE_LIMIT_USV` | `2.5` | alarm when more than this many µSv were collected within the window |

The dose alarm looks at the **time spent** near a source, not at the momentary
value. The higher the dose rate, the faster it triggers:

| Dose rate | DOSE triggers after (2.5 µSv / 15 min) |
|---|---|
| 5 µSv/h | never (only 1.25 µSv in 15 min) |
| 10 µSv/h | ~15 min |
| 50 µSv/h | ~3 min |
| 100 µSv/h | ~1.5 min |
| 1000 µSv/h | ~9 s |

Counting starts with the Bluetooth connection; periods without data (e.g.
disconnected) count as 0. The frame shows the collected dose, e.g.
`2.6 uSv/15min`. Together with DANGER this covers both cases: a high momentary
value (DANGER, immediate) and a longer stay at moderately raised levels (DOSE).

> For orientation only: acute radiation sickness starts at about
> 500 000–1 000 000 µSv received within a short time – far beyond anything
> these alarms are meant for. The default values are deliberately very
> conservative. Authoritative information: Bundesamt für Strahlenschutz,
> <https://www.bfs.de>.

### Beeps per alarm

(`ALARM1_…` HIGH, `ALARM2_…` DANGER, `ALARM3_…` DOSE)

| Setting | Alarm 1 | Alarm 2 | Alarm 3 | Meaning |
|---|---|---|---|---|
| `_ON` | `True` | `True` | `True` | beeps on/off (the display still shows the alarm) |
| `_FREQ_HZ` | `2000` | `3000` | `2500` | beep frequency |
| `_BEEPS` | `1` | `3` | `2` | beeps per trigger |
| `_BEEP_MS` | `100` | `100` | `150` | beep length |
| `_PAUSE_MS` | `100` | `100` | `100` | pause between beeps |
| `_INTERVAL_MS` | `10000` | `2000` | `5000` | repeat interval |
| `_MAX_REPEAT` | `3` | `0` | `5` | max. triggers per alarm event, `0` = unlimited |

Behaviour:

- Each alarm has its own repeat counter. It restarts when the alarm ends
  (below the hysteresis limit). Escalating from HIGH to DANGER starts DANGER
  with its own counter.
- **Short PWR press** acknowledges **all** running alarms: beeping stops, the
  frame stops blinking and shows `ACK_TEXT`, until the alarms end. Escalation
  to a higher rate level or a new dose alarm makes it audible again.

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
Time;uSv/h;CPS;Alarm;Dose15
2026-10-16 14:07:03;0,12;8,53;0;0,03
```

- `Alarm`: `0` = none, `1` = HIGH, `2` = DANGER, `3` = DOSE – the alarm shown
  in the frame at that moment (priority DANGER > DOSE > HIGH), derived from
  the thresholds configured at that time, independent of whether beeps are
  enabled.
- `Dose15`: dose in µSv collected within the dose window
  (`DOSE_WINDOW_MIN`, default 15 min).

Logging only runs while the RadiaCode is connected with fresh data and the
RTC has a valid time. About **36 KB per hour**, ~0.9 MB per 24 h.
