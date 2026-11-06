#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Host-side quantization-error simulation for the ESL paper.

Loads the HF Qwen3-format MiniMind model, applies the SAME per-block (block=32)
quantization recipe used by tools/convert_minimind.py (q4_0/q3_0/q2_0, fp16 block
scales, round-to-nearest with absmax), keeps norms/biases in fp32, then computes
per-token cross-entropy on the fixed held-out token sequence.

Profiles: q4, q3e4, q2 (KMCU roles: emb/attn/gu/down).
Output: measurements/ce_host.csv and measurements/ce_host.json
"""
import argparse
import json
import os

import numpy as np
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

BLOCK = 32
LEVELS = {4: 8, 3: 4, 2: 2}


def quantize_2d(w: np.ndarray, bits: int) -> np.ndarray:
    """KMCU q*_0 recipe: per-block absmax scale (stored fp16), symmetric-ish."""
    rows, cols = w.shape
    cols_p = (cols + BLOCK - 1) // BLOCK * BLOCK
    if cols_p != cols:
        w = np.pad(w, ((0, 0), (0, cols_p - cols)))
    blocks = w.reshape(rows, cols_p // BLOCK, BLOCK).astype(np.float32)
    amax = np.abs(blocks).max(axis=2)
    d = np.where(amax > 0.0, amax / float(LEVELS[bits]), 1.0).astype(np.float32)
    d = d.astype(np.float16).astype(np.float32)  # fp16 scale, as stored
    q = np.clip(np.rint(blocks / d[:, :, None]), -LEVELS[bits], LEVELS[bits] - 1)
    deq = (q * d[:, :, None]).astype(np.float32)
    return deq.reshape(rows, cols_p)[:, :cols]


def role_of(key: str):
    if key.endswith("embed_tokens.weight") or key.endswith("lm_head.weight"):
        return "emb"
    if any(s in key for s in ("q_proj", "k_proj", "v_proj", "o_proj")):
        return "attn"
    if any(s in key for s in ("gate_proj", "up_proj")):
        return "gu"
    if "down_proj" in key:
        return "down"
    return None


PROFILES = {
    "q4":    dict(emb=4, attn=4, gu=4, down=4),
    "q3e4":  dict(emb=4, attn=3, gu=3, down=3),
    "q2":    dict(emb=2, attn=2, gu=2, down=2),
    "q3":    dict(emb=3, attn=3, gu=3, down=3),
    "mixed": dict(emb=4, attn=4, gu=3, down=3),
    "mix42": dict(emb=4, attn=4, gu=2, down=2),
    "mix432": dict(emb=4, attn=4, gu=2, down=3),
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=r"C:\p4test\work\hf_minimind3_official")
    ap.add_argument("--ids", default=r"C:\p4test\paper\heldout_ids.json")
    ap.add_argument("--outdir", default=r"C:\p4test\paper\measurements")
    ap.add_argument("--window", type=int, default=96)
    args = ap.parse_args()
    os.makedirs(args.outdir, exist_ok=True)

    meta = json.load(open(args.ids, encoding="utf-8"))
    ids = meta.get("windows_3") or meta["windows_2"]
    tok = AutoTokenizer.from_pretrained(args.model)
    print("text:", tok.decode(ids[:16]), "...")
    print("tokens:", len(ids), "windows:", len(ids) // args.window)

    base = AutoModelForCausalLM.from_pretrained(
        args.model, dtype=torch.float32
    )
    base.eval()

    rows = []
    for prof_name, prof in [("fp32", None)] + list(PROFILES.items()):
        model = AutoModelForCausalLM.from_pretrained(
            args.model, dtype=torch.float32
        )
        model.eval()
        if prof is not None:
            with torch.no_grad():
                for name, p in model.named_parameters():
                    role = role_of(name)
                    if role is None or p.dim() != 2:
                        continue
                    w = p.detach().cpu().numpy().astype(np.float32)
                    p.copy_(torch.from_numpy(quantize_2d(w, prof[role])))
            print(f"[{prof_name}] quantized weights applied")
        # windowed evaluation: each window is scored independently, exactly like
        # the on-device 96-token context (KV resets at every window boundary).
        ce_all = []
        win_ce = []
        with torch.no_grad():
            for start in range(0, len(ids) - 1, args.window):
                seg = ids[start:min(start + args.window, len(ids))]
                if len(seg) < 2:
                    break
                logits = model(torch.tensor([seg], dtype=torch.long)).logits[0].float()
                logp = torch.log_softmax(logits[:-1], dim=-1)
                tgt = torch.tensor(seg[1:], dtype=torch.long)
                ce = -logp[torch.arange(len(tgt)), tgt].numpy()
                ce_all.append(ce)
                win_ce.append(float(ce.mean()))
        ce_tok = np.concatenate(ce_all)
        mean_ce = float(ce_tok.mean())
        rows.append(dict(profile=prof_name, ce=mean_ce, ppl=float(np.exp(mean_ce)),
                         windows=win_ce, tokens=len(ce_tok)))
        print(f"[{prof_name}] CE={mean_ce:.4f}  PPL={np.exp(mean_ce):.2f}  windows={['%.4f' % w for w in win_ce]}")
        del model

    with open(os.path.join(args.outdir, "ce_host.csv"), "w", encoding="utf-8") as f:
        f.write("profile,ce,ppl,tokens,windows\n")
        for r in rows:
            f.write(f"{r['profile']},{r['ce']:.6f},{r['ppl']:.4f},{r['tokens']},\"{r['windows']}\"\n")
    with open(os.path.join(args.outdir, "ce_host.json"), "w", encoding="utf-8") as f:
        json.dump({"text": "paper/heldout_text.txt", "ids_file": "paper/heldout_ids.json",
                   "tokens": len(ids), "window": args.window, "results": rows},
                  f, ensure_ascii=False, indent=1)
    print("saved", os.path.join(args.outdir, "ce_host.csv"))


if __name__ == "__main__":
    main()
