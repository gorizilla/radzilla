# Hardware

## Board: Waveshare ESP32-S3-LCD-1.69 (V2, without touch)

| Item | Value |
|---|---|
| SoC | ESP32-S3R8, dual-core Xtensa LX7, 240 MHz |
| Memory | 512 KB SRAM, **8 MB octal PSRAM**, 16 MB quad-SPI flash (W25Q128) |
| Radio | 2.4 GHz WiFi (b/g/n), Bluetooth 5 LE |
| Display | 1.69" IPS, 240×280, ST7789V2, 4-wire SPI |
| IMU | QMI8658 (accelerometer + gyroscope), I2C 0x6B – not used yet |
| RTC | PCF85063A, I2C 0x51, optional backup-battery header |
| Power | ETA6098 LiPo charger, ME6217 3.3 V LDO (800 mA), soft power switch |
| Other | passive buzzer, PWR / BOOT / RST buttons, USB-C (native USB) |

Product page: <https://www.waveshare.com/esp32-s3-lcd-1.69.htm>
Wiki and schematic: <https://www.waveshare.com/wiki/ESP32-S3-LCD-1.69>

### Hardware version

Boards with a **"V2QC" sticker** are version V2 – RadZilla is written for V2.
V1 boards use different pins:

| Signal | V1 | V2 |
|---|---|---|
| Buzzer | GPIO33 | GPIO42 |
| RTC_INT | GPIO41 | GPIO39 |
| SYS_EN (power latch) | GPIO35 | GPIO41 |
| SYS_OUT (PWR button) | GPIO36 | GPIO40 |

For a V1 board, adjust `board/pins.py` and `board/boot.py`.

## Pin assignment (V2)

### Used on the board

| Function | GPIO |
|---|---|
| LCD SCLK / MOSI / CS / DC / RST | 6 / 7 / 5 / 4 / 8 |
| LCD backlight (PWM) | 15 |
| I2C SCL / SDA (IMU, RTC) | 10 / 11 |
| IMU INT2 | 38 |
| RTC INT | 39 |
| Battery voltage (ADC, divider ×3) | 1 |
| Buzzer | 42 |
| SYS_OUT – PWR button (LOW = pressed) | 40 |
| SYS_EN – power latch (HIGH = on) | 41 |
| BOOT button | 0 |
| USB D− / D+ | 19 / 20 |
| Octal PSRAM – **never use** | 35, 36, 37 |

### 12-pin header (free pins)

| Pin | Signal | Notes |
|---|---|---|
| 1 | GPIO18 | free |
| 2 | GPIO17 | free |
| 3 | GPIO16 | free |
| 4 | GPIO3 | free, strapping pin – do not pull hard during boot |
| 5 | GPIO2 | free, ADC capable |
| 6 | SDA (GPIO11) | shared I2C bus, pull-ups 2.2 kΩ on board |
| 7 | SCL (GPIO10) | shared I2C bus |
| 8 | TXD (GPIO43) | UART1 TX in RadZilla |
| 9 | RXD (GPIO44) | UART1 RX in RadZilla |
| 10 | 3V3 | LDO output, max. 800 mA in total |
| 11 | GND | |
| 12 | VBUS | 5 V, only when USB is connected |

> ⚠ All GPIOs are **3.3 V only**. The wire colours of the supplied cable do
> not follow any standard (red is not necessarily 5 V) – measure before use.
> The pin-1 side of the header is not documented here; verify with a
> multimeter (3V3 / GND / VBUS).

Free GPIOs are left unconfigured (high impedance) by RadZilla.

## Power and battery

- **Battery:** 1-cell LiPo 3.7 V with protection circuit, plug **MX1.25 2-pin**.
  ⚠ **Check the polarity** against the "+ / −" marking on the board – many
  ready-made cables are wired the other way round and can destroy the charger.
- **Charging:** automatic while USB-C is connected (ETA6098), also during
  operation. The charge current is set by a resistor on the board; use a
  quality cell of at least ~1000 mAh.
- **Power switch:** pressing PWR connects the battery; the firmware keeps it
  on via SYS_EN (`boot.py`). A long press releases SYS_EN and switches off.
  On USB power the board cannot switch itself off.
- **Battery reading:** without a battery the reading shows the charger
  voltage (~4.2 V).

### Runtime estimate (not measured)

| Load | approx. |
|---|---|
| ESP32-S3 active + Bluetooth | 40–50 mA |
| Backlight (200/255) | 15–30 mA |
| Rest | ~5 mA |
| **Total** | **~60–85 mA** |

For 14 h: about **1500–2000 mAh**. Lower backlight, lower CPU clock or light
sleep can roughly halve the consumption (not implemented yet).

## RadiaCode

- Tested with **RadiaCode-102** (firmware as of 2026-10).
- Connection: Bluetooth LE, write characteristic
  `e63215e6-7003-49d8-96b0-b024798fb901`, notify characteristic
  `e63215e7-7003-49d8-96b0-b024798fb901`.
- A RadiaCode accepts **one Bluetooth connection at a time** – the phone app
  must be disconnected.
