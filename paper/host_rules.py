#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Host-side 30-prompt rule-score evaluation with the same KMCU quantization
recipe as the device. Produces responses_<profile>.jsonl and a rule score table.

Greedy decoding: 32 new tokens, stop at EOS; if the budget is exhausted, append
an ellipsis so that the response is a complete UTF-8 string (the device firmware
does the same after the 2026-11-06 fix).
"""
import argparse
import json
import os
import re

import numpy as np
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

BLOCK = 32
LEVELS = {4: 8, 3: 4, 2: 2}
PROFILES = {
    "fp32": None,
    "q4": dict(emb=4, attn=4, gu=4, down=4),
    "q3e4": dict(emb=4, attn=3, gu=3, down=3),
    "q3": dict(emb=3, attn=3, gu=3, down=3),
    "mixed": dict(emb=4, attn=4, gu=3, down=3),
    "mix42": dict(emb=4, attn=4, gu=2, down=2),
    "mix432": dict(emb=4, attn=4, gu=2, down=3),
    "q2": dict(emb=2, attn=2, gu=2, down=2),
}
END_OK = set("。！？!?…；;：:」』”\")》】")
CTRL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def trigram_repeat_ratio(s: str) -> float:
    s = re.sub(r"\s+", "", s)
    if len(s) < 6:
        return 0.0
    grams = [s[i:i + 3] for i in range(len(s) - 2)]
    total = len(grams)
    return (total - len(set(grams))) / total if total else 0.0


def quantize_2d(w, bits):
    rows, cols = w.shape
    cols_p = (cols + BLOCK - 1) // BLOCK * BLOCK
    if cols_p != cols:
        w = np.pad(w, ((0, 0), (0, cols_p - cols)))
    blocks = w.reshape(rows, cols_p // BLOCK, BLOCK).astype(np.float32)
    amax = np.abs(blocks).max(axis=2)
    d = np.where(amax > 0.0, amax / float(LEVELS[bits]), 1.0).astype(np.float32)
    d = d.astype(np.float16).astype(np.float32)
    q = np.clip(np.rint(blocks / d[:, :, None]), -LEVELS[bits], LEVELS[bits] - 1)
    deq = (q * d[:, :, None]).astype(np.float32)
    return deq.reshape(rows, cols_p)[:, :cols]


def role_of(key):
    if key.endswith("embed_tokens.weight") or key.endswith("lm_head.weight"):
        return "emb"
    if any(s in key for s in ("q_proj", "k_proj", "v_proj", "o_proj")):
        return "attn"
    if any(s in key for s in ("gate_proj", "up_proj")):
        return "gu"
    if "down_proj" in key:
        return "down"
    return None


def score(prompt, response):
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
    ap.add_argument("--model", default=r"C:\p4test\work\hf_minimind3_selftrained")
    ap.add_argument("--prompts", default=r"C:\p4test\paper\eval_prompts.json")
    ap.add_argument("--outdir", default=r"C:\p4test\paper\measurements")
    ap.add_argument("--max-new", type=int, default=32)
    args = ap.parse_args()
    os.makedirs(args.outdir, exist_ok=True)
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    print("device:", dev)

    tok = AutoTokenizer.from_pretrained(args.model)
    eos = tok.eos_token_id
    prompts = json.load(open(args.prompts, encoding="utf-8"))
    pre = "<|im_start|>user\n"
    post = "<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n"

    base = AutoModelForCausalLM.from_pretrained(args.model, dtype=torch.float32)
    results = {}
    for prof_name, prof in PROFILES.items():
        model = AutoModelForCausalLM.from_pretrained(args.model, dtype=torch.float32)
        if prof is not None:
            with torch.no_grad():
                for name, p in model.named_parameters():
                    role = role_of(name)
                    if role is None or p.dim() != 2:
                        continue
                    w = p.detach().cpu().numpy().astype(np.float32)
                    p.copy_(torch.from_numpy(quantize_2d(w, prof[role])))
        model.eval().to(dev)
        rows = []
        passed = 0
        for item in prompts:
            ids = tok(pre + item["prompt"] + post, return_tensors="pt").input_ids.to(dev)
            gen = []
            with torch.no_grad():
                for _ in range(args.max_new):
                    logits = model(ids).logits[0, -1]
                    nxt = int(torch.argmax(logits).item())
                    if nxt == eos:
                        break
                    gen.append(nxt)
                    ids = torch.cat([ids, torch.tensor([[nxt]], device=dev)], dim=1)
            text = tok.decode(gen, skip_special_tokens=True, errors="ignore")
            truncated = len(gen) >= args.max_new
            if truncated:
                text = text.rstrip()
                if not text:
                    text = "……"
                elif text[-1] not in END_OK:
                    text += "……"
            ok, reasons, rep = score(item["prompt"], text)
            passed += 1 if ok else 0
            rows.append({"id": item["id"], "prompt": item["prompt"], "response": text,
                         "pass": ok, "reasons": reasons, "repetition": rep,
                         "len": len(text), "truncated": truncated})
        rate = passed / len(rows)
        results[prof_name] = {"pass_rate": rate, "passed": passed, "total": len(rows), "rows": rows}
        print(f"[{prof_name}] rule score {passed}/{len(rows)} = {rate:.1%}")
        with open(os.path.join(args.outdir, f"responses_host_{prof_name}.jsonl"), "w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps({"id": r["id"], "prompt": r["prompt"],
                                    "response": r["response"]}, ensure_ascii=False) + "\n")
        del model

    with open(os.path.join(args.outdir, "rules_host.json"), "w", encoding="utf-8") as f:
        json.dump({k: {kk: vv for kk, vv in v.items() if kk != "rows"} for k, v in results.items()},
                  f, ensure_ascii=False, indent=1)
    print("saved", os.path.join(args.outdir, "rules_host.json"))


if __name__ == "__main__":
    main()
