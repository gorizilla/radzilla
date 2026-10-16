# ntp.py – time sync with the PTB atomic clock via NTP.
#
# RadZilla – external display for RadiaCode
# Copyright (c) 2026 Shimizilla – licensed under CC BY-NC 4.0 (see LICENSE.md)
#
# Flow: WiFi on -> scan -> connect to the strongest known network ->
# query NTP -> convert UTC to German local time (CET/CEST with automatic
# daylight saving time) -> write to the RTC -> WiFi off again.
#
# The calendar functions are independent of the firmware's epoch, so they
# behave identically on MicroPython and CPython (used for testing).
import asyncio
import socket
import struct

NTP_DELTA = 2208988800   # seconds between 1900-01-01 and 1970-01-01


# ---------- calendar ----------------------------------------------------------
def days_from_civil(y, m, d):
    """Days since 1970-01-01 (proleptic Gregorian calendar)."""
    y -= m <= 2
    era = (y if y >= 0 else y - 399) // 400
    yoe = y - era * 400
    doy = (153 * (m + (-3 if m > 2 else 9)) + 2) // 5 + d - 1
    doe = yoe * 365 + yoe // 4 - yoe // 100 + doy
    return era * 146097 + doe - 719468


def civil_from_days(z):
    """Days since 1970-01-01 -> (year, month, day)."""
    z += 719468
    era = (z if z >= 0 else z - 146096) // 146097
    doe = z - era * 146097
    yoe = (doe - doe // 1460 + doe // 36524 - doe // 146096) // 365
    y = yoe + era * 400
    doy = doe - (365 * yoe + yoe // 4 - yoe // 100)
    mp = (5 * doy + 2) // 153
    d = doy - (153 * mp + 2) // 5 + 1
    m = mp + (3 if mp < 10 else -9)
    return y + (m <= 2), m, d


def _days_in_month(y, m):
    if m == 2:
        return 29 if (y % 4 == 0 and y % 100 != 0) or y % 400 == 0 else 28
    return 30 if m in (4, 6, 9, 11) else 31


def _last_sunday(y, m):
    last = _days_in_month(y, m)
    wd = (days_from_civil(y, m, last) + 4) % 7   # 0 = Sunday
    return last - wd


def is_dst(unix):
    """EU summer time: last Sunday of March 01:00 UTC until
    last Sunday of October 01:00 UTC."""
    y = civil_from_days(unix // 86400)[0]
    start = days_from_civil(y, 3, _last_sunday(y, 3)) * 86400 + 3600
    end = days_from_civil(y, 10, _last_sunday(y, 10)) * 86400 + 3600
    return start <= unix < end


def berlin_from_unix(unix):
    """UTC Unix time -> (year, month, day, hour, min, sec, weekday 0=Sun)."""
    local = unix + 3600 + (3600 if is_dst(unix) else 0)
    days, rem = divmod(local, 86400)
    y, m, d = civil_from_days(days)
    return y, m, d, rem // 3600, (rem % 3600) // 60, rem % 60, (days + 4) % 7


# ---------- NTP ---------------------------------------------------------------
def query(host, timeout_s=2):
    """Single NTP request. Returns UTC Unix time in seconds."""
    addr = socket.getaddrinfo(host, 123)[0][-1]
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.settimeout(timeout_s)
        pkt = bytearray(48)
        pkt[0] = 0x1B                    # LI=0, version 3, mode 3 (client)
        s.sendto(pkt, addr)
        msg = s.recv(48)
    finally:
        s.close()
    secs, frac = struct.unpack("!II", msg[40:48])
    if secs == 0:
        raise OSError("empty NTP reply")
    return secs - NTP_DELTA + (1 if frac >= 0x80000000 else 0)


def _known_by_strength(wlan, networks):
    """Known networks that are in range, strongest first."""
    known = {ssid: pw for ssid, pw in networks}
    found = {}
    for res in wlan.scan():              # (ssid, bssid, channel, rssi, ...)
        try:
            ssid = res[0].decode()
        except UnicodeError:
            continue
        if ssid in known and (ssid not in found or res[3] > found[ssid]):
            found[ssid] = res[3]
    return [(s, known[s]) for s in sorted(found, key=lambda s: -found[s])]


async def _connect(wlan, ssid, password, timeout_ms):
    wlan.connect(ssid, password)
    waited = 0
    while not wlan.isconnected():
        if waited >= timeout_ms:
            wlan.disconnect()
            return False
        await asyncio.sleep_ms(200)
        waited += 200
    return True


async def sync(rtc, networks, servers, timeout_ms=15000):
    """WiFi on, get the time, set the RTC, WiFi off.

    networks: list of (ssid, password). Returns (True, local time tuple)
    or (False, short reason) – the reason is shown on the display."""
    import network
    if not networks:
        return False, "no WiFi set"
    wlan = network.WLAN(network.STA_IF)
    try:
        wlan.active(True)
        candidates = _known_by_strength(wlan, networks)
        if not candidates:
            return False, "no WiFi"
        connected = False
        for ssid, pw in candidates:
            print("WiFi: connecting to", ssid)
            if await _connect(wlan, ssid, pw, timeout_ms):
                connected = True
                break
        if not connected:
            return False, "no WiFi"

        unix = None
        for host in servers:
            try:
                unix = query(host)
                print("NTP:", host, "OK")
                break
            except Exception as e:
                print("NTP:", host, "error:", e)
        if unix is None:
            return False, "no NTP"

        t = berlin_from_unix(unix)
        rtc.set_datetime(t[0], t[1], t[2], t[3], t[4], t[5], t[6])
        return True, t
    finally:
        try:
            wlan.disconnect()
        except Exception:
            pass
        wlan.active(False)
