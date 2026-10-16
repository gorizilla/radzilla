# app.py – RadiaCode display: 3 pages, alarms, dose alarm, trend and CSV log.
#
# RadZilla – external display for RadiaCode
# Copyright (c) 2026 Shimizilla – licensed under CC BY-NC 4.0 (see LICENSE.md)
#
# ⚠ Experimental – not a safety device. See NOTICE.md.
#
# Settings: rc_config.py
#
# Pages (short PWR press cycles through them):
#   0  dose rate µSv/h large, CPS small, trend arrow
#   1  count rate CPS large, µSv/h small, trend arrow
#   2  DOSE page: radiation symbol with two rings
#        outer ring (segments): dose within the last DOSE_WINDOW_MIN minutes
#                               vs. DOSE_LIMIT_USV – drives the DOSE alarm
#        inner ring (thin, blue): extra dose today above BACKGROUND_USV
#                                 vs. DAILY_BUDGET_USV – information only
#
# Alarms (codes as used in the CSV log):
#   1 HIGH    dose rate >= LEVEL1_USV                         yellow
#   2 DANGER  dose rate >= LEVEL2_USV                         red
#   3 DOSE    dose within DOSE_WINDOW_MIN >= DOSE_LIMIT_USV   orange
# Several at once: the most important is shown, DANGER > DOSE > HIGH.
# All alarms end only below threshold x (1 - HYSTERESIS).
# HIGH / DANGER blink until acknowledged. DOSE blinks only while its sound
# plays (siren, once by default) and then stays lit until it ends.
#
# PWR short:  alarm active -> acknowledge all alarms (silent until they end)
#             otherwise    -> next page
# PWR double: time sync (handled by main.py)
#
# Interface used by main.py:
#   setup(ctx), loop(ctx), draw(ctx), on_short(ctx), on_shutdown(ctx),
#   show_battery()
#   The application area of the screen starts at y = 60.

import asyncio
import math
import time
from array import array
from machine import Pin, PWM

import pins
import rc_config as C
from logger import Logger
from st7789 import WHITE, GREY, GREEN, YELLOW, RED, color565

APP_Y = 60
ORANGE = color565(255, 140, 0)
DIM_ORANGE = color565(150, 80, 0)       # dose ring below 100 %
DARK = color565(45, 45, 45)             # empty ring segments
BLUE = color565(0, 140, 255)            # extra-dose ring
DARK_BLUE = color565(20, 35, 70)        # empty part of the extra-dose ring

PAGE_USV, PAGE_CPS, PAGE_DOSE = 0, 1, 2
N_PAGES = 3

# Layout of the bottom status lines (all pages)
Y_STATUS = 256
Y_LOGSTATUS = 268

# Status texts (bottom line)
ST_START = "Start"
ST_SCAN = "Scanning ..."
ST_NOTFOUND = "Not found"
ST_CONNECTING = "Connecting ..."
ST_CONNECTED = "Connected"
ST_DISCONNECTED = "Disconnected"
ST_NO_AIOBLE = "aioble missing"


class State:
    def __init__(self):
        self.status = ST_START
        self.connected = False
        self.name = ""
        self.cps = None
        self.usv = None
        self.batt = None          # RadiaCode battery in %
        self.last_ms = None       # time of the last reading
        self.view = PAGE_USV      # current page
        self.level = 0            # dose-rate alarm level 0 / 1 / 2
        self.acked = False
        self.count = 0            # beeps triggered in the current level
        self.last_beep = None
        self.hist = []            # (ticks_ms, usv, cps) for the trend
        self.blink_on = True
        self.time_valid = False
        # dose alarm
        self.dose_hist = []       # (ticks_ms, µSv increment) within the window
        self.dose_total = 0.0     # µSv within the window (running sum)
        self.last_rd_ms = None    # time of the previous reading (None = gap)
        self.dose_active = False
        self.dose_acked = False
        self.dose_count = 0
        self.dose_last_beep = None
        self.dose_blink_until = None   # DOSE blinks only until this time
        # extra dose today (above background, since switching on)
        self.extra_total = 0.0


S = State()
LOG = Logger(C)


# ---------- helpers -------------------------------------------------------------
def _fresh():
    """True if the last reading is recent enough to be shown."""
    return S.last_ms is not None and \
        time.ticks_diff(time.ticks_ms(), S.last_ms) < C.RC_STALE_MS


def _fmt_usv(v):
    return "%.2f" % v if v < 100 else "%.1f" % v


def _fmt_cps(v):
    if v < 100:
        return "%.2f" % v
    if v < 1000:
        return "%.1f" % v
    return "%d" % v


# ---------- trend ------------------------------------------------------------------
def _add_hist(usv, cps):
    now = time.ticks_ms()
    S.hist.append((now, usv, cps))
    keep = 2 * C.TREND_WINDOW_S * 1000 + 2000
    while S.hist and time.ticks_diff(now, S.hist[0][0]) > keep:
        S.hist.pop(0)


def _trend(idx, min_abs):
    """Compare the average of the last window with the window before.
    Returns +1 rising, -1 falling, 0 steady, None = not enough data."""
    if not S.hist:
        return None
    now = time.ticks_ms()
    w = C.TREND_WINDOW_S * 1000
    if time.ticks_diff(now, S.hist[0][0]) < 2 * w - 1500:
        return None
    new = [h[idx] for h in S.hist if time.ticks_diff(now, h[0]) <= w]
    old = [h[idx] for h in S.hist if w < time.ticks_diff(now, h[0]) <= 2 * w]
    if not new or not old:
        return None
    a_new = sum(new) / len(new)
    a_old = sum(old) / len(old)
    diff = a_new - a_old
    if abs(diff) >= max(a_old * C.TREND_PCT, min_abs):
        return 1 if diff > 0 else -1
    return 0


# ---------- dose -------------------------------------------------------------------
def _add_dose(usv, now):
    """Add the dose of one reading to the 15-min window and to the extra
    dose of the day. The time step is limited to 2 poll intervals, so gaps
    without data (disconnect) count as 0."""
    if S.last_rd_ms is None:
        dt = C.RC_POLL_MS
    else:
        dt = min(time.ticks_diff(now, S.last_rd_ms), 2 * C.RC_POLL_MS)
    S.last_rd_ms = now
    inc = usv * dt / 3_600_000           # µSv/h x ms -> µSv
    S.dose_hist.append((now, inc))
    S.dose_total += inc
    S.extra_total += max(0.0, usv - C.BACKGROUND_USV) * dt / 3_600_000
    _trim_dose(now)


def _trim_dose(now):
    """Remove readings older than the window from the running sum."""
    w = C.DOSE_WINDOW_MIN * 60_000
    while S.dose_hist and time.ticks_diff(now, S.dose_hist[0][0]) > w:
        S.dose_total -= S.dose_hist.pop(0)[1]
    if not S.dose_hist or S.dose_total < 0:   # empty window / rounding errors
        S.dose_total = 0.0


def _alarm3_sound_ms():
    """Duration of the DOSE alarm sound = time the DOSE alarm blinks."""
    if C.ALARM3_SOUND == "siren":
        return C.SIREN_RISE_MS + C.SIREN_HOLD_MS + C.SIREN_FALL_MS
    n = C.ALARM3_BEEPS
    return n * C.ALARM3_BEEP_MS + (n - 1) * C.ALARM3_PAUSE_MS


def _update_dose(ctx):
    """Dose alarm on/off with hysteresis."""
    if not C.DOSE_ON:
        new = False
    else:
        lim = C.DOSE_LIMIT_USV
        new = S.dose_total >= lim or \
            (S.dose_active and S.dose_total >= lim * (1 - C.HYSTERESIS))
    if new == S.dose_active:
        return
    S.dose_active = new
    S.dose_acked = False                 # new alarm or alarm over
    S.dose_count = 0
    S.dose_last_beep = None
    # blink once for the length of the sound (at least 1 s, also if muted)
    S.dose_blink_until = time.ticks_add(time.ticks_ms(),
                                        max(1000, _alarm3_sound_ms())) if new else None
    ctx.dirty = True


def _dose_pct():
    return S.dose_total / C.DOSE_LIMIT_USV * 100 if C.DOSE_LIMIT_USV else 0


def _extra_pct():
    return S.extra_total / C.DAILY_BUDGET_USV * 100 if C.DAILY_BUDGET_USV else 0


def _dose_eta():
    """Time until the dose limit is reached at the current dose rate."""
    lim = C.DOSE_LIMIT_USV
    if S.dose_total >= lim:
        return "LIMIT REACHED"
    if not _fresh() or not S.usv:
        return "--"
    # at a constant rate the window sum approaches rate x window
    if S.usv * C.DOSE_WINDOW_MIN / 60 < lim:
        return "SAFE"
    secs = int((lim - S.dose_total) / S.usv * 3600)
    return "DOSE LIMIT IN %d:%02d" % (secs // 60, secs % 60)


# ---------- alarm state -------------------------------------------------------------
def _shown_alarm():
    """Alarm shown on screen and written to the log (priority)."""
    if S.level == 2:
        return 2
    if S.dose_active:
        return 3
    return S.level                       # 1 or 0


def _is_acked(alarm):
    return S.dose_acked if alarm == 3 else S.acked


def _is_blinking(alarm):
    """HIGH/DANGER blink until acknowledged; DOSE only while its sound plays."""
    if alarm == 0 or _is_acked(alarm):
        return False
    if alarm == 3:
        return S.dose_blink_until is not None and \
            time.ticks_diff(S.dose_blink_until, time.ticks_ms()) > 0
    return True


def _visible(alarm):
    return not _is_blinking(alarm) or S.blink_on


# ---------- graphics ---------------------------------------------------------------
def _trefoil(fb, cx, cy, r, color):
    """Radiation warning symbol: three 60° blades and a centre dot."""
    ri = r * 0.32
    for a0 in (90, 210, 330):                  # blades: bottom, top-left, top-right
        pts = []
        for a in range(a0 - 30, a0 + 31, 10):  # outer arc
            t = math.radians(a)
            pts.append(int(round(r * math.cos(t))))
            pts.append(int(round(r * math.sin(t))))
        for a in range(a0 + 30, a0 - 31, -15): # inner arc (back)
            t = math.radians(a)
            pts.append(int(round(ri * math.cos(t))))
            pts.append(int(round(ri * math.sin(t))))
        fb.poly(cx, cy, array("h", pts), color, True)
    d = max(2, int(r * 0.2))
    fb.ellipse(cx, cy, d, d, color, True)


def _arc_poly(r_in, r_out, a0, a1, steps):
    """Polygon of a ring segment (angles in degrees, 0° = right, clockwise)."""
    pts = []
    for i in range(steps + 1):
        t = math.radians(a0 + (a1 - a0) * i / steps)
        pts.append(int(round(r_out * math.cos(t))))
        pts.append(int(round(r_out * math.sin(t))))
    for i in range(steps, -1, -1):
        t = math.radians(a0 + (a1 - a0) * i / steps)
        pts.append(int(round(r_in * math.cos(t))))
        pts.append(int(round(r_in * math.sin(t))))
    return array("h", pts)


# Ring geometry is computed once and reused for every frame.
RING_SEGMENTS = 24          # outer ring: 24 segments of 15° (~4 % each)
RING_STEPS = 72             # inner ring: 72 steps of 5°
_RING = None


def _ring_geometry():
    global _RING
    if _RING is None:
        outer = [_arc_poly(44, 52, -90 + i * 15 + 1.5, -90 + i * 15 + 13.5, 3)
                 for i in range(RING_SEGMENTS)]
        inner = [_arc_poly(37, 40, -90 + i * 5, -90 + i * 5 + 5, 1)
                 for i in range(RING_STEPS)]
        _RING = (outer, inner)
    return _RING


def _alarm_box(lcd, alarm, acked, show):
    """HUD-style alarm frame: chamfered box, corner brackets, symbol, text.
    alarm: 1 HIGH (yellow), 2 DANGER (red), 3 DOSE (orange)."""
    if not show:
        return
    fb = lcd.fb
    col = (YELLOW, RED, ORANGE)[alarm - 1]
    x0, y0, x1, y1, c = 14, 194, 226, 236, 10
    for k in (0, 1):                            # 2 px outline
        a, b, e, f, cc = x0 + k, y0 + k, x1 - k, y1 - k, c
        fb.poly(0, 0, array("h", [a + cc, b, e - cc, b, e, b + cc, e, f - cc,
                                  e - cc, f, a + cc, f, a, f - cc, a, b + cc]),
                col, False)
    L = 12                                       # corner brackets
    for ax, ay, sx, sy in ((x0 - 6, y0 - 6, 1, 1), (x1 + 6, y0 - 6, -1, 1),
                           (x0 - 6, y1 + 6, 1, -1), (x1 + 6, y1 + 6, -1, -1)):
        fb.fill_rect(min(ax, ax + L * sx), ay - (1 if sy < 0 else 0), L, 2, col)
        fb.fill_rect(ax - (1 if sx < 0 else 0), min(ay, ay + L * sy), 2, L, col)
    _trefoil(fb, 42, 215, 13, col)
    txt = _alarm_text(alarm)
    tx = 64 + (158 - len(txt) * 16) // 2
    # second line: dose for the dose alarm, ACK after acknowledging
    sub = ""
    if alarm == 3:
        sub = "%.1f uSv/%dmin" % (S.dose_total, C.DOSE_WINDOW_MIN)
    if acked:
        sub = (sub + " " + C.ACK_TEXT) if sub else C.ACK_TEXT
    if sub:
        sub = sub[:19]
        lcd.text(txt, tx, 203, col, 2)
        lcd.text(sub, 64 + (158 - len(sub) * 8) // 2, 224, GREY, 1)
    else:
        lcd.text(txt, tx, 207, col, 2)


def _alarm_text(alarm):
    return (C.ALARM1_TEXT, C.ALARM2_TEXT, C.ALARM3_TEXT)[alarm - 1][:9]


def _alarm_color(alarm):
    return (YELLOW, RED, ORANGE)[alarm - 1]


def _arrow(fb, x, y, d, color):
    """Arrow in a 24x24 box: d = 1 up, -1 down, 0 right."""
    if d == 0:
        fb.fill_rect(x, y + 9, 14, 6, color)
        fb.poly(x, y, array("h", [12, 0, 24, 12, 12, 24]), color, True)
    elif d > 0:
        fb.fill_rect(x + 9, y + 10, 6, 14, color)
        fb.poly(x, y, array("h", [0, 12, 12, 0, 24, 12]), color, True)
    else:
        fb.fill_rect(x + 9, y, 6, 14, color)
        fb.poly(x, y, array("h", [0, 12, 24, 12, 12, 24]), color, True)


def _color(level):
    return (GREEN, YELLOW, RED)[level]


# ---------- alarm logic -----------------------------------------------------------
def _new_level(usv, cur):
    """Alarm level with hysteresis: a level ends only below threshold x (1-H)."""
    h = 1 - C.HYSTERESIS
    if usv >= C.LEVEL2_USV or (cur == 2 and usv >= C.LEVEL2_USV * h):
        return 2
    if usv >= C.LEVEL1_USV or (cur >= 1 and usv >= C.LEVEL1_USV * h):
        return 1
    return 0


def _update_level(ctx):
    new = _new_level(S.usv, S.level) if S.usv is not None else 0
    if new == S.level:
        return
    if new == 0:
        S.acked = False                 # alarm is over
    elif new > S.level:
        S.acked = False                 # escalation -> audible again
    S.count = 0
    S.last_beep = None
    S.level = new
    ctx.dirty = True


def _buzzer_off(p):
    p.deinit()
    Pin(pins.BUZZER, Pin.OUT, value=0)    # leave the pin LOW (no current)


async def _beep(freq, n, on_ms, pause_ms):
    """Non-blocking beep pattern (runs as its own task)."""
    p = PWM(Pin(pins.BUZZER), freq=freq, duty_u16=32768)
    try:
        for i in range(n):
            p.duty_u16(32768)
            await asyncio.sleep_ms(on_ms)
            p.duty_u16(0)
            if i < n - 1:
                await asyncio.sleep_ms(pause_ms)
    finally:
        _buzzer_off(p)


async def _siren():
    """Rising and falling siren (DOSE alarm). Stops early when acknowledged.
    The small on-board buzzer is quiet below ~1 kHz, hence the high range."""
    lo, hi, step = C.SIREN_LOW_HZ, C.SIREN_HIGH_HZ, C.SIREN_STEP_MS
    p = PWM(Pin(pins.BUZZER), freq=lo, duty_u16=32768)
    try:
        n = max(1, C.SIREN_RISE_MS // step)
        for i in range(n + 1):                       # rise
            if S.dose_acked:
                return
            p.freq(int(lo + (hi - lo) * i / n))
            p.duty_u16(32768)
            await asyncio.sleep_ms(step)
        t = 0
        while t < C.SIREN_HOLD_MS:                   # hold
            if S.dose_acked:
                return
            await asyncio.sleep_ms(step)
            t += step
        n = max(1, C.SIREN_FALL_MS // step)
        for i in range(n + 1):                       # fall
            if S.dose_acked:
                return
            p.freq(int(hi - (hi - lo) * i / n))
            p.duty_u16(32768)
            await asyncio.sleep_ms(step)
    finally:
        _buzzer_off(p)


def _alarm_cfg(alarm):
    if alarm == 1:
        return (C.ALARM1_ON, C.ALARM1_FREQ_HZ, C.ALARM1_BEEPS, C.ALARM1_BEEP_MS,
                C.ALARM1_PAUSE_MS, C.ALARM1_INTERVAL_MS, C.ALARM1_MAX_REPEAT)
    if alarm == 2:
        return (C.ALARM2_ON, C.ALARM2_FREQ_HZ, C.ALARM2_BEEPS, C.ALARM2_BEEP_MS,
                C.ALARM2_PAUSE_MS, C.ALARM2_INTERVAL_MS, C.ALARM2_MAX_REPEAT)
    return (C.ALARM3_ON, C.ALARM3_FREQ_HZ, C.ALARM3_BEEPS, C.ALARM3_BEEP_MS,
            C.ALARM3_PAUSE_MS, C.ALARM3_INTERVAL_MS, C.ALARM3_MAX_REPEAT)


async def alarm_task(ctx):
    """Dose window upkeep, blinking and sound of the shown alarm.
    Only the shown alarm makes a sound; each alarm has its own counter."""
    was_blinking = False
    while True:
        await asyncio.sleep_ms(50)
        now = time.ticks_ms()
        _trim_dose(now)                      # dose decays also without data
        _update_dose(ctx)

        a = _shown_alarm()
        blinking = _is_blinking(a)
        if blinking:
            on = (now // C.ALARM_BLINK_MS) % 2 == 0
            if on != S.blink_on:
                S.blink_on = on
                ctx.dirty = True
        elif was_blinking:                   # blinking just ended -> show steady
            S.blink_on = True
            ctx.dirty = True
        was_blinking = blinking

        if a == 0 or _is_acked(a) or not _fresh():
            continue
        on, freq, n, on_ms, pause, interval, maxrep = _alarm_cfg(a)
        count = S.dose_count if a == 3 else S.count
        last = S.dose_last_beep if a == 3 else S.last_beep
        if not on or (maxrep and count >= maxrep):
            continue
        if last is None or time.ticks_diff(now, last) >= interval:
            if a == 3:
                S.dose_last_beep = now
                S.dose_count += 1
                S.dose_blink_until = time.ticks_add(now, max(1000, _alarm3_sound_ms()))
                if C.ALARM3_SOUND == "siren":
                    asyncio.create_task(_siren())
                else:
                    asyncio.create_task(_beep(freq, n, on_ms, pause))
            else:
                S.last_beep = now
                S.count += 1
                asyncio.create_task(_beep(freq, n, on_ms, pause))


# ---------- log -------------------------------------------------------------------------
async def log_task(ctx):
    """One CSV line every LOG_INTERVAL_S while connected with fresh data."""
    while True:
        await asyncio.sleep_ms(C.LOG_INTERVAL_S * 1000)
        try:
            t, valid = ctx.rtc.datetime()
        except OSError:
            valid = False
        if valid != S.time_valid:
            S.time_valid = valid
            ctx.dirty = True
        if valid and S.connected and _fresh():
            was_full = LOG.full
            LOG.add(t, S.usv, S.cps, _shown_alarm(), S.dose_total)
            if LOG.full != was_full:
                ctx.dirty = True


# ---------- interface to main.py -------------------------------------------------------
def setup(ctx):
    asyncio.create_task(alarm_task(ctx))
    asyncio.create_task(log_task(ctx))


def on_shutdown(ctx):
    """Called before switching off and when stopped from Thonny."""
    LOG.flush()


def show_battery():
    """main.py asks whether to show the board battery line (not on DOSE page)."""
    return S.view != PAGE_DOSE


def on_short(ctx):
    rate_open = S.level > 0 and not S.acked
    dose_open = S.dose_active and not S.dose_acked
    if rate_open or dose_open:               # acknowledge all running alarms
        if S.level > 0:
            S.acked = True
        if S.dose_active:
            S.dose_acked = True
    else:
        S.view = (S.view + 1) % N_PAGES
    ctx.dirty = True


def _draw_status(lcd):
    st = S.status
    if S.batt is not None and S.connected:
        st += "  RC %d%%" % S.batt
    lcd.text_center(st, Y_STATUS, GREY, 1)
    ls = LOG.status(S.time_valid)
    if ls:
        lcd.text_center(ls, Y_LOGSTATUS, RED if LOG.full or LOG.error else GREY, 1)


def _draw_rate_page(lcd, fresh):
    col = _color(S.level) if fresh else GREY
    if fresh:
        usv_s, cps_s = _fmt_usv(S.usv), _fmt_cps(S.cps)
    else:
        usv_s = cps_s = "--"

    if S.view == PAGE_USV:
        big, big_unit, big_col = usv_s, "uSv/h", col
        small = "CPS " + cps_s
        small_col = WHITE if fresh else GREY
        tr = _trend(1, C.TREND_MIN_USV) if fresh else None
    else:
        big, big_unit, big_col = cps_s, "CPS", WHITE if fresh else GREY
        small = usv_s + " uSv/h"
        small_col = col
        tr = _trend(2, C.TREND_MIN_CPS) if fresh else None

    # large value, centred together with the trend arrow
    w = len(big) * 32
    if tr is None:
        lcd.text(big, (lcd.WIDTH - w) // 2, 90, big_col, 4)
    else:
        x = (lcd.WIDTH - (w + 8 + 24)) // 2
        lcd.text(big, x, 90, big_col, 4)
        acol = (GREY, ORANGE, GREEN)[tr]      # 0 grey, 1 orange, -1 green
        _arrow(lcd.fb, x + w + 8, 94, tr, acol)
    lcd.text_center(big_unit, 132, GREY, 2)
    lcd.text_center(small, 168, small_col, 2)

    # alarm frame
    a = _shown_alarm()
    if a and fresh:
        _alarm_box(lcd, a, _is_acked(a), _visible(a))


def _draw_dose_page(lcd, fresh):
    fb = lcd.fb
    cx, cy = 120, 126
    pct = _dose_pct()
    epct = _extra_pct()

    # colour: dimmed orange below 100 %, bright orange from 100 % (DOSE alarm);
    # while the DOSE alarm blinks, the bright phases alternate with dimmed ones
    if pct >= 100 and (not _is_blinking(3) or S.blink_on):
        col = ORANGE
    else:
        col = DIM_ORANGE

    outer, inner = _ring_geometry()
    filled = min(RING_SEGMENTS, int(pct / 100 * RING_SEGMENTS + 0.5))
    for i, seg in enumerate(outer):
        fb.poly(cx, cy, seg, col if i < filled else DARK, True)
    efilled = min(RING_STEPS, int(epct / 100 * RING_STEPS + 0.5))
    for i, seg in enumerate(inner):
        fb.poly(cx, cy, seg, BLUE if i < efilled else DARK_BLUE, True)
    _trefoil(fb, cx, cy, 25, col)

    # alarm badge at the top (the large frame does not fit on this page)
    a = _shown_alarm()
    if a and _visible(a):
        badge = _alarm_text(a) + ((" " + C.ACK_TEXT) if _is_acked(a) else "")
        lcd.text_center(badge, 62, _alarm_color(a), 1)

    lcd.text_center("%d %%" % int(pct + 0.5), 184, col, 3)
    lcd.text_center("%.2f / %.2f uSv  %dmin" % (S.dose_total, C.DOSE_LIMIT_USV,
                                                C.DOSE_WINDOW_MIN), 212, WHITE, 1)
    eta = _dose_eta()
    lcd.text_center(eta, 224, GREEN if eta == "SAFE" else (GREY if eta == "--" else col), 1)
    lcd.text_center("Extra today %.2f uSv (%d%%)" % (S.extra_total, int(epct + 0.5)),
                    236, BLUE, 1)
    lcd.text_center("H %.2f  D %.1f  DOSE %.1f/%d" % (C.LEVEL1_USV, C.LEVEL2_USV,
                                                      C.DOSE_LIMIT_USV, C.DOSE_WINDOW_MIN),
                    246, GREY, 1)


def draw(ctx):
    lcd = ctx.lcd
    fresh = _fresh()
    if S.view == PAGE_DOSE:
        _draw_dose_page(lcd, fresh)
    else:
        _draw_rate_page(lcd, fresh)
    _draw_status(lcd)


def _set_status(ctx, text, connected=False):
    S.status = text
    S.connected = connected
    ctx.dirty = True


async def loop(ctx):
    """Find the RadiaCode, connect, read every RC_POLL_MS, reconnect on loss."""
    try:
        import radiacode
    except ImportError:
        _set_status(ctx, ST_NO_AIOBLE)
        print("aioble is not installed – see docs/SETUP.md")
        while True:
            await asyncio.sleep_ms(10000)

    while True:
        rc = None
        try:
            _set_status(ctx, ST_SCAN)
            dev, name = await radiacode.find(C.RC_NAME, C.RC_NAME_PREFIX,
                                             C.RC_SCAN_MS)
            if dev is None:
                _set_status(ctx, ST_NOTFOUND)
                await asyncio.sleep_ms(C.RC_RECONNECT_MS)
                continue

            _set_status(ctx, ST_CONNECTING)
            S.name = name
            rc = await radiacode.RadiaCode.connect(dev)
            print("RadiaCode connected:", name)
            S.hist = []                      # rebuild the trend after reconnect
            _set_status(ctx, ST_CONNECTED, True)

            while rc.is_connected():
                d = await rc.read_data()
                if "cps" in d:
                    S.cps = d["cps"]
                    S.usv = d["dose_raw"] * C.RC_DOSE_FACTOR
                    S.last_ms = time.ticks_ms()
                    _add_hist(S.usv, S.cps)
                    _add_dose(S.usv, S.last_ms)
                if "batt" in d:
                    S.batt = d["batt"]
                _update_level(ctx)
                _update_dose(ctx)
                ctx.dirty = True
                await asyncio.sleep_ms(C.RC_POLL_MS)
        except Exception as e:
            print("RadiaCode:", repr(e))
        if rc:
            await rc.disconnect()
        S.last_rd_ms = None                  # gap: no dose is counted
        _set_status(ctx, ST_DISCONNECTED)
        await asyncio.sleep_ms(C.RC_RECONNECT_MS)
