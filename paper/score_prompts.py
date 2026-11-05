#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Deterministic rule-based scorer for the 30-prompt evaluation (IEEE ESL plan).

Input: JSONL, one object per line: {"id": 1, "prompt": "...", "response": "..."}
Output: per-prompt pass/fail with reasons + aggregate pass rate.

Rules (pre-declared, do not tune after seeing results):
  R1 non-empty, 8 <= len(response) <= 400 characters
  R2 repetition: fraction of repeated character trigrams <= 10%
  R3 complete ending: last char in  。！？!?…；;：:」』”")  or a digit/letter
  R4 no prompt echo: prompt not contained verbatim in response
  R5 no control characters except newline/tab
A response passes if all five rules pass. Aggregate pass rate = passed / total.
"""
import json
import re
import sys
import argparse

END_OK = set("。！？!?…；;：:」』”\")》】")
CTRL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def trigram_repeat_ratio(s: str) -> float:
    s = re.sub(r"\s+", "", s)
    if len(s) < 6:
        return 0.0
    grams = [s[i:i + 3] for i in range(len(s) - 2)]
    total = len(grams)
    if total == 0:
        return 0.0
    repeated = total - len(set(grams))
    return repeated / total


def score_one(prompt: str, response: str) -> tuple:
    reasons = []
    text = response.strip()
    if not (8 <= len(text) <= 400):
        reasons.append("R1_length")
    if trigram_repeat_ratio(text) > 0.10:
        reasons.append("R2_repetition")
    if text and text[-1] not in END_OK and not text[-1].isalnum():
        reasons.append("R3_ending")
    if prompt and prompt in text:
        reasons.append("R4_prompt_echo")
    if CTRL.search(text):
        reasons.append("R5_control")
    return (len(reasons) == 0, reasons, round(trigram_repeat_ratio(text), 3))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--json-out", default=None)
    args = ap.parse_args()

    rows = []
    with open(args.input, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))

    passed = 0
    results = []
    for r in rows:
        ok, reasons, rep = score_one(r.get("prompt", ""), r.get("response", ""))
        passed += 1 if ok else 0
        results.append({
            "id": r.get("id"), "prompt": r.get("prompt", ""),
            "pass": ok, "reasons": reasons, "repetition": rep,
            "len": len(r.get("response", "")),
        })
        print(f"[{'PASS' if ok else 'FAIL'}] id={r.get('id')} rep={rep:.3f} "
              f"len={len(r.get('response', ''))} {','.join(reasons)}")

    rate = passed / len(rows) if rows else 0.0
    print(f"\nTOTAL {len(rows)}  PASS {passed}  RATE {rate:.1%}")
    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as f:
            json.dump({"pass_rate": rate, "passed": passed, "total": len(rows),
                       "results": results}, f, ensure_ascii=False, indent=2)
        print(f"saved {args.json_out}")


if __name__ == "__main__":
    main()
