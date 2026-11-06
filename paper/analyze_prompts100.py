#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Analyse the 100-prompt run: rule pass rates with Wilson CIs and simple
task-level checks (math numeric answers, code keywords, translation keywords)."""
import json
import os
import re
import sys

import math

BASE = r"C:\p4test"
PROMPT_DIR = os.path.join(BASE, r"paper\measurements\prompts100")
PROMPTS = json.load(open(os.path.join(BASE, r"paper\eval_prompts_100.json"), encoding="utf-8"))
by_id = {p["id"]: p for p in PROMPTS}

sys.path.insert(0, os.path.join(BASE, r"paper"))
from host_rules import score  # noqa: E402

MATH = {
    31: ["70"], 32: ["40"], 33: ["1024"], 34: ["14"], 35: ["12"],
    36: ["9"], 37: ["23"], 38: ["28.2", "28.3", "28", "9π", "9π"], 39: ["3/4", "0.75"], 40: ["6"],
}
CODE = {
    41: ["def", "return"], 42: ["def", "return"], 43: ["list", "tuple", "元组", "列表"],
    44: ["def", "return"], 45: ["void", "swap", "int"], 46: ["递归", "自己"],
    47: ["def", "return"], 48: ["try", "except"], 49: ["open", "read", "行"],
    50: ["复杂度", "o("],
}
TRANS = {
    51: ["weather"], 52: ["machine learning", "learning"], 53: ["file", "desktop", "save"],
    54: ["algorithm", "linear", "complexity"], 55: ["computer"], 56: ["time"],
    57: ["model", "phone"], 58: ["wait", "moment"], 59: ["practice", "programming"],
    60: ["meeting", "tomorrow"],
}


def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    den = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (max(0.0, centre - half), min(1.0, centre + half))


def check_task(kind, pid, resp):
    if kind == "math":
        keys = MATH.get(pid)
    elif kind == "code":
        keys = CODE.get(pid)
    elif kind == "translate":
        keys = TRANS.get(pid)
    else:
        return None
    if not keys:
        return None
    t = resp.lower()
    return any(k.lower() in t for k in keys)


def main():
    profiles = ["fp32", "q4", "q3e4", "q3", "mixed", "mix42", "mix432", "q2"]
    lines = ["profile,rule_pass,rule_total,rule_rate,wilson_lo,wilson_hi,math_pass,math_n,code_pass,code_n,trans_pass,trans_n"]
    for prof in profiles:
        path = os.path.join(PROMPT_DIR, rf"responses_host_{prof}.jsonl")
        if not os.path.exists(path):
            continue
        rows = [json.loads(l) for l in open(path, encoding="utf-8")]
        passed = 0
        for r in rows:
            ok, _, _ = score(r["prompt"], r["response"])
            r["_ok"] = ok
            passed += 1 if ok else 0
        n = len(rows)
        lo, hi = wilson(passed, n)
        stats = {}
        for kind, mapping, expected in (("math", MATH, 10), ("code", CODE, 10), ("translate", TRANS, 10)):
            ids = set(mapping)
            sub = [r for r in rows if r["id"] in ids]
            ok = sum(1 for r in sub if check_task(kind, r["id"], r["response"]))
            stats[kind] = (ok, len(sub))
        lines.append(f"{prof},{passed},{n},{passed/n:.3f},{lo:.3f},{hi:.3f},"
                     f"{stats['math'][0]},{stats['math'][1]},{stats['code'][0]},{stats['code'][1]},"
                     f"{stats['translate'][0]},{stats['translate'][1]}")
        print(f"{prof}: rule {passed}/{n} ({passed/n:.1%}, 95% CI {lo:.1%}-{hi:.1%}); "
              f"math {stats['math'][0]}/10; code {stats['code'][0]}/10; trans {stats['translate'][0]}/10")
    out = os.path.join(PROMPT_DIR, "analysis_100.csv")
    open(out, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print("saved", out)


if __name__ == "__main__":
    main()
