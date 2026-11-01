#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""convert_minimind.py - MiniMind-3 (HF Qwen3 format) -> KMCU v1 image.

KMCU v1 layout follows the Kestrel-MCU project
(https://github.com/m13253246268-ship-it/kestrel-llm-mcu, Apache-2.0), reused as
the MCU inference base. MiniMind-3 adds Qwen3 QK-norm, stored as
"L<i>.q_norm" / "L<i>.k_norm" f32 tensors (the patched kmcu.c applies them
before RoPE).

Weight dtypes (directory entry byte 24):
  1 = f32            raw little-endian float32 (norms)
  2 = q4_0           18 B / 32 weights: fp16 scale + 16 packed nibbles, w=(nib-8)*d
  4 = q3_0           14 B / 32 weights: fp16 scale + 12 B packed 3-bit, w=(q-4)*d
  5 = q2_0           10 B / 32 weights: fp16 scale +  8 B packed 2-bit, w=(q-2)*d
All quantized rows are padded to a multiple of 32 (zero tail), blocks never
cross a row.

Profiles (attention vs FFN bits can differ, the P4 PSRAM budget decides):
  q4      all quantized tensors q4_0                       (~34.3 MiB image)
  mixed   attn+embed q4_0, FFN q3_0                        (~23.7 MiB image)
  q3      all q3_0                                         (~28.0 MiB image)
  q2      all q2_0                                         (~20.0 MiB image)

Usage:
  python convert_minimind.py --src <hf_dir> --out <model.kmcu> [--profile q4]
"""
import argparse
import json
import os
import struct

import numpy as np

HEADER_BYTES = 128
DIR_ENTRY_BYTES = 48
ALIGN = 64
BLOCK = 32

DT_F32 = 1
DT_Q4 = 2
DT_Q3 = 4
DT_Q2 = 5

PAYLOAD = {DT_Q4: 18, DT_Q3: 14, DT_Q2: 10}


def _q_block_pack(q: np.ndarray, bits: int) -> bytes:
    """q: (..., 32) integer codes in [0, 2**bits). Returns packed bytes."""
    if bits == 4:
        return (q[..., 0::2] | (q[..., 1::2] << 4)).astype(np.uint8).tobytes()
    if bits == 3:
        q = q.astype(np.uint32)
        chunks = np.zeros(q.shape[:-1] + (12,), dtype=np.uint8)
        for c in range(4):
            v = (q[..., 8 * c + 0] | (q[..., 8 * c + 1] << 3) |
                 (q[..., 8 * c + 2] << 6) | (q[..., 8 * c + 3] << 9) |
                 (q[..., 8 * c + 4] << 12) | (q[..., 8 * c + 5] << 15) |
                 (q[..., 8 * c + 6] << 18) | (q[..., 8 * c + 7] << 21))
            chunks[..., 3 * c + 0] = (v & 0xFF).astype(np.uint8)
            chunks[..., 3 * c + 1] = ((v >> 8) & 0xFF).astype(np.uint8)
            chunks[..., 3 * c + 2] = ((v >> 16) & 0xFF).astype(np.uint8)
        return chunks.tobytes()
    if bits == 2:
        q = q.astype(np.uint8)
        return ((q[..., 0::4] | (q[..., 1::4] << 2) |
                 (q[..., 2::4] << 4) | (q[..., 3::4] << 6)).astype(np.uint8).tobytes())
    raise ValueError(bits)


def quantize_2d(w: np.ndarray, dtype: int) -> bytes:
    """Quantize a 2-D float array to the KMCU block format of ``dtype``."""
    if dtype == DT_F32:
        return np.asarray(w, dtype=np.float32).tobytes()
    bits = {DT_Q4: 4, DT_Q3: 3, DT_Q2: 2}[dtype]
    levels = {4: 8, 3: 4, 2: 2}[bits]
    w = np.asarray(w, dtype=np.float32)
    rows, cols = w.shape
    cols_p = (cols + BLOCK - 1) // BLOCK * BLOCK
    if cols_p != cols:
        w = np.pad(w, ((0, 0), (0, cols_p - cols)))
    blocks = w.reshape(rows, cols_p // BLOCK, BLOCK)
    amax = np.abs(blocks).max(axis=2).astype(np.float32)
    d = np.where(amax > 0.0, amax / float(levels), 1.0).astype(np.float32)
    q = np.clip(np.rint(blocks / d[:, :, None]), -levels, levels - 1).astype(np.int32)
    q = (q + levels).astype(np.uint8)
    scale = np.ascontiguousarray(d.astype(np.float16)).view(np.uint8).tobytes()
    packed = _q_block_pack(q, bits)
    nblk = rows * (cols_p // BLOCK)
    # interleave: per block [scale(2B) | packed(bits*4B)]
    total = nblk * PAYLOAD[dtype]
    out = np.empty(total, dtype=np.uint8)
    scales = np.frombuffer(scale, dtype=np.uint8).reshape(nblk, 2)
    body = np.frombuffer(packed, dtype=np.uint8).reshape(nblk, PAYLOAD[dtype] - 2)
    out = out.reshape(nblk, PAYLOAD[dtype])
    out[:, 0:2] = scales
    out[:, 2:] = body
    return out.tobytes()


def add(tensors, name, w, dtype):
    w = np.asarray(w, dtype=np.float32)
    if w.ndim == 1:
        rows, cols = 1, w.size
    else:
        rows, cols = w.shape
    tensors.append((name, rows, cols, dtype, quantize_2d(w, dtype)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--profile", default="q4",
                    choices=["q4", "mixed", "q3e4", "mix42", "mix432", "q3", "q2"])
    args = ap.parse_args()

    cfg = json.load(open(os.path.join(args.src, "config.json"), encoding="utf-8"))
    dim = int(cfg["hidden_size"])
    nl = int(cfg["num_hidden_layers"])
    nh = int(cfg["num_attention_heads"])
    nkv = int(cfg["num_key_value_heads"])
    hd = int(cfg.get("head_dim") or dim // nh)
    ffn = int(cfg["intermediate_size"])
    vocab = int(cfg["vocab_size"])
    max_seq = int(cfg.get("max_position_embeddings", 32768))
    rope_theta = float(cfg.get("rope_theta", 1000000.0))
    eps = float(cfg.get("rms_norm_eps", 1e-6))
    tied = 1 if cfg.get("tie_word_embeddings") else 0
    bos, eos = 1, 2
    ctx_cap = min(max_seq, 256)

    # dtype assignment per tensor role
    # emb: token embedding (tied output head, most quality-sensitive)
    # attn: q/k/v/o; gu: gate/up; down: down_proj
    PROFILES = {
        "q4":    dict(emb=DT_Q4, attn=DT_Q4, gu=DT_Q4, down=DT_Q4),
        "mixed": dict(emb=DT_Q4, attn=DT_Q4, gu=DT_Q3, down=DT_Q3),
        "q3e4":  dict(emb=DT_Q4, attn=DT_Q3, gu=DT_Q3, down=DT_Q3),
        "mix42": dict(emb=DT_Q4, attn=DT_Q4, gu=DT_Q2, down=DT_Q2),
        "mix432": dict(emb=DT_Q4, attn=DT_Q4, gu=DT_Q2, down=DT_Q3),
        "q3":    dict(emb=DT_Q3, attn=DT_Q3, gu=DT_Q3, down=DT_Q3),
        "q2":    dict(emb=DT_Q2, attn=DT_Q2, gu=DT_Q2, down=DT_Q2),
    }
    P = PROFILES[args.profile]
    W, E = P["attn"], P["gu"]
    EMB, DOWN = P["emb"], P["down"]

    from safetensors.numpy import load_file

    print(f"loading safetensors from {args.src} ... profile={args.profile}")
    sd = load_file(os.path.join(args.src, "model.safetensors"))
    print(f"tensors in source: {len(sd)}")

    tensors = []
    add(tensors, "tok_embed", sd["model.embed_tokens.weight"], EMB)
    for i in range(nl):
        p = f"model.layers.{i}."
        add(tensors, f"L{i}.in_ln", sd[p + "input_layernorm.weight"], DT_F32)
        add(tensors, f"L{i}.q", sd[p + "self_attn.q_proj.weight"], W)
        add(tensors, f"L{i}.k", sd[p + "self_attn.k_proj.weight"], W)
        add(tensors, f"L{i}.v", sd[p + "self_attn.v_proj.weight"], W)
        add(tensors, f"L{i}.o", sd[p + "self_attn.o_proj.weight"], W)
        add(tensors, f"L{i}.q_norm", sd[p + "self_attn.q_norm.weight"], DT_F32)
        add(tensors, f"L{i}.k_norm", sd[p + "self_attn.k_norm.weight"], DT_F32)
        add(tensors, f"L{i}.post_ln", sd[p + "post_attention_layernorm.weight"], DT_F32)
        add(tensors, f"L{i}.gate", sd[p + "mlp.gate_proj.weight"], E)
        add(tensors, f"L{i}.up", sd[p + "mlp.up_proj.weight"], E)
        add(tensors, f"L{i}.down", sd[p + "mlp.down_proj.weight"], DOWN)
    add(tensors, "final_norm", sd["model.norm.weight"], DT_F32)
    if not tied:
        add(tensors, "lm_head", sd["lm_head.weight"], EMB)

    n_tensors = len(tensors)
    dir_offset = HEADER_BYTES
    data_offset = (HEADER_BYTES + n_tensors * DIR_ENTRY_BYTES + ALIGN - 1) // ALIGN * ALIGN
    off = data_offset
    entries = []
    n_params = 0
    for (name, rows, cols, dtype, payload) in tensors:
        entries.append((name, rows, cols, dtype, off, len(payload)))
        off = (off + len(payload) + ALIGN - 1) // ALIGN * ALIGN
        n_params += rows * cols

    print(f"n_tensors={n_tensors} params={n_params/1e6:.2f}M")
    print(f"image size = {off/1024/1024:.2f} MiB  (profile={args.profile})")
    print(f"arch: dim={dim} nl={nl} nh={nh} nkv={nkv} hd={hd} ffn={ffn} "
          f"vocab={vocab} ctx={ctx_cap} theta={rope_theta} eps={eps}")

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "wb") as f:
        hdr = bytearray(HEADER_BYTES)
        hdr[0:4] = b"KMCU"
        struct.pack_into("<I", hdr, 4, 1)
        struct.pack_into("<I", hdr, 8, nl)
        struct.pack_into("<I", hdr, 12, dim)
        struct.pack_into("<I", hdr, 16, nh)
        struct.pack_into("<I", hdr, 20, nkv)
        struct.pack_into("<I", hdr, 24, hd)
        struct.pack_into("<I", hdr, 28, ffn)
        struct.pack_into("<I", hdr, 32, vocab)
        struct.pack_into("<I", hdr, 36, ctx_cap)
        struct.pack_into("<I", hdr, 40, bos)
        struct.pack_into("<I", hdr, 44, eos)
        struct.pack_into("<I", hdr, 48, tied)
        struct.pack_into("<I", hdr, 52, n_tensors)
        struct.pack_into("<I", hdr, 56, dir_offset)
        struct.pack_into("<I", hdr, 60, data_offset)
        struct.pack_into("<f", hdr, 64, rope_theta)
        struct.pack_into("<f", hdr, 68, eps)
        struct.pack_into("<I", hdr, 72, n_params)
        struct.pack_into("<I", hdr, 76, 0)
        struct.pack_into("<I", hdr, 80, 0)
        struct.pack_into("<I", hdr, 84, 0)
        struct.pack_into("<f", hdr, 88, 0.0)
        struct.pack_into("<I", hdr, 92, 0)
        f.write(bytes(hdr))

        for (name, rows, cols, dtype, offset, nb) in entries:
            e = bytearray(DIR_ENTRY_BYTES)
            raw = name.encode("ascii")[:24]
            e[0:len(raw)] = raw
            e[24] = dtype
            struct.pack_into("<I", e, 28, rows)
            struct.pack_into("<I", e, 32, cols)
            struct.pack_into("<I", e, 36, offset)
            struct.pack_into("<I", e, 40, nb)
            f.write(bytes(e))

        gap = data_offset - (HEADER_BYTES + n_tensors * DIR_ENTRY_BYTES)
        if gap > 0:
            f.write(b"\x00" * gap)
        cur = data_offset
        for (t, e) in zip(tensors, entries):
            payload = t[4]
            assert e[4] == cur, (t[0], e[4], cur)
            f.write(payload)
            cur += len(payload)
            pad = (ALIGN - (cur % ALIGN)) % ALIGN
            if pad:
                f.write(b"\x00" * pad)
                cur += pad

    manifest = os.path.splitext(args.out)[0] + ".manifest.txt"
    with open(manifest, "w", encoding="utf-8") as mf:
        mf.write(f"profile={args.profile} arch dim={dim} nl={nl} nh={nh} nkv={nkv} "
                 f"hd={hd} ffn={ffn} vocab={vocab} ctx={ctx_cap} theta={rope_theta} eps={eps}\n")
        mf.write(f"tied_embed={tied} n_tensors={n_tensors} data_offset={data_offset} "
                 f"file_size={off}\n")
        for (name, rows, cols, dtype, offset, nb) in entries:
            mf.write(f"{name:18s} dtype={dtype} shape=({rows},{cols}) off={offset} nb={nb}\n")
    print(f"written: {args.out}\nmanifest: {manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
