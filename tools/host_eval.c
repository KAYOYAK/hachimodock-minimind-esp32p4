/* host_eval.c - PC-side evaluation harness for the patched Kestrel-MCU kernel.
 *
 * Compiles the same kmcu.c used by the ESP32-P4 firmware but with a scalar
 * pie_gemv_row stub, loads a KMCU image, feeds a prompt (token ids), prints the
 * top-8 logits after the prompt and a short greedy continuation. The output is
 * compared against tools/ref_minimind.py (NumPy reference over the same
 * quantized weights) to prove the port (QK-norm, GQA, RoPE, SwiGLU, tied head).
 *
 * Build (host, zig or gcc):
 *   zig cc -O2 -std=c11 -I main -o host_eval host_eval.c main/kmcu.c -lm
 * Usage:
 *   host_eval <model.kmcu> [comma-separated prompt token ids]
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "kmcu.h"

/* Scalar stand-in for the ESP32-P4 PIE assembly kernel. */
float pie_gemv_row(const int8_t *q, const int16_t *x, const int16_t *d, int nblk, int shift) {
    (void)shift;
    float acc = 0.0f;
    for (int b = 0; b < nblk; b++) {
        int32_t s = 0;
        for (int j = 0; j < 32; j++)
            s += (int32_t)q[(size_t)b * 32 + j] * (int32_t)x[(size_t)b * 32 + j];
        acc += (float)d[b] * (float)s;
    }
    return acc;
}

typedef struct { const uint8_t *base; } mem_ctx_t;
static int mem_read(void *ctx, uint32_t off, void *dst, uint32_t len) {
    memcpy(dst, ((mem_ctx_t *)ctx)->base + off, len);
    return 0;
}

/* MiniMind-3 chat prompt:
 *   <|im_start|>user\n你好，介绍一下你自己<|im_end|>\n
 *   <|im_start|>assistant\n<think>\n\n</think>\n\n
 */
static const int k_prompt[] = {
    1, 832, 311, 234, 1968, 294, 2919, 2360, 441, 1153, 2, 234,
    1, 1388, 570, 811, 234, 25, 234, 234, 26, 234, 234,
};

int main(int argc, char **argv) {
    if (argc < 2) {
        fprintf(stderr, "usage: %s <model.kmcu> [comma-separated prompt ids]\n", argv[0]);
        return 2;
    }
    FILE *f = fopen(argv[1], "rb");
    if (!f) { fprintf(stderr, "open fail: %s\n", argv[1]); return 2; }
    fseek(f, 0, SEEK_END);
    long sz = ftell(f);
    fseek(f, 0, SEEK_SET);
    uint8_t *base = (uint8_t *)malloc((size_t)sz);
    if (!base || fread(base, 1, (size_t)sz, f) != (size_t)sz) {
        fprintf(stderr, "read fail\n");
        return 2;
    }
    fclose(f);

    int prompt[64];
    int np = 0;
    if (argc >= 3) {
        char buf[4096];
        snprintf(buf, sizeof(buf), "%s", argv[2]);
        char *tok = strtok(buf, ",");
        while (tok && np < 64) {
            prompt[np++] = atoi(tok);
            tok = strtok(NULL, ",");
        }
    } else {
        np = (int)(sizeof(k_prompt) / sizeof(k_prompt[0]));
        memcpy(prompt, k_prompt, sizeof(k_prompt));
    }

    uint32_t n_tensors;
    memcpy(&n_tensors, base + 52, 4);
    km_model_t m;
    memset(&m, 0, sizeof(m));
    m.tensors = (km_tensor_t *)calloc(n_tensors, sizeof(km_tensor_t));
    km_err_t err;
    if (km_open(&m, base, &err) != 0) {
        fprintf(stderr, "km_open: %s\n", err.buf);
        return 2;
    }
    const km_arch_t *A = &m.arch;
    printf("FILE_BYTES %ld\n", sz);
    printf("ARCH layers=%u dim=%u nh=%u nkv=%u hd=%u ffn=%u vocab=%u max_seq=%u "
           "tied=%u theta=%.6f eps=%.8f\n",
           A->n_layers, A->dim, A->n_heads, A->n_kv_heads, A->head_dim,
           A->ffn_dim, A->vocab_size, A->max_seq, A->tied_embed,
           (double)A->rope_theta, (double)A->norm_eps);

    size_t fbytes = km_fast_bytes(&m);
    printf("FAST_BYTES %zu\n", fbytes);
    uint8_t *arena = (uint8_t *)malloc(fbytes);
    km_fast_t fast;
    fast.t = (km_ft_t *)calloc(n_tensors, sizeof(km_ft_t));
    km_fast_build(&m, &fast, arena, fbytes);

    uint32_t ctx = A->max_seq;
    if (ctx > (uint32_t)(np + 16)) ctx = (uint32_t)(np + 16);
    size_t kv = (size_t)A->n_layers * ctx * A->n_kv_heads * A->head_dim;
    float *kc = (float *)calloc(kv, sizeof(float));
    float *vc = (float *)calloc(kv, sizeof(float));
    float *sc = (float *)malloc(km_scratch_bytes(A));
    km_state_t st;
    km_state_init(&st, A, ctx, kc, vc, sc);

    uint8_t stage[65536];
    mem_ctx_t mctx = { base };
    int ids[8];
    float vals[8];
    int last = -1;
    for (int i = 0; i < np; i++) {
        last = km_decode_step(&m, &fast, &st, prompt[i], NULL, ids, vals, 8,
                              mem_read, &mctx, stage, sizeof(stage));
        if (last < 0) { fprintf(stderr, "decode fail at prompt %d\n", i); return 2; }
    }

    printf("PROMPT_N %d\n", np);
    printf("TOP8");
    for (int j = 0; j < 8; j++) printf(" %d:%.6f", ids[j], (double)vals[j]);
    printf("\n");

    int seq[128];
    int ns = 0;
    for (int i = 0; i < np; i++) seq[ns++] = prompt[i];
    seq[ns++] = last;
    for (int g = 0; g < 16; g++) {
        last = km_decode_step(&m, &fast, &st, last, NULL, ids, vals, 8,
                              mem_read, &mctx, stage, sizeof(stage));
        if (last < 0) break;
        seq[ns++] = last;
    }
    printf("SEQ");
    for (int i = 0; i < ns; i++) printf(" %d", seq[i]);
    printf("\n");
    return 0;
}
