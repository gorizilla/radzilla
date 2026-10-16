# Changelog

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
