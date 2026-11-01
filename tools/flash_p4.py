#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Flash the ESP32-P4 firmware through the native USB-Serial-JTAG port.

This board's CH343 "UART" port carries P4 logs (TX only for our purposes); the
ROM is flashed over the P4 native USB port. The USB-Serial/JTAG device only
enumerates while the chip is running (or in ROM download mode), so the sequence:
  1) enter download mode via the CH343 control lines (DTR->IO0, RTS->EN)
  2) wait for the USB-JTAG COM port to appear
  3) esptool write-flash via the USB port with --before no-reset
  4) release IO0 and reset via EN so the new firmware boots normally

Usage:
  python tools/flash_p4.py --build C:\\p4test\\firmware_app\\build \
        --uart COM4 --usb COM5
"""
import argparse
import os
import subprocess
import sys
import time

import serial
from serial.tools import list_ports


def find_usb_jtag_port(timeout=6.0):
    """Return a COM port whose VID:PID is Espressif USB-JTAG (303A:1001)."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        for p in list_ports.comports():
            if p.vid == 0x303A and p.pid == 0x1001:
                return p.device
        time.sleep(0.2)
    return None


def enter_download_mode(uart_port):
    s = serial.Serial(uart_port, 115200, timeout=0.2)
    s.dtr = False
    s.rts = False
    time.sleep(0.25)
    s.reset_input_buffer()
    s.dtr = True          # IO0 low
    s.rts = True          # EN low
    time.sleep(0.15)
    s.rts = False         # EN high -> sample IO0 low -> download mode
    time.sleep(0.25)
    s.close()


def boot_normally(uart_port):
    s = serial.Serial(uart_port, 115200, timeout=0.2)
    s.dtr = False         # IO0 high
    s.rts = True          # EN low
    time.sleep(0.15)
    s.rts = False         # EN high -> normal boot
    time.sleep(0.1)
    s.close()


def release_lines(uart_port):
    """Leave CH343 DTR/RTS deasserted so the board is not held in reset/download."""
    s = serial.Serial(uart_port, 115200, timeout=0.2)
    s.dtr = False
    s.rts = False
    time.sleep(0.15)
    s.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", default=r"C:\p4test\firmware_app\build")
    ap.add_argument("--uart", default="COM4")
    ap.add_argument("--usb", default=None, help="USB-JTAG COM port (auto-detect when omitted)")
    ap.add_argument("--baud", type=int, default=460800)
    args = ap.parse_args()

    print(f"[1/4] enter download mode via {args.uart} ...")
    enter_download_mode(args.uart)
    time.sleep(0.5)

    usb = args.usb or find_usb_jtag_port()
    if not usb:
        print("ERROR: USB-Serial-JTAG port not found (VID 303A:1001). Check the USB-C cable in the 'USB' port.")
        return 2
    print(f"[2/4] USB-JTAG port: {usb}")

    esptool = [sys.executable, "-m", "esptool", "--chip", "esp32p4", "-p", usb, "-b", str(args.baud),
               "--before", "no-reset", "--after", "hard-reset", "write-flash", "@flash_args"]
    print("[3/4] flashing ...")
    rc = subprocess.call(esptool, cwd=args.build)
    if rc != 0:
        print("ERROR: esptool failed")
        return rc

    print("[4/4] release IO0 and reset to boot normally")
    boot_normally(args.uart)
    time.sleep(0.3)
    release_lines(args.uart)
    print("done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

