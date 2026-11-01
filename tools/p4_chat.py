#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Talk to the MiniMind-3 firmware over the USB-Serial-JTAG console.

Usage:
  python tools/p4_chat.py --port COM5 --prompt "你好，介绍一下你自己" --timeout 120
  python tools/p4_chat.py --port COM5            # interactive
"""
import argparse
import time

import serial
from serial.tools import list_ports


def find_usb_jtag_port(timeout=15.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        for p in list_ports.comports():
            if p.vid == 0x303A and p.pid == 0x1001:
                return p.device
        time.sleep(0.3)
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", default=None)
    ap.add_argument("--prompt", default=None)
    ap.add_argument("--timeout", type=float, default=120.0)
    args = ap.parse_args()

    port = args.port or find_usb_jtag_port()
    if not port:
        print("USB-Serial-JTAG port not found")
        return 2
    print("port:", port)
    ser = serial.Serial(port, 921600, timeout=0.3)
    ser.reset_input_buffer()

    # wait until the firmware prints "Chat ready" or a prompt
    deadline = time.time() + args.timeout
    ready = False
    while time.time() < deadline:
        line = ser.readline()
        if not line:
            continue
        text = line.decode("utf-8", "replace")
        print(text, end="", flush=True)
        if "Chat ready" in text or "User:" in text:
            ready = True
            break
    if not ready:
        print("\n(firmware did not report Chat ready; it may be still loading)")
        ser.close()
        return 1

    if args.prompt is not None:
        ser.write((args.prompt + "\n").encode("utf-8"))
        ser.flush()
        deadline = time.time() + args.timeout
        while time.time() < deadline:
            data = ser.read(4096)
            if data:
                print(data.decode("utf-8", "replace"), end="", flush=True)
        ser.close()
        print()
        return 0

    # interactive
    try:
        while True:
            line = input("User: ")
            if line.strip() in ("/quit", "/exit"):
                break
            ser.write((line + "\n").encode("utf-8"))
            ser.flush()
            last = time.time()
            while time.time() - last < 0.8:
                data = ser.read(4096)
                if data:
                    print(data.decode("utf-8", "replace"), end="", flush=True)
                    last = time.time()
    except (KeyboardInterrupt, EOFError):
        pass
    finally:
        ser.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
