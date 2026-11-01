#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""HachimoDock 最小 host 原型（PC 侧，M1 验证）。

目标：不依赖官方客户端，直接用 CH343 串口验证官方 USB 协议：
  1) 自动探测设备波特率（v3 4 Mbaud，回退 2M/3M/921600/115200）
  2) 等设备主动发 hello（含 capabilities）
  3) 每 2 秒发 system/heartbeat 保活
  4) 发一条 ui/conversation 测试气泡，等 protocol/ack
  5) 打印设备发来的 input/event 等消息

用法：
  python tools/hachi_probe.py                 # 自动找 CH343 端口
  python tools/hachi_probe.py --port COM3
  python tools/hachi_probe.py --bubble-text "你好，我是本地 AI" --listen-seconds 30
"""
import argparse
import json
import sys
import threading
import time

import serial
from serial.tools import list_ports

CH343_VID = 0x1A86
CH343_PID = 0x55D3
BAUD_CANDIDATES = [4000000, 2000000, 3000000, 921600, 115200]


def find_ch343_port():
    for p in list_ports.comports():
        if p.vid == CH343_VID and p.pid == CH343_PID:
            return p.device
    return None


def open_serial(port, baud):
    s = serial.Serial()
    s.port = port
    s.baudrate = baud
    s.timeout = 0.2
    s.write_timeout = 1.0
    s.rtscts = False
    s.dsrdtr = False
    s.open()
    # 避免 CH343 的 DTR/RTS 把设备拉进下载/复位
    try:
        s.dtr = False
        s.rts = False
    except Exception:
        pass
    s.reset_input_buffer()
    return s


def probe_baud(port, per_baud_wait=4.0):
    for baud in BAUD_CANDIDATES:
        try:
            s = open_serial(port, baud)
        except Exception as e:
            print(f"[probe] {baud}: open failed ({e})")
            continue
        print(f"[probe] trying {baud} ...")
        deadline = time.time() + per_baud_wait
        found = None
        raw_tail = []
        while time.time() < deadline:
            line = s.readline()
            if not line:
                continue
            text = line.decode("utf-8", "ignore").strip()
            if not text:
                continue
            raw_tail.append(text)
            if len(raw_tail) > 6:
                raw_tail.pop(0)
            if '"topic"' in text and '"hello"' in text.replace(" ", ""):
                try:
                    found = json.loads(text)
                    break
                except Exception:
                    pass
        if found:
            print(f"[probe] hello found at {baud} baud")
            for t in raw_tail:
                print("  boot>", t[:160])
            return s, baud, found
        s.close()
        print(f"[probe] no hello at {baud}" + (f"; last lines: {raw_tail[-2:]}" if raw_tail else ""))
    return None, None, None


def summarize_hello(hello):
    p = hello.get("payload", {})
    caps = p.get("capabilities", {})
    tr = caps.get("transport", {})
    disp = caps.get("display", {})
    fw = caps.get("features", {})
    print("=== device hello ===")
    print(f"  boardDeviceId : {p.get('boardDeviceId')}")
    print(f"  deviceModel   : {p.get('deviceModel')}")
    print(f"  fw            : {p.get('fw')} (buildId {p.get('buildId')}, dirty={p.get('buildDirty')})")
    print(f"  protocolSchema: {p.get('protocolSchema')}  wireProtocol={p.get('wireProtocol')}")
    print(f"  transport     : usbUart={tr.get('usbUart')} baud={tr.get('usbUartBaud')} nativeUsb={tr.get('nativeUsb')}")
    print(f"  display       : {disp.get('width')}x{disp.get('height')} {disp.get('pixelFormat')}")
    print(f"  features      : voice={caps.get('voice')} audio={caps.get('audio')} widgets={caps.get('widgets')} "
          f"touch={caps.get('touch')} firmwareOta={caps.get('firmwareOta')}")
    print(f"  controls      : sw1={caps.get('controls', {}).get('sw1')} sw2={caps.get('controls', {}).get('sw2')} "
          f"sw3={caps.get('controls', {}).get('sw3')} activeLow={caps.get('controls', {}).get('activeLow')}")
    return p


class Host:
    def __init__(self, ser):
        self.ser = ser
        self.lock = threading.Lock()
        self.stop = False
        self.rx_count = 0
        self.acks = []

    def send(self, topic, payload):
        msg = {"topic": topic, "payload": payload}
        raw = (json.dumps(msg, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
        with self.lock:
            self.ser.write(raw)
            self.ser.flush()
        print(f"  >> {topic} {json.dumps(payload, ensure_ascii=False)[:200]}")

    def heartbeat_loop(self, interval=2.0):
        i = 0
        while not self.stop:
            try:
                self.send("system/heartbeat", {"ts": int(time.time() * 1000), "seq": i})
            except Exception as e:
                print("  !! heartbeat write failed:", e)
                return
            i += 1
            time.sleep(interval)

    def ping_bubble(self, text):
        req = {"sessionId": "hachi-test-1", "state": "speaking", "name": "小西",
               "text": text, "role": "pet", "final": True, "requestId": "hachi-req-1"}
        self.send("ui/conversation", req)

    def end_bubble(self):
        self.send("ui/conversation", {"sessionId": "hachi-test-1", "state": "ended"})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", default=None, help="默认自动找 CH343 (VID 1A86 PID 55D3)")
    ap.add_argument("--bubble-text", default="你好，我是本地 AI 原型")
    ap.add_argument("--listen-seconds", type=float, default=30.0)
    ap.add_argument("--no-bubble", action="store_true")
    args = ap.parse_args()

    port = args.port or find_ch343_port()
    if not port:
        print("没找到 CH343 串口（VID 1A86 PID 55D3）。请把哈基米机 USB-C 插到电脑，确认设备管理器出现 CH343 串口。")
        return 2
    print("port:", port)

    ser, baud, hello = probe_baud(port)
    if not ser:
        print("没有在候选波特率上收到设备 hello。检查设备是否上电、是否已烧 v3 固件。")
        return 2

    info = summarize_hello(hello)
    host = Host(ser)
    threading.Thread(target=host.heartbeat_loop, daemon=True).start()

    t0 = time.time()
    bubble_sent = False
    last_rx = time.time()
    try:
        while time.time() - t0 < args.listen_seconds:
            line = ser.readline()
            if not line:
                # 长时间没数据只提示一次
                if time.time() - last_rx > 6:
                    print(f"  .. no data from device ({time.time()-t0:.0f}s)")
                    last_rx = time.time()
                continue
            last_rx = time.time()
            text = line.decode("utf-8", "ignore").strip()
            if not text:
                continue
            host.rx_count += 1
            try:
                msg = json.loads(text)
            except Exception:
                print("  << (non-json)", text[:160])
                continue
            topic = msg.get("topic", "?")
            payload = msg.get("payload", {})
            shown = json.dumps(payload, ensure_ascii=False)
            print(f"  << {topic} {shown[:240]}")
            if topic == "protocol/ack":
                host.acks.append(payload)
            if topic == "input/event":
                action = payload.get("action")
                print(f"     [input] action={action} context={payload.get('context')}")
                # 按键实测时自动回一条气泡
                if action and not args.no_bubble:
                    host.send("ui/conversation", {
                        "sessionId": "hachi-test-btn", "state": "speaking", "name": "小西",
                        "role": "pet", "final": True,
                        "text": f"你按了 {action}",
                    })
            if not bubble_sent and time.time() - t0 > 5.0 and not args.no_bubble:
                host.ping_bubble(args.bubble_text)
                bubble_sent = True
                time.sleep(0.5)
            if time.time() - t0 > 12.0 and host.acks:
                print("=== protocol/ack summary ===")
                for a in host.acks[-5:]:
                    print(" ", json.dumps(a, ensure_ascii=False)[:240])
    finally:
        host.stop = True
        try:
            if not args.no_bubble:
                host.end_bubble()
        except Exception:
            pass
        ser.close()

    print(f"\n[done] baud={baud}, rx_msgs={host.rx_count}, acks={len(host.acks)}")
    if not host.acks and bubble_sent:
        print("注意：没收到 protocol/ack——可能 ui/conversation 需要 requestId/字段不同，或设备屏幕未接时行为不同。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
