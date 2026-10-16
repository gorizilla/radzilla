# Setup

Tested on macOS (Apple Silicon) with Thonny. Windows and Linux work the same
way, only the serial port name differs.

## 1. Requirements

- [Thonny](https://thonny.org) (≥ 4.x)
- USB-C **data** cable (some cables only charge)
- Python 3 on the computer, only needed for flashing with `esptool`

## 2. Flash MicroPython

Use the **official** MicroPython build. Third-party "unified" builds were
found to break hardware SPI (`TypeError: can't create 'SPI' instances`).

1. Download from <https://micropython.org/download/ESP32_GENERIC_S3/> the
   section **"Support for Octal-SPIRAM"**, latest **stable** release (no
   "preview"), file type **`.bin`**
   (e.g. `ESP32_GENERIC_S3-SPIRAM_OCT-20260824-v1.29.0.bin`).

2. **Option A – Thonny:** *Tools → Options → Interpreter → MicroPython (ESP32)
   → Install or update MicroPython (esptool)* → *≡ → Select local MicroPython
   image …* → choose the `.bin` → *Install*.
   If *Install* stays greyed out, re-select the target port.

3. **Option B – terminal (if Thonny fails):**

   ```bash
   pip3 install esptool
   ```

   Put the board into download mode without buttons – in the Thonny shell:

   ```python
   import machine; machine.bootloader()
   ```

   Close Thonny completely, then:

   ```bash
   ls /dev/cu.usbmodem*          # find the port
   python3 -m esptool --chip esp32s3 --port /dev/cu.usbmodemXXXX --before no_reset erase_flash
   python3 -m esptool --chip esp32s3 --port /dev/cu.usbmodemXXXX --before no_reset write_flash 0 ESP32_GENERIC_S3-SPIRAM_OCT-….bin
   ```

   (esptool 4.x uses `erase_flash` / `write_flash`, esptool 5.x uses
   `erase-flash` / `write-flash`.)

4. Unplug and replug USB, select the port in Thonny and check:

   ```python
   import os, gc; print(os.uname()); print(gc.mem_free())
   from machine import SPI, Pin
   print(SPI(1, baudrate=40000000, sck=Pin(6), mosi=Pin(7), miso=None))
   ```

   Expected: machine name ends with **"with Octal-SPIRAM"**, about
   **8 000 000** bytes free, and an `SPI(id=1, … miso=-1)` line.

## 3. Install aioble

Thonny's package manager searches PyPI, where aioble is not available.
Install it directly on the board via WiFi (Stop first, then in the shell):

```python
import network, time, mip
w = network.WLAN(network.STA_IF); w.active(True); w.connect("YOUR_SSID", "YOUR_PASSWORD")
while not w.isconnected(): time.sleep(0.5)
mip.install("aioble")
w.active(False)
```

Result: folder `/lib/aioble/` on the board.

## 4. Configure

1. Copy `board/secrets_example.py` to **`board/secrets.py`** and enter your
   WiFi networks (2.4 GHz only). This file is ignored by git.
2. Adjust `board/rc_config.py` if needed (thresholds, alarms, log) – see
   [CONFIGURATION.md](CONFIGURATION.md).

## 5. Upload

In Thonny: *View → Files*, open the local `board/` folder, select **all
`.py` files** → right click → **Upload to /**. Then press **RST**.

When updating later, `secrets.py` only needs to be uploaded again if it
changed.

## 6. First start

1. Disconnect the RadiaCode from the phone app.
2. Press RST. The bottom line shows *Scanning … → Connecting … → Connected*.
3. If the RTC has no valid time, the board syncs with the PTB atomic clock
   automatically (*Time sync …* → *Time OK*). Manual sync: double press PWR.
4. **Compare the µSv/h value with the RadiaCode display.** If it differs,
   adjust `RC_DOSE_FACTOR` in `rc_config.py`.

## 7. Get the logs

Click **Stop** in Thonny (the log buffer is saved on stop), then *View →
Files → logs* → right click a file → **Download to …**. Press RST afterwards
to restart.

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| Display frozen, nothing updates | Thonny stopped the program (connecting, Stop, file browser). Press RST, or run without Thonny (power bank / charger). |
| `TypeError: can't create 'SPI' instances` | Non-official firmware → flash the official build (step 2). |
| esptool: `Device not configured` | Board resets during connect → use `machine.bootloader()` and `--before no_reset`. |
| Thonny can't find aioble | Install via `mip` (step 3). |
| *aioble missing* on screen | aioble not installed on the board. |
| *Scanning … / Not found* | RadiaCode off, out of range, or still connected to the phone app. |
| `TimeoutError` after *Connected* | Bluetooth interference / weak signal; reconnects automatically. |
| *Sync: no WiFi set* | `secrets.py` missing or empty. |
| *Sync: no WiFi* | No known network in range, wrong password or 5 GHz network. |
| *Log: no time* | RTC not set yet – wait for the time sync or double press PWR. |
| *Log full* | Limits in `rc_config.py` reached – download and delete old logs. |
| Board gets warm | WiFi/Bluetooth active is normal; buzzer pin must be LOW (done in `boot.py`). |

For deeper analysis set `DIAG = True` in `config.py`: the shell then shows a
status line every 5 s (RTC time, shown time, redraw count and duration,
dose rate, free memory).
