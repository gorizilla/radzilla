# logger.py – CSV log of the RadiaCode readings with overflow protection.
#
# RadZilla – external display for RadiaCode
# Copyright (c) 2026 Shimizilla – licensed under CC BY-NC 4.0 (see LICENSE.md)
#
#   /logs/rc_2026-10-16_1401.csv
#     Time;uSv/h;CPS;Alarm;Dose15
#     2026-10-16 14:01:03;0,12;8,53;0;0,03
#
#   Alarm  0 = none, 1 = HIGH, 2 = DANGER, 3 = DOSE (alarm shown, by priority)
#   Dose15 dose in µSv within the dose window (rc_config.DOSE_WINDOW_MIN)
#
# * one file per start, new file after LOG_MAX_AGE_H hours of run time
# * buffered in RAM, written every LOG_FLUSH_S seconds (protects the flash)
# * clean-up: deletes files whose last entry is older than LOG_MAX_AGE_H,
#   keeps LOG_MAX_FILES / LOG_MAX_TOTAL_KB and LOG_MIN_FREE_KB free flash;
#   the current file is never deleted. If the limits cannot be met,
#   logging stops ("Log full") while the rest of the system keeps running.
import os
import time

HEADER = "Time;uSv/h;CPS;Alarm;Dose15\n"


def _secs(t):
    """(Y, M, D, h, m, s) local time -> continuous seconds."""
    from ntp import days_from_civil
    return days_from_civil(t[0], t[1], t[2]) * 86400 + t[3] * 3600 + t[4] * 60 + t[5]


def _parse_ts(s):
    """'2026-10-16 14:01:03' -> tuple or None."""
    try:
        return (int(s[0:4]), int(s[5:7]), int(s[8:10]),
                int(s[11:13]), int(s[14:16]), int(s[17:19]))
    except (ValueError, IndexError):
        return None


def _parse_name(name):
    """'rc_2026-10-16_1401.csv' (or '..._1401_2.csv') -> tuple or None."""
    try:
        return (int(name[3:7]), int(name[8:10]), int(name[11:13]),
                int(name[14:16]), int(name[16:18]), 0)
    except (ValueError, IndexError):
        return None


def _num(v):
    """Number with 2 decimals and decimal comma."""
    return ("%.2f" % v).replace(".", ",")


class Logger:
    def __init__(self, cfg):
        self.c = cfg
        self.path = None          # current file
        self.start_s = None       # start time of the current file (seconds)
        self.buf = []
        self.last_flush = time.ticks_ms()
        self.last_check = None
        self.full = False
        self.error = None

    # ---------- status line ----------
    def status(self, time_valid):
        if not self.c.LOG_ON:
            return ""
        if self.full:
            return "Log full"
        if self.error:
            return "Log error"
        if not time_valid:
            return "Log: no time"
        return "LOG"

    # ---------- file system ----------
    def _ensure_dir(self):
        try:
            os.stat(self.c.LOG_DIR)
        except OSError:
            os.mkdir(self.c.LOG_DIR)

    def _files(self):
        """Log files, oldest first (the name contains date and time)."""
        try:
            names = [n for n in os.listdir(self.c.LOG_DIR)
                     if n.startswith("rc_") and n.endswith(".csv")]
        except OSError:
            return []
        names.sort()
        return [self.c.LOG_DIR + "/" + n for n in names]

    @staticmethod
    def _size(path):
        try:
            return os.stat(path)[6]
        except OSError:
            return 0

    def _free_kb(self):
        s = os.statvfs(self.c.LOG_DIR)
        return s[0] * s[3] // 1024

    def _last_entry_s(self, path):
        """Time of the last entry, otherwise the time from the file name."""
        try:
            size = self._size(path)
            with open(path, "rb") as f:
                if size > 96:
                    f.seek(size - 96)
                tail = f.read().decode()
            for line in reversed(tail.split("\n")):
                t = _parse_ts(line)
                if t:
                    return _secs(t)
        except (OSError, UnicodeError):
            pass
        t = _parse_name(path.rsplit("/", 1)[-1])
        return _secs(t) if t else None

    def _delete(self, path):
        try:
            os.remove(path)
            print("Log deleted:", path)
        except OSError:
            pass

    def cleanup(self, now_s):
        """Apply age, count, size and free-space limits."""
        c = self.c
        files = [p for p in self._files() if p != self.path]
        # 1. too old
        max_age = c.LOG_MAX_AGE_H * 3600
        keep = []
        for p in files:
            last = self._last_entry_s(p)
            if last is not None and now_s - last > max_age:
                self._delete(p)
            else:
                keep.append(p)
        files = keep
        # 2. count / total size / free space -> delete the oldest first
        cur = 1 if self.path else 0
        while files:
            total_kb = (sum(self._size(p) for p in files) +
                        (self._size(self.path) if self.path else 0)) // 1024
            if (len(files) + cur <= c.LOG_MAX_FILES and
                    total_kb <= c.LOG_MAX_TOTAL_KB and
                    self._free_kb() >= c.LOG_MIN_FREE_KB):
                break
            self._delete(files.pop(0))
        # 3. still not enough -> log full
        total_kb = (self._size(self.path) if self.path else 0) // 1024 + \
            sum(self._size(p) for p in files) // 1024
        self.full = (self._free_kb() < c.LOG_MIN_FREE_KB or
                     total_kb > c.LOG_MAX_TOTAL_KB)

    def _new_file(self, t):
        self._ensure_dir()
        base = "%s/rc_%04d-%02d-%02d_%02d%02d" % (self.c.LOG_DIR, t[0], t[1], t[2], t[3], t[4])
        path = base + ".csv"
        n = 2
        while True:                         # avoid overwriting (same minute)
            try:
                os.stat(path)
                path = "%s_%d.csv" % (base, n)
                n += 1
            except OSError:
                break
        with open(path, "w") as f:
            f.write(HEADER)
        self.path = path
        self.start_s = _secs(t)
        print("Log created:", path)

    # ---------- writing ----------
    def add(self, t, usv, cps, alarm, dose):
        """Queue one line. t = valid local time tuple, alarm = 0..3,
        dose = µSv within the dose window."""
        if not self.c.LOG_ON or self.full or self.error:
            return
        now_s = _secs(t)
        try:
            if self.path is None:
                self._ensure_dir()
                self.cleanup(now_s)
                self.last_check = time.ticks_ms()
                if self.full:
                    return
                self._new_file(t)
            elif now_s - self.start_s >= self.c.LOG_MAX_AGE_H * 3600:
                self.flush()
                self._new_file(t)
            self.buf.append("%04d-%02d-%02d %02d:%02d:%02d;%s;%s;%d;%s\n" % (
                t[0], t[1], t[2], t[3], t[4], t[5],
                _num(usv), _num(cps), alarm, _num(dose)))
            now = time.ticks_ms()
            if time.ticks_diff(now, self.last_flush) >= self.c.LOG_FLUSH_S * 1000:
                self.flush()
            if time.ticks_diff(now, self.last_check) >= self.c.LOG_CHECK_S * 1000:
                self.last_check = now
                self.cleanup(now_s)
        except OSError as e:
            self.error = e
            print("Log error:", repr(e))

    def flush(self):
        """Write the buffer to the file (also called on stop / shut-down)."""
        self.last_flush = time.ticks_ms()
        if not self.buf or not self.path:
            return
        try:
            if self._free_kb() < self.c.LOG_MIN_FREE_KB:
                self.full = True
                self.buf = []
                print("Log full")
                return
            with open(self.path, "a") as f:
                for line in self.buf:
                    f.write(line)
            self.buf = []
        except OSError as e:
            self.error = e
            print("Log error:", repr(e))
