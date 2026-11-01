"""Numerical equivalence check: MiniMind native PyTorch forward vs converted HF Qwen3 forward.

If the two produce (near-)identical logits for the same token ids, the Qwen3 mapping
(and therefore the GGUF built from it) preserves the checkpoint exactly.
"""
import os
import sys

import torch

REPO = r"D:\minimind\src\minimind-master"
sys.path.insert(0, REPO)

from transformers import AutoTokenizer, Qwen3ForCausalLM  # noqa: E402
from model.model_minimind import MiniMindConfig, MiniMindForCausalLM  # noqa: E402

PTH = r"D:\minimind\official\full_sft_768.pth"
HF = r"C:\p4test\work\hf_minimind3_official"


def main() -> None:
    tok = AutoTokenizer.from_pretrained(HF)
    msgs = [{"role": "user", "content": "你好，介绍一下你自己"}]
    text = tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
    ids = tok(text, return_tensors="pt").input_ids
    print("prompt text:", text.replace("\n", "\\n"))
    print("prompt ids:", ids.tolist())

    cfg = MiniMindConfig(hidden_size=768, num_hidden_layers=8, max_seq_len=8192, use_moe=False)
    native = MiniMindForCausalLM(cfg).eval()
    native.load_state_dict(torch.load(PTH, map_location="cpu", weights_only=False), strict=True)

    hf = Qwen3ForCausalLM.from_pretrained(HF, torch_dtype=torch.float32).eval()

    with torch.no_grad():
        a = native(ids).logits.float()
        b = hf(ids).logits.float()
    diff = (a - b).abs()
    print(f"logits shape {tuple(a.shape)}")
    print(f"max|diff| = {diff.max().item():.3e}  mean|diff| = {diff.mean().item():.3e}")
    print(f"last-token argmax native={a[0, -1].argmax().item()} hf={b[0, -1].argmax().item()}")
    top = torch.topk(b[0, -1], 8)
    print("hf top8:", [(tok.decode([i]), round(float(p), 3)) for p, i in zip(top.values, top.indices)])


if __name__ == "__main__":
    main()
