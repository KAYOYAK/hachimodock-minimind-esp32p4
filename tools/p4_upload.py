#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Upload files to the board's TF card over the USB-Serial-JTAG port.

Firmware upload mode (no model.kmcu on card) protocol, with per-chunk ACK:
  board: "MMUP1\\n" when entering upload mode
  host : "PUT <name> <size>\\n" -> board: "READY\\n"
  host : <8192-byte chunk>     -> board: "." after writing it
  host : "END\\n"              -> board: "BYE\\n" and restarts

Usage:
  python tools/p4_upload.py --port COM5 \
      --file C:\\p4test\\artifacts\\minimind-3-q3e4.kmcu \
      --file C:\\p4test\\artifacts\\tokenizer.bin
"""
import argparse
import os
import time

import serial
from serial.tools import list_ports

CHUNK = 8192


def find_usb_jtag_port(timeout=20.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        for p in list_ports.comports():
            if p.vid == 0x303A and p.pid == 0x1001:
                return p.device
        time.sleep(0.3)
    return None


def read_line(ser, timeout=10.0):
    deadline = time.time() + timeout
    buf = bytearray()
    while time.time() < deadline:
        b = ser.read(1)
        if not b:
            continue
        if b in (b"\n", b"\r"):
            if buf:
                return bytes(buf)
            continue
        buf += b
        if len(buf) > 512:
            return bytes(buf)
    return bytes(buf)


def wait_for(ser, needle, timeout=30.0, verbose=True):
    deadline = time.time() + timeout
    while time.time() < deadline:
        line = read_line(ser, timeout=1.0)
        if not line:
            continue
        if verbose:
            print("  <", line.decode("utf-8", "replace"))
        if needle in line:
            return True
    return False


def wait_ack(ser, timeout=20.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        b = ser.read(1)
        if b == b".":
            return True
        if b == b"!":
            return False
    return False


def upload_file(ser, path):
    name = os.path.basename(path)
    size = os.path.getsize(path)
    print(f"uploading {name} ({size} bytes)")
    ser.write(f"PUT {name} {size}\n".encode())
    ser.flush()
    if not wait_for(ser, b"READY"):
        raise RuntimeError(f"no READY for {name}")
    sent = 0
    chunks = 0
    t0 = time.time()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(CHUNK)
            if not chunk:
                break
            ser.write(chunk)
            ser.flush()
            if not wait_ack(ser):
                raise RuntimeError(f"chunk {chunks} not acked at {sent} bytes")
            sent += len(chunk)
            chunks += 1
            if chunks % 512 == 0:
                dt = max(time.time() - t0, 0.001)
                print(f"  sent {sent/1024/1024:.1f} MiB ({sent/dt/1024:.0f} KiB/s)")
    if not wait_for(ser, b"DONE", timeout=120):
        raise RuntimeError(f"no DONE for {name}")
    print(f"  ok: {name}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", default=None)
    ap.add_argument("--file", action="append", default=None)
    ap.add_argument("--baud", type=int, default=921600)
    args = ap.parse_args()

    files = args.file or [
        r"C:\p4test\artifacts\minimind-3-q3e4.kmcu",
        r"C:\p4test\artifacts\tokenizer.bin",
    ]

    port = args.port or find_usb_jtag_port()
    if not port:
        print("USB-Serial-JTAG port not found (VID 303A:PID 1001)")
        return 2
    print("port:", port)

    ser = serial.Serial(port, args.baud, timeout=0.2)
    time.sleep(0.5)
    ser.reset_input_buffer()
    print("waiting for UPLOAD mode handshake (MMUP1) ...")
    if not wait_for(ser, b"MMUP1", timeout=5):
        print("(handshake not seen; assuming firmware already in upload mode)")
        ser.reset_input_buffer()

    try:
        for f in files:
            upload_file(ser, f)
        print("sending END (board will restart)")
        ser.write(b"END\n")
        ser.flush()
        wait_for(ser, b"BYE", timeout=10)
    finally:
        ser.close()
    print("upload done; board is restarting")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
