import sys
SRC = r"D:\AI\tools\llama-src\llama.cpp-b11270"
sys.path[:0] = [SRC, SRC + r"\gguf-py"]
import gguf, numpy as np
for path in [r"C:\p4test\artifacts\minimind-3-Q2_K.gguf", r"C:\p4test\artifacts\minimind-3-f16.gguf"]:
    r = gguf.GGUFReader(path)
    print("===", path, "===")
    arch = r.get_field("general.architecture")
    print("arch:", bytes(arch.parts[-1]).decode() if arch else None)
    for k in ["qwen3.block_count","qwen3.embedding_length","qwen3.feed_forward_length","qwen3.attention.head_count","qwen3.attention.head_count_kv","qwen3.rope.freq_base","qwen3.attention.layer_norm_rms_epsilon","qwen3.context_length"]:
        f = r.get_field(k)
        if f: print(k, f.parts[-1].tolist() if hasattr(f.parts[-1],'tolist') else f.parts[-1])
    tot = 0; by_type = {}
    for t in r.tensors:
        ts = int(np.prod(t.shape))
        tot += ts
        tt = str(t.tensor_type.name)
        by_type.setdefault(tt, [0,0])
        by_type[tt][0] += 1; by_type[tt][1] += ts
    print("tensor count:", len(r.tensors), "params:", tot/1e6, "M")
    for tt,(c,n) in sorted(by_type.items(), key=lambda kv:-kv[1][1]):
        print(f"  {tt:12s} tensors={c:3d} params={n/1e6:8.3f}M")
    # specific important tensors
    for name in ["token_embd.weight","output.weight","blk.0.attn_q.weight","blk.0.attn_q_norm.weight","blk.0.ffn_gate.weight"]:
        for t in r.tensors:
            if t.name == name:
                print(" ", name, str(t.tensor_type.name), "shape", list(t.shape), "bytes", t.data.nbytes)
                break
