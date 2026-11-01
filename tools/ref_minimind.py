#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ref_minimind.py - NumPy fp32 reference for MiniMind-3 over a KMCU image.

The reference deliberately reuses the *same quantized weights* as the MCU kernel
(no float16 source weights), so the only expected difference against
firmware/main/kmcu.c is floating-point accumulation order plus the kernel's
int16 activation quantization in gemv_q8.

Checks performed:
  1. logits after the prompt: top-1 id and top-8 ids/values vs host_eval output.
  2. greedy continuation ids vs host_eval.
  3. (optional, if torch is importable) top-1 agreement vs the original
     float16 HF model to quantify q4 quantization damage.

Usage:
  python ref_minimind.py --km <model.kmcu> --host-out <host_eval_stdout.txt> \
                         [--hf <hf_dir>] [--out-json <path>]
"""
import argparse
import json
import struct

import numpy as np

HEADER_BYTES = 128
DIR_ENTRY_BYTES = 48
BLOCK = 32
Q4_BYTES = 18

PROMPT = [1, 832, 311, 234, 1968, 294, 2919, 2360, 441, 1153, 2, 234,
          1, 1388, 570, 811, 234, 25, 234, 234, 26, 234, 234]
GEN = 16


class KMCU:
    def __init__(self, path):
        self.buf = open(path, "rb").read()
        b = self.buf
        assert b[:4] == b"KMCU", "bad magic"
        (self.version, self.n_layers, self.dim, self.n_heads, self.n_kv_heads,
         self.head_dim, self.ffn_dim, self.vocab_size, self.max_seq,
         self.bos, self.eos, self.tied, self.n_tensors, self.dir_offset,
         self.data_offset) = struct.unpack_from("<15I", b, 4)
        self.rope_theta, self.norm_eps, self.total_params = struct.unpack_from("<ffI", b, 64)
        self.entries = {}
        for i in range(self.n_tensors):
            o = self.dir_offset + i * DIR_ENTRY_BYTES
            name = b[o:o + 24].split(b"\x00", 1)[0].decode("ascii")
            dtype = b[o + 24]
            rows, cols, off, nbytes = struct.unpack_from("<IIII", b, o + 28)
            self.entries[name] = (dtype, rows, cols, off, nbytes)

    def tensor(self, name):
        dtype, rows, cols, off, _ = self.entries[name]
        if dtype == 1:  # f32
            return np.frombuffer(self.buf, dtype="<f4", count=rows * cols, offset=off).reshape(rows, cols)
        nblk = (cols + 31) // 32
        if dtype == 2:  # q4_0: fp16 scale + 16 packed nibbles
            blocks = np.frombuffer(self.buf, dtype=np.uint8, count=rows * nblk * 18,
                                   offset=off).reshape(rows, nblk, 18)
            d = np.ascontiguousarray(blocks[:, :, 0:2]).view("<f2").astype(np.float32)[:, :, 0]
            nb = blocks[:, :, 2:18]
            packed = np.empty((rows, nblk, 32), dtype=np.int16)
            packed[:, :, 0::2] = nb & 0x0F
            packed[:, :, 1::2] = nb >> 4
            w = (packed.astype(np.float32) - 8.0) * d[:, :, None]
            return w.reshape(rows, nblk * 32)[:, :cols].astype(np.float32)
        if dtype == 4:  # q3_0: fp16 scale + 12 B packed 3-bit
            blocks = np.frombuffer(self.buf, dtype=np.uint8, count=rows * nblk * 14,
                                   offset=off).reshape(rows, nblk, 14)
            d = np.ascontiguousarray(blocks[:, :, 0:2]).view("<f2").astype(np.float32)[:, :, 0]
            chunks = blocks[:, :, 2:14].reshape(rows, nblk, 4, 3).astype(np.uint32)
            v = chunks[:, :, :, 0] | (chunks[:, :, :, 1] << 8) | (chunks[:, :, :, 2] << 16)
            packed = np.empty((rows, nblk, 32), dtype=np.int16)
            for c in range(4):
                for j in range(8):
                    packed[:, :, 8 * c + j] = (v[:, :, c] >> (3 * j)) & 7
            w = (packed.astype(np.float32) - 4.0) * d[:, :, None]
            return w.reshape(rows, nblk * 32)[:, :cols].astype(np.float32)
        if dtype == 5:  # q2_0: fp16 scale + 8 B packed 2-bit
            blocks = np.frombuffer(self.buf, dtype=np.uint8, count=rows * nblk * 10,
                                   offset=off).reshape(rows, nblk, 10)
            d = np.ascontiguousarray(blocks[:, :, 0:2]).view("<f2").astype(np.float32)[:, :, 0]
            nb = blocks[:, :, 2:10]
            packed = np.empty((rows, nblk, 32), dtype=np.int16)
            for j in range(4):
                packed[:, :, j::4] = (nb >> (2 * j)) & 3
            w = (packed.astype(np.float32) - 2.0) * d[:, :, None]
            return w.reshape(rows, nblk * 32)[:, :cols].astype(np.float32)
        raise ValueError(f"unsupported dtype {dtype} for {name}")


def rms_norm(x, w, eps):
    return (x / np.sqrt(np.mean(x * x) + eps)).astype(np.float32) * w


def rope(v, n_heads, hd, pos, theta):
    v = v.reshape(n_heads, hd).copy()
    half = hd // 2
    i = np.arange(half, dtype=np.float32)
    inv = theta ** (-2.0 * i / hd)
    ang = pos * inv
    c, s = np.cos(ang), np.sin(ang)
    a = v[:, :half].copy()
    b = v[:, half:].copy()
    v[:, :half] = a * c - b * s
    v[:, half:] = b * c + a * s
    return v.reshape(-1)


class Ref:
    def __init__(self, km):
        self.km = km
        self.emb = km.tensor("tok_embed")
        self.layers = []
        for i in range(km.n_layers):
            self.layers.append({
                "in_ln": km.tensor(f"L{i}.in_ln"),
                "q": km.tensor(f"L{i}.q"),
                "k": km.tensor(f"L{i}.k"),
                "v": km.tensor(f"L{i}.v"),
                "o": km.tensor(f"L{i}.o"),
                "q_norm": km.tensor(f"L{i}.q_norm").reshape(-1),
                "k_norm": km.tensor(f"L{i}.k_norm").reshape(-1),
                "post_ln": km.tensor(f"L{i}.post_ln"),
                "gate": km.tensor(f"L{i}.gate"),
                "up": km.tensor(f"L{i}.up"),
                "down": km.tensor(f"L{i}.down"),
            })
        self.final = km.tensor("final_norm").reshape(-1)

    def decode(self, token, pos, kc, vc):
        km = self.km
        dim, nh, nkv, hd = km.dim, km.n_heads, km.n_kv_heads, km.head_dim
        kvw = nkv * hd
        x = self.emb[token].astype(np.float32)
        for i, L in enumerate(self.layers):
            h = rms_norm(x, L["in_ln"].reshape(-1), km.norm_eps)
            q = L["q"].astype(np.float32) @ h
            k = L["k"].astype(np.float32) @ h
            v = L["v"].astype(np.float32) @ h
            # QK-norm (Qwen3): per-head RMSNorm before RoPE
            q = np.concatenate([rms_norm(q[j * hd:(j + 1) * hd], L["q_norm"], km.norm_eps)
                                for j in range(nh)])
            k = np.concatenate([rms_norm(k[j * hd:(j + 1) * hd], L["k_norm"], km.norm_eps)
                                for j in range(nkv)])
            q = rope(q, nh, hd, pos, km.rope_theta)
            k = rope(k, nkv, hd, pos, km.rope_theta)
            kc[i, pos] = k.reshape(nkv, hd)
            vc[i, pos] = v.reshape(nkv, hd)
            attn = np.zeros(dim, dtype=np.float32)
            scale = 1.0 / np.sqrt(hd)
            for hh in range(nh):
                kvh = hh // (nh // nkv)
                kh = kc[i, :pos + 1, kvh, :]          # (npos, hd)
                s = kh @ q[hh * hd:(hh + 1) * hd] * scale
                s = np.exp(s - s.max())
                s /= s.sum()
                attn[hh * hd:(hh + 1) * hd] = (s[:, None] * vc[i, :pos + 1, kvh, :]).sum(axis=0)
            x = x + L["o"].astype(np.float32) @ attn
            h2 = rms_norm(x, L["post_ln"].reshape(-1), km.norm_eps)
            g = L["gate"].astype(np.float32) @ h2
            u = L["up"].astype(np.float32) @ h2
            act = (g / (1.0 + np.exp(-g))) * u
            x = x + L["down"].astype(np.float32) @ act
        x = rms_norm(x, self.final, km.norm_eps)
        return self.emb.astype(np.float32) @ x


def topk(logits, k=8):
    idx = np.argsort(-logits)[:k]
    return [(int(i), float(logits[i])) for i in idx]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--km", required=True)
    ap.add_argument("--host-out", default=None)
    ap.add_argument("--hf", default=None)
    ap.add_argument("--tok", default=None)
    ap.add_argument("--out-json", default=None)
    args = ap.parse_args()

    km = KMCU(args.km)
    print(f"KMCU: dim={km.dim} nl={km.n_layers} nh={km.n_heads} nkv={km.n_kv_heads} "
          f"hd={km.head_dim} ffn={km.ffn_dim} vocab={km.vocab_size} ctx={km.max_seq}")
    ref = Ref(km)
    kc = np.zeros((km.n_layers, km.max_seq, km.n_kv_heads, km.head_dim), dtype=np.float32)
    vc = np.zeros_like(kc)

    logits = None
    pos = 0
    for t in PROMPT:
        logits = ref.decode(t, pos, kc, vc)
        pos += 1
    ref_top = topk(logits, 8)
    seq = list(PROMPT)
    for _ in range(GEN):
        nxt = int(np.argmax(logits))
        seq.append(nxt)
        logits = ref.decode(nxt, pos, kc, vc)
        pos += 1
    generated = seq[len(PROMPT):]

    print("REF_TOP8 " + " ".join(f"{i}:{v:.6f}" for i, v in ref_top))
    print("REF_SEQ " + " ".join(str(x) for x in seq))

    if args.tok:
        try:
            from transformers import AutoTokenizer
            tok = AutoTokenizer.from_pretrained(args.tok)
            print("REF_TEXT " + repr(tok.decode(seq[len(PROMPT):])))
        except Exception as exc:  # noqa: BLE001 - decode is diagnostic only
            print(f"tokenizer decode skipped: {exc}")

    # ---- parse host_eval output (optional) ----
    host_top, host_seq = None, None
    if args.host_out:
        for line in open(args.host_out, encoding="utf-8", errors="replace"):
            line = line.strip()
            if line.startswith("TOP8"):
                parts = line.split()[1:]
                host_top = []
                for p in parts:
                    i, v = p.split(":")
                    host_top.append((int(i), float(v)))
            elif line.startswith("SEQ"):
                host_seq = [int(x) for x in line.split()[1:]]

    result = {"km": args.km, "ref_top8": ref_top, "ref_seq": seq}
    if host_top:
        ids_match = all(a[0] == b[0] for a, b in zip(ref_top, host_top))
        vmax = max(abs(a[1] - b[1]) for a, b in zip(ref_top, host_top))
        vmean = float(np.mean([abs(a[1] - b[1]) for a, b in zip(ref_top, host_top)]))
        gen_match = host_seq is not None and host_seq[:len(seq)] == seq
        result.update({"host_top8": host_top, "top8_ids_match": bool(ids_match),
                       "top8_max_absdiff": float(vmax), "top8_mean_absdiff": vmean,
                       "greedy_seq_match": bool(gen_match), "host_seq": host_seq})
        print(f"COMPARE top8_ids_match={ids_match} max_absdiff={vmax:.5f} "
              f"mean_absdiff={vmean:.5f} greedy_seq_match={gen_match}")
        if not ids_match or not gen_match:
            print("REF_TOP8 ", [(i, round(v, 4)) for i, v in ref_top])
            print("HOST_TOP8", host_top)
            print("REF_SEQ ", seq)
            print("HOST_SEQ", host_seq)

    # ---- optional: quantization damage vs original HF float model ----
    if args.hf:
        try:
            import torch
            from transformers import AutoModelForCausalLM
            m = AutoModelForCausalLM.from_pretrained(args.hf, dtype=torch.float32).eval()
            with torch.no_grad():
                ids = torch.tensor([PROMPT])
                out = m(ids).logits[0, -1].float().numpy()
            hf_top = topk(out, 8)
            top1_match = hf_top[0][0] == ref_top[0][0]
            rank_agree = len(set(i for i, _ in hf_top) & set(i for i, _ in ref_top))
            result.update({"hf_top8": hf_top, "hf_top1_match": bool(top1_match),
                           "hf_top8_overlap": rank_agree})
            print(f"HF_Q4_DAMAGE top1_match={top1_match} top8_overlap={rank_agree}/8 "
                  f"hf_top1={hf_top[0]} ref_top1={ref_top[0]}")
        except Exception as exc:  # noqa: BLE001 - optional diagnostic only
            print(f"HF compare skipped: {exc}")

    if args.out_json:
        with open(args.out_json, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print("wrote", args.out_json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
