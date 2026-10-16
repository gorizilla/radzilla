# Changelog

## Unreleased

- Repository: folders for 3D-printed parts (`hardware/3d/stl/`, STL only,
  print-settings template) and photos (`media/photos/`, JPEG).
- `.gitignore` excludes G-code; `.gitattributes` marks binaries and contains
  an optional Git LFS template.

## v1.1.0 – 2026-10-16

- **New: dose alarm DOSE** (orange) – triggers when more than
  `DOSE_LIMIT_USV` (default 2.5 µSv) were collected within
  `DOSE_WINDOW_MIN` (default 15 min). Shows the collected dose in the frame,
  own beep pattern (2× 2500 Hz, every 5 s, max. 5 times), same hysteresis.
- Alarm priority DANGER > DOSE > HIGH; one short PWR press acknowledges all.
- New defaults: HIGH from **0.28 µSv/h** (≈ 2× background), DANGER from
  **10 µSv/h** (immediate alarm).
- CSV log: new column `Dose15`, alarm code `3` = DOSE.
  Header is now `Time;uSv/h;CPS;Alarm;Dose15`.

## v1.0.0 – 2026-10-16

First release.

- Base system for the Waveshare ESP32-S3-LCD-1.69 (V2): status bar with clock
  and battery voltage, PWR button (short / double / long press), safe
  shut-down, buzzer muted at boot.
- Time sync with the PTB atomic clock via NTP (CET/CEST with automatic
  daylight saving time), list of known WiFi networks, strongest one is used.
- Bluetooth connection to RadiaCode 10x with automatic reconnect.
- Large dose-rate / count-rate display with colour levels and trend arrow.
- Two alarm levels (HIGH / DANGER) with hysteresis, blinking HUD frame,
  configurable beeps, repeat limits and acknowledge.
- CSV log with retention (24 h), file/size limits and minimum free space.
- Secrets kept out of git (`secrets.py`), documentation in `docs/`.
