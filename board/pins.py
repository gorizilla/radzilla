# pins.py – pin assignment of the Waveshare ESP32-S3-LCD-1.69, hardware V2.
#
# RadZilla – external display for RadiaCode
# Copyright (c) 2026 Shimizilla – licensed under CC BY-NC 4.0 (see LICENSE.md)
#
# Source: Waveshare schematic "ESP32-S3-LCD-1.69_V2.pdf".
# Boards WITHOUT the "V2QC" sticker (V1) use different pins for buzzer,
# RTC_INT, SYS_EN and SYS_OUT – see docs/HARDWARE.md.

# -----------------------------------------------------------------------------
# USED ON THE BOARD – do not use for other purposes
# -----------------------------------------------------------------------------
LCD_SCLK = 6
LCD_MOSI = 7
LCD_CS = 5
LCD_DC = 4
LCD_RST = 8
LCD_BL = 15       # backlight (PWM)

I2C_SCL = 10      # shared: QMI8658, PCF85063, header pin 7
I2C_SDA = 11      # shared: QMI8658, PCF85063, header pin 6

IMU_INT2 = 38     # QMI8658 interrupt 2
RTC_INT = 39      # PCF85063 interrupt
BAT_ADC = 1       # battery voltage via 1:3 divider
BUZZER = 42       # passive buzzer
SYS_OUT = 40      # PWR button state (LOW = pressed)
SYS_EN = 41       # battery power latch (HIGH = keep on)
BOOT_BTN = 0
USB_DN = 19
USB_DP = 20
# GPIO35–37 are used by the octal PSRAM – never use them.

ADDR_QMI8658 = 0x6B
ADDR_PCF85063 = 0x51

# -----------------------------------------------------------------------------
# FREE – 12-pin header
# Left unconfigured (high impedance) until an application uses them.
# Logic level 3.3 V – never apply 5 V signals!
# -----------------------------------------------------------------------------
GPIO_18 = 18      # header pin 1
GPIO_17 = 17      # header pin 2
GPIO_16 = 16      # header pin 3
GPIO_3 = 3        # header pin 4 – strapping pin, do not pull hard at boot
GPIO_2 = 2        # header pin 5 – ADC capable

FREE_GPIO = (GPIO_18, GPIO_17, GPIO_16, GPIO_3, GPIO_2)

UART_TX = 43      # header pin 8
UART_RX = 44      # header pin 9

# Header pin 10 = 3V3, pin 11 = GND, pin 12 = VBUS (5 V only when on USB)
