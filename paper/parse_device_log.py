#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Parse measurement-firmware serial logs.

Extracts:
  - bench lines (ms/token, r, weight_MBps)
  - CE window lines (ce, ppl)
  - 30-prompt RULE blocks -> responses JSONL
Then computes the pre-registered rule score (same rules as score_prompts.py).

Usage:
  python paper/parse_device_log.py --log logs/q3e4_rules.log --model q3e4 \
      --outdir paper/measurements
"""
import argparse
import json
import os
import re

END_OK = set("。！？!?…；;：:」』”\")》】")
CTRL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def trigram_repeat_ratio(s: str) -> float:
    s = re.sub(r"\s+", "", s)
    if len(s) < 6:
        return 0.0
    grams = [s[i:i + 3] for i in range(len(s) - 2)]
    total = len(grams)
    return (total - len(set(grams))) / total if total else 0.0


def score(prompt: str, response: str):
    reasons = []
    t = response.strip()
    if not (8 <= len(t) <= 400):
        reasons.append("R1_length")
    if trigram_repeat_ratio(t) > 0.10:
        reasons.append("R2_repetition")
    if t and t[-1] not in END_OK and not t[-1].isalnum():
        reasons.append("R3_ending")
    if prompt and prompt in t:
        reasons.append("R4_prompt_echo")
    if CTRL.search(t):
        reasons.append("R5_control")
    return (not reasons, reasons, round(trigram_repeat_ratio(t), 3))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--outdir", default=r"C:\p4test\paper\measurements")
    args = ap.parse_args()
    os.makedirs(args.outdir, exist_ok=True)

    text = open(args.log, encoding="utf-8", errors="replace").read()
    out = {"model": args.model, "bench": [], "ce": [], "rules": {}}

    for ln in text.splitlines():
        if "bench:" in ln:
            m = re.search(r"([\d.]+) ms/token", ln)
            r = re.search(r"r=([\d.]+)", ln)
            mb = re.search(r"weight_MBps=([\d.]+)", ln)
            out["bench"].append({"ms_per_token": float(m.group(1)) if m else None,
                                 "r": float(r.group(1)) if r else None,
                                 "weight_MBps": float(mb.group(1)) if mb else None})
        if ln.startswith("CE win="):
            m = re.search(r"win=(\d+) tokens=(\d+) ce=([\d.]+) ppl=([\d.]+)", ln)
            if m:
                out["ce"].append({"window": int(m.group(1)), "tokens": int(m.group(2)),
                                  "ce": float(m.group(3)), "ppl": float(m.group(4))})
        if ln.startswith("CE mean"):
            m = re.search(r"ce=([\d.]+) ppl=([\d.]+) tokens=(\d+)", ln)
            if m:
                out["ce_mean"] = {"ce": float(m.group(1)), "ppl": float(m.group(2)),
                                  "tokens": int(m.group(3))}

    blocks = re.findall(r"RULE_BEGIN (\d+)\nPROMPT: (.*?)\nRESP: (.*?)\nRULE_END", text, re.S)
    rows = []
    passed = 0
    for idx, prompt, resp in blocks:
        ok, reasons, rep = score(prompt, resp)
        passed += 1 if ok else 0
        rows.append({"id": int(idx), "prompt": prompt, "response": resp.strip(),
                     "pass": ok, "reasons": reasons, "repetition": rep,
                     "len": len(resp.strip())})
    if rows:
        out["rules"] = {"total": len(rows), "passed": passed,
                        "pass_rate": passed / len(rows), "rows": rows}
        with open(os.path.join(args.outdir, f"responses_{args.model}.jsonl"), "w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps({"id": r["id"], "prompt": r["prompt"],
                                    "response": r["response"]}, ensure_ascii=False) + "\n")

    path = os.path.join(args.outdir, f"summary_{args.model}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(json.dumps({k: v for k, v in out.items() if k != "rules"}, ensure_ascii=False, indent=1))
    if out["rules"]:
        print("rules:", out["rules"]["passed"], "/", out["rules"]["total"],
              f"({out['rules']['pass_rate']:.1%})")
    print("saved", path)


if __name__ == "__main__":
    main()
