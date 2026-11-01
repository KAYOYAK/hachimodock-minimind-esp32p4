"""Convert a MiniMind-3 raw PyTorch checkpoint to a HuggingFace Qwen3-format model dir.

MiniMind-3's attention (q_norm / k_norm RMSNorm on head_dim + GQA + SwiGLU + RoPE)
matches transformers' Qwen3ForCausalLM exactly, so we can materialise a standard
Qwen3 HF directory from the raw `full_sft_768.pth` state dict. This directory is the
input for llama.cpp's convert_hf_to_gguf.py and for our on-PC reference inference.

Usage:
  python pth2hf.py <input.pth> <output_dir>
"""
import json
import os
import sys

import torch

REPO = r"D:\minimind\src\minimind-master"
sys.path.insert(0, REPO)

from transformers import AutoTokenizer, Qwen3Config, Qwen3ForCausalLM  # noqa: E402
from model.model_minimind import MiniMindConfig  # noqa: E402


def main() -> None:
    src = sys.argv[1]
    dst = sys.argv[2]
    os.makedirs(dst, exist_ok=True)

    lm_config = MiniMindConfig(hidden_size=768, num_hidden_layers=8, max_seq_len=8192, use_moe=False)
    common = {
        "vocab_size": lm_config.vocab_size,
        "hidden_size": lm_config.hidden_size,
        "intermediate_size": lm_config.intermediate_size,
        "num_hidden_layers": lm_config.num_hidden_layers,
        "num_attention_heads": lm_config.num_attention_heads,
        "num_key_value_heads": lm_config.num_key_value_heads,
        "head_dim": lm_config.head_dim,
        "max_position_embeddings": lm_config.max_position_embeddings,
        "rms_norm_eps": lm_config.rms_norm_eps,
        "rope_theta": lm_config.rope_theta,
        "tie_word_embeddings": True,
        "use_sliding_window": False,
        "sliding_window": None,
    }
    print("qwen3 config:", json.dumps(common, ensure_ascii=False))

    cfg = Qwen3Config(**common)
    model = Qwen3ForCausalLM(cfg)
    state = torch.load(src, map_location="cpu", weights_only=False)
    model.load_state_dict(state, strict=True)
    model = model.to(torch.float16)
    n = sum(p.numel() for p in model.parameters())
    print(f"params: {n / 1e6:.2f}M")
    model.save_pretrained(dst, safe_serialization=True)

    tok = AutoTokenizer.from_pretrained(os.path.join(REPO, "model"))
    tok.save_pretrained(dst)
    print("tokenizer saved; special ids:", {t: tok.convert_tokens_to_ids(t) for t in
          ["<|im_start|>", "<|im_end|>", "<|endoftext|>"]})
    print("wrote HF model to", dst)


if __name__ == "__main__":
    main()
