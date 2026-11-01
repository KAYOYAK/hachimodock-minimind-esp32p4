#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate tokenizer test cases, run the C tokenizer host test, compare with HF."""
import json
import os
import random
import subprocess
import sys

TOK_DIR = r"C:\p4test\work\hf_minimind3_official"
BIN = r"C:\p4test\artifacts\tokenizer.bin"
EXE = r"C:\p4test\work\tokenizer_host_test.exe"
CASES = r"C:\p4test\work\tokenizer_cases.hex"


def corpus():
    base = [
        "你好，介绍一下你自己", "你好", "解释什么是机器学习", "推荐一道中国的家常菜",
        "1+1 等于几？", "请用 Python 写一个计算斐波那契数列的函数",
        "Hello, world!", "The quick brown fox jumps over the lazy dog.",
        "I've been told he's there, 'RE you sure? 'M not sure I'll make it.",
        "  leading spaces", "trailing spaces   ", "line1\nline2\r\nline3",
        "a\n\nb", "数字 12345 和 3.14 以及 100%", "我们 123abc 混合 text 测试",
        "emoji 😀🚀 测试", "code: def f(x):\n    return x+1",
        "<|im_start|>user\n你好<|im_end|>", "中文English混合中文",
        "、。！？；：（）《》【】“”‘’", "café naïve résumé", "Привет мир",
        "こんにちは世界", "안녕하세요", "  \n\t  ", "", "a   b", "a \n b",
        "word\n", "\nword", "123abc456", "abc123", "3.14159", "-42", "e=mc^2",
        "``code`` **bold**", "a\r\n\r\nb", " \n ", "\t\tx", "x\t\ty",
        "混合123中文", "！？", "😀😀😀", "hello world\nsecond line",
        "<|im_start|>user\n推荐一道中国的家常菜<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n",
        "写一个冒泡排序的 Python 函数，并解释时间复杂度。",
        "What is machine learning? Explain in simple terms.",
        "把这句话翻译成英文：今天天气很好。",
        "  多个   空格   和\t制表符\t测试  ",
    ]
    # a few deterministic random mixes
    rng = random.Random(1337)
    zh = "你好世界机器学习人工智能模型推理部署开发板嵌入式芯片内存速度"
    en = "the quick brown fox jumps over lazy dog hello world mini mind"
    for _ in range(30):
        k = rng.randint(1, 12)
        parts = []
        for _ in range(k):
            r = rng.random()
            if r < 0.45:
                i = rng.randrange(0, len(zh) - rng.randint(1, 4))
                parts.append(zh[i:i + rng.randint(1, 4)])
            elif r < 0.8:
                w = en.split()
                j = rng.randrange(len(w))
                parts.append(w[j])
            else:
                parts.append(rng.choice(["，", "。", "！", "？", "：", " ", "\n", "\t", "123", "3.14", "😀"]))
        base.append("".join(parts))
    return base


def main():
    sys.path.insert(0, r"C:\p4test\vendor\py")
    from tokenizers import Tokenizer
    hf = Tokenizer.from_file(os.path.join(TOK_DIR, "tokenizer.json"))
    texts = corpus()
    refs = [hf.encode(t, add_special_tokens=False).ids for t in texts]

    with open(CASES, "w", encoding="ascii") as f:
        for t in texts:
            f.write(t.encode("utf-8").hex() + "\n")

    r = subprocess.run([EXE, BIN, CASES], capture_output=True, text=True)
    if r.returncode != 0:
        print("C tokenizer failed:", r.returncode, r.stderr)
        return 1
    lines = r.stdout.splitlines()
    bad = 0
    di = 0
    for idx, t in enumerate(texts):
        enc = lines[di].split()
        dec = lines[di + 1].split()
        di += 2
        if not enc or enc[0] != "E":
            print("bad output", idx)
            return 1
        got_ids = [int(x) for x in enc[1:]]
        ok_enc = got_ids == refs[idx]
        got_hex = dec[1] if len(dec) > 1 else ""
        ok_dec = len(dec) >= 1 and dec[0] == "D" and got_hex == t.encode("utf-8").hex()
        if not (ok_enc and ok_dec):
            bad += 1
            if bad <= 8:
                print("MISMATCH:", repr(t))
                print("  hf  ids:", refs[idx])
                print("  our ids:", got_ids)
                if not ok_dec:
                    print("  decode  :", got_hex)
                    print("  expected:", t.encode("utf-8").hex())
    print(f"{len(texts)-bad}/{len(texts)} tokenizer cases match (encode ids + decode bytes)")
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
