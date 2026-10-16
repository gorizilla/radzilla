# secrets_example.py – template for your private settings.
#
# RadZilla – external display for RadiaCode
# Copyright (c) 2026 Shimizilla – licensed under CC BY-NC 4.0 (see LICENSE.md)
#
# HOW TO USE
#   1. Copy this file to "secrets.py" (same folder).
#   2. Enter your own WiFi networks in secrets.py.
#   3. Upload secrets.py to the board together with the other files.
#
# secrets.py is listed in .gitignore and is never committed to git.
# Do NOT put real credentials into this example file.
#
# WiFi is only used for the time sync with the PTB atomic clock (NTP).
# The board scans for networks and connects to the strongest known one.
# Only 2.4 GHz networks are supported by the ESP32-S3.

WIFI_NETWORKS = [
    # ("SSID", "password"),
    ("YOUR_SSID", "YOUR_PASSWORD"),
    ("YOUR_PHONE_HOTSPOT", "YOUR_PASSWORD"),
]
