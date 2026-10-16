# Notice

## ⚠️ Experimental software – read before use

RadZilla is an **experimental hobby project**. It is **not** a certified
radiation measuring or safety device and must **not** be relied upon for
radiation protection, safety decisions, medical purposes or any situation in
which a failure could cause harm.

- Readings, colours, trend arrows and alarms shown by RadZilla are derived
  from data received over Bluetooth and may be **delayed, wrong or missing**
  (e.g. connection loss, software errors, empty battery, wrong configuration).
- The dose-rate conversion factor and the alarm thresholds are user settings
  and have **not** been validated or calibrated.
- Always use the RadiaCode device itself and the manufacturer's official app
  as the authoritative source, and follow applicable radiation-protection
  rules.

**No warranty, no liability.** The software is provided "as is", without
warranty of any kind, express or implied. To the maximum extent permitted by
law, the author accepts no liability for any direct or indirect damage
arising from the use, misuse or inability to use this software or the
hardware it controls (including damage to batteries, boards or connected
devices). Use at your own risk. Mandatory statutory liability (e.g. for
intent or gross negligence, where it cannot be excluded by law) remains
unaffected.

## No affiliation, trademarks

RadZilla is an independent project. It is **not affiliated with, endorsed
by or supported by** the manufacturer of RadiaCode devices, by Waveshare, by
Espressif or by the MicroPython project.

"RadiaCode", "Waveshare", "ESP32" and other product names are trademarks of
their respective owners and are used here only to describe compatibility.

## Acknowledgements

Many thanks to the authors of the projects RadZilla builds on:

| Project | Used for | License |
|---|---|---|
| [cdump/radiacode](https://github.com/cdump/radiacode) | The RadiaCode Bluetooth protocol implemented in `board/radiacode.py` follows this Python library (command IDs, framing, data-buffer record layout). No code was copied; the protocol was re-implemented for MicroPython. | MIT |
| [MicroPython](https://micropython.org) | Firmware running on the board | MIT |
| [aioble](https://github.com/micropython/micropython-lib/tree/master/micropython/bluetooth/aioble) (micropython-lib) | Bluetooth Low Energy library, installed separately on the board via `mip` | MIT |
| [Waveshare ESP32-S3-LCD-1.69 wiki](https://www.waveshare.com/wiki/ESP32-S3-LCD-1.69) | Pin assignments taken from the published schematic | – |
| [PTB](https://www.ptb.de) (Physikalisch-Technische Bundesanstalt) | Public NTP time servers `ptbtime1/2.ptb.de` | – |

Third-party software is not included in this repository and is not covered by
RadZilla's license. Each component keeps its own license.
