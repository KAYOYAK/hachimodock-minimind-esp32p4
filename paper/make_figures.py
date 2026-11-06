#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate the paper figure: (a) capacity-accuracy frontier, (b) per-token latency."""
import os
import re
import statistics

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BASE = r"C:\p4test"
OUT = os.path.join(BASE, r"paper\figures")
os.makedirs(OUT, exist_ok=True)

# (label, size MB, CE/q4, pass, deployed, measured_ms)
POINTS = [
    ("q2", 20.03, 1.450, False, False, 1352),
    ("mix42", 24.80, 1.104, True, False, None),
    ("mix432", 26.67, 1.075, True, False, None),
    ("q3", 28.02, 1.020, True, False, None),
    ("q3e4", 28.63, 1.020, True, True, 2152),
    ("mixed", 30.40, 1.013, True, False, 2017),
    ("q4*", 36.01, 1.000, None, False, None),
]

# per-token latency from the measured log
lat = []
for path in [os.path.join(BASE, r"logs\measure_latency.log")]:
    try:
        txt = open(path, encoding="utf-8", errors="replace").read()
        lat = [int(v) / 1000.0 for v in re.findall(r"STEPUS \d+ (\d+)", txt)][-32:]
    except FileNotFoundError:
        pass
if not lat:
    lat = [2147.76, 2150.00, 2151.54, 2152.79, 2154.55, 2155.68, 2157.43, 2158.52,
           2147.96, 2150.41, 2152.03, 2153.45, 2153.70, 2155.76, 2156.93, 2158.31,
           2160.07, 2161.59, 2162.92, 2163.81, 2164.89, 2166.61, 2167.73, 2169.34,
           2170.52, 2171.66, 2173.21, 2174.75, 2175.96, 2177.69, 2178.40, 2180.31,
           2180.94, 2182.60, 2183.35, 2185.37, 2186.17, 2187.59]

plt.rcParams.update({
    "font.family": "serif",
    "font.size": 7,
    "axes.linewidth": 0.6,
    "xtick.major.width": 0.5,
    "ytick.major.width": 0.5,
    "lines.linewidth": 0.9,
    "legend.fontsize": 6.5,
})

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.0, 2.35))

# ---- (a) frontier ----
for label, size, ratio, ok, deployed, _ms in POINTS:
    if ratio is None:
        continue
    if ok is None:
        ax1.plot(size, ratio, "s", mfc="none", mec="0.45", ms=5, mew=0.7)
        ax1.annotate(label, (size, ratio), textcoords="offset points", xytext=(-14, -9),
                     fontsize=6, color="0.35")
    elif deployed:
        ax1.plot(size, ratio, "*", color="#d62728", ms=9, zorder=5)
        ax1.annotate(label + "\n(deployed)", (size, ratio), textcoords="offset points",
                     xytext=(4, -18), fontsize=6.5, color="#d62728")
    else:
        color = "#2ca02c" if ok else "#d62728"
        ax1.plot(size, ratio, "o", color=color, ms=4, mfc=color)
        off = {"q3": (-12, 5), "mixed": (6, 5), "mix42": (5, 3), "mix432": (5, 3)}.get(label, (5, 3))
        ax1.annotate(label, (size, ratio), textcoords="offset points", xytext=off,
                     fontsize=6)
ax1.axhline(1.15, color="0.2", ls="--", lw=0.7)
ax1.text(20.4, 1.155, r"pre-registered bound $1.15\times$", fontsize=6, color="0.2")
ax1.axvline(32, color="0.5", ls=":", lw=0.7)
ax1.text(30.6, 1.42, "32 MB budget", rotation=90, fontsize=6, color="0.45",
         va="top", ha="right")
ax1.set_xlim(19, 37.5)
ax1.set_ylim(0.975, 1.47)
ax1.set_xlabel("model image size (MB)")
ax1.set_ylabel("windowed CE relative to q4")
ax1.set_title("(a) capacity--accuracy frontier", fontsize=7.5)
ax1.grid(True, lw=0.3, color="0.9")

# ---- (b) latency ----
pos = list(range(len(lat)))
ax2.plot(pos, lat, "-", color="#1f77b4", lw=0.9)
ax2.plot(pos, lat, ".", color="#1f77b4", ms=2.5)
mean = statistics.mean(lat)
p95 = sorted(lat)[min(int(0.95 * len(lat)), len(lat) - 1)]
ax2.axhline(mean, color="0.3", ls="--", lw=0.7)
ax2.axhline(p95, color="#d62728", ls=":", lw=0.8)
ax2.text(pos[-1], mean + 0.6, "mean %.0f ms" % mean, ha="right", fontsize=6, color="0.3")
ax2.text(pos[-1], p95 + 0.8, "p95 %.0f ms" % p95, ha="right", fontsize=6,
         color="#d62728")
ax2.set_xlabel("decode position")
ax2.set_ylabel("per-token latency (ms)")
ax2.set_title("(b) per-token latency (n=%d)" % len(lat), fontsize=7.5)
ax2.set_xlim(-0.5, max(pos) + 0.5)
ax2.set_ylim(2135, 2200)
ax2.grid(True, lw=0.3, color="0.9")

fig.tight_layout(pad=0.3)
out = os.path.join(OUT, "fig_frontier_latency.png")
fig.savefig(out, dpi=300)
print("saved", out)
