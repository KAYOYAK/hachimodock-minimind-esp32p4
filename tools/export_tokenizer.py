#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Export the MiniMind-3 tokenizer (Qwen2-like ByteLevel BPE) to a compact binary
that the ESP32-P4 firmware can load from TF card.

Binary layout (little endian):
  u32 magic 'MMTK'
  u32 version = 1
  u32 vocab_size V
  u32 n_merges M
  u32 n_special S
  u32 byte2id[256]        # byte -> vocab id (single-byte token)
  u32 byte2cp[256]        # byte -> unicode codepoint used by ByteLevel
  vocab:   V × (u32 len, bytes[utf8])
  merges:  M × (u32 a_id, u32 b_id, u32 merged_id)   # rank = index
  special: S × (u32 id, u32 len, bytes[utf8])        # literal special strings

Validation is done by tools/tokenizer_host_test.c against this file.
"""
import json
import os
import struct
import sys

TOK_DIR = r"C:\p4test\work\hf_minimind3_official"
OUT = r"C:\p4test\artifacts\tokenizer.bin"


def bytes_to_unicode():
    bs = (list(range(ord("!"), ord("~") + 1))
          + list(range(ord("¡"), ord("¬") + 1))
          + list(range(ord("®"), ord("ÿ") + 1)))
    cs = bs[:]
    n = 0
    for b in range(256):
        if b not in bs:
            bs.append(b)
            cs.append(256 + n)
            n += 1
    return dict(zip(bs, map(chr, cs)))


def main():
    tj = json.load(open(os.path.join(TOK_DIR, "tokenizer.json"), encoding="utf-8"))
    vocab = tj["model"]["vocab"]                     # token(str) -> id
    id2s = {i: s for s, i in vocab.items()}
    assert len(id2s) == len(vocab) == max(id2s) + 1, "vocab ids must be contiguous"
    V = len(id2s)

    merges = tj["model"]["merges"]
    mg = []
    for a, b in merges:
        merged = a + b
        if merged not in vocab:
            raise SystemExit(f"merge produces unknown token {merged!r}")
        mg.append((vocab[a], vocab[b], vocab[merged]))

    b2c = bytes_to_unicode()
    byte2id = []
    byte2cp = []
    for bidx in range(256):
        ch = b2c[bidx]
        tok = vocab.get(ch)
        if tok is None:
            raise SystemExit(f"missing single-byte token for byte {bidx} char {ch!r}")
        byte2id.append(tok)
        byte2cp.append(ord(ch))

    specials = []
    for a in tj.get("added_tokens") or []:
        specials.append((a["id"], a["content"]))
    # longest first helps the C matcher; C also sorts defensively
    specials.sort(key=lambda x: -len(x[1]))

    out = bytearray()
    out += b"MMTK"
    out += struct.pack("<IIII", 1, V, len(mg), len(specials))
    out += struct.pack("<256I", *byte2id)
    out += struct.pack("<256I", *byte2cp)
    for i in range(V):
        raw = id2s[i].encode("utf-8")
        out += struct.pack("<I", len(raw)) + raw
    for (a, b, m) in mg:
        out += struct.pack("<III", a, b, m)
    for (sid, content) in specials:
        raw = content.encode("utf-8")
        out += struct.pack("<II", sid, len(raw)) + raw

    with open(OUT, "wb") as f:
        f.write(out)

    print(f"tokenizer.bin: {len(out)} bytes")
    print(f"  vocab={V} merges={len(mg)} specials={len(specials)}")
    print(f"  specials sample: {specials[:5]}")
    print(f"  byte tokens: id[space]={byte2id[32]}, id[newline]={byte2id[10]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
