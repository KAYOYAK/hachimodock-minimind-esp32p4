#ifndef MM_TOKENIZER_H
#define MM_TOKENIZER_H

#include <stddef.h>
#include <stdint.h>

/* MiniMind-3 tokenizer 接口（Qwen2 ByteLevel BPE，vocab 6400）。
 *
 * 目前为 stub：待实现。计划：
 *   - tools/export_tokenizer.py: HF tokenizer.json -> tokenizer.bin
 *       [vocab 字符串表][merge rank 表][special tokens][byte->unicode 表]
 *   - tokenizer.c: GPT-2 byte-level BPE + 简化 pretokenizer（ASCII/CJK/数字/空白分组）
 *   - 用 HF tokenizer 在 中/英/混合 测试集上逐 id 对拍，要求 100% 一致。
 *
 * 返回：0 成功，<0 失败。 */
int mm_tok_load(const char *path);                 /* 从 TF 卡/flash 加载词表 */
int mm_tok_ready(void);
int mm_tok_encode(const char *text, int *ids, int max_ids);
int mm_tok_decode(const int *ids, int n_ids, char *out, int out_cap);
int mm_tok_special(const char *name);              /* "<|im_start|>" -> id */
int mm_tok_eos(void);
int mm_tok_bos(void);

#endif /* MM_TOKENIZER_H */
