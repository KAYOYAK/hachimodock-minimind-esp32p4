import sys, runpy
SRC = r"D:\AI\tools\llama-src\llama.cpp-b11270"
sys.path[:0] = [SRC, SRC + r"\gguf-py"]
import conversion.base as base

_orig = base.TextModel.get_vocab_base_pre

def _patched(self, tokenizer):
    try:
        return _orig(self, tokenizer)
    except Exception as exc:
        print(f"[patch] pre-tokenizer not recognised ({exc.__class__.__name__}); using gpt2")
        return "gpt-2"

base.TextModel.get_vocab_base_pre = _patched
sys.argv = ["convert_hf_to_gguf.py", r"C:\p4test\work\hf_minimind3_official", "--outfile", r"C:\p4test\artifacts\minimind-3-f16.gguf", "--outtype", "f16"]
runpy.run_path(SRC + r"\convert_hf_to_gguf.py", run_name="__main__")
