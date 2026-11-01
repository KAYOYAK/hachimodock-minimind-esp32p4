/* MiniMind-3 tokenizer: GPT-2/Qwen2-style ByteLevel BPE (vocab 6400) for MCU.
 *
 * Portable C11 (no ESP-IDF dependency) so the same file runs on the PC host test
 * (tools/tokenizer_host_test.c) and in the ESP32-P4 firmware.
 *
 * Pretokenizer = hand-written equivalent of the GPT-2 regex
 *   (?i:'s|'t|'re|'ve|'m|'ll|'d)| ?\p{L}+| ?\p{N}+| ?[^\s\p{L}\p{N}]+|\s+(?!\S)|\s+
 * validated against the HF tokenizers output (see tools/tokenizer_proto*.py).
 *
 * Binary format: produced by tools/export_tokenizer.py ("MMTK" v1).
 */
#include "tokenizer.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define TK_MAGIC 0x4b544d4d /* "MMTK" */
#define TK_MAX_PIECE 1024

typedef struct {
    uint32_t id;
    const uint8_t *str;
    uint32_t len;
} tk_special_t;

static struct {
    int ready;
    const uint8_t *buf;
    size_t size;
    uint32_t V, M, S;
    const uint32_t *byte2id;
    const uint32_t *byte2cp;
    uint32_t *vocab_off;   /* V */
    uint32_t *vocab_len;   /* V */
    const uint8_t *vocab_base;
    uint32_t *mg_a, *mg_b, *mg_m; /* M each */
    tk_special_t *spec;    /* S */
    /* merge hash: key = a*V+b+1 -> merge index+1 (0 = empty) */
    uint32_t hbits;
    uint32_t *hkey;
    uint32_t *hval;
} g;

static uint32_t rd_u32(const uint8_t *p) {
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8) | ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}

/* ---------------- UTF-8 / unicode class ---------------- */

static int is_letter(uint32_t c) {
    return ((c >= 0x41 && c <= 0x5A) || (c >= 0x61 && c <= 0x7A) ||
            (c >= 0xC0 && c <= 0xD6) || (c >= 0xD8 && c <= 0xF6) || (c >= 0xF8 && c <= 0xFF) ||
            c == 0xAA || c == 0xB5 || c == 0xBA ||
            (c >= 0x0370 && c <= 0x03FF) || (c >= 0x0400 && c <= 0x04FF) ||
            (c >= 0x3040 && c <= 0x309F) || (c >= 0x30A0 && c <= 0x30FF) ||
            (c >= 0x3400 && c <= 0x4DBF) || (c >= 0x4E00 && c <= 0x9FFF) ||
            (c >= 0xF900 && c <= 0xFAFF) || (c >= 0x20000 && c <= 0x2FA1F) ||
            (c >= 0xAC00 && c <= 0xD7A3) || (c >= 0x1100 && c <= 0x11FF) ||
            (c >= 0xFF21 && c <= 0xFF3A) || (c >= 0xFF41 && c <= 0xFF5A));
}
static int is_number(uint32_t c) {
    return (c >= 0x30 && c <= 0x39) || (c >= 0xFF10 && c <= 0xFF19) ||
           (c >= 0x0660 && c <= 0x0669) || (c >= 0x06F0 && c <= 0x06F9);
}
static int is_space(uint32_t c) {
    return (c == 0x09 || c == 0x0A || c == 0x0B || c == 0x0C || c == 0x0D || c == 0x20 ||
            c == 0x85 || c == 0xA0 || c == 0x1680 || c == 0x2028 || c == 0x2029 ||
            c == 0x202F || c == 0x205F || c == 0x3000 || (c >= 0x2000 && c <= 0x200A));
}
static int is_punct(uint32_t c) { return !(is_space(c) || is_letter(c) || is_number(c)); }

/* Decode UTF-8. Returns bytes consumed (>=1), stores codepoint. */
static int utf8_next(const uint8_t *s, size_t n, uint32_t *cp) {
    uint8_t b = s[0];
    if (b < 0x80) { *cp = b; return 1; }
    if ((b & 0xE0) == 0xC0 && n >= 2 && (s[1] & 0xC0) == 0x80) {
        *cp = ((uint32_t)(b & 0x1F) << 6) | (s[1] & 0x3F);
        return 2;
    }
    if ((b & 0xF0) == 0xE0 && n >= 3 && (s[1] & 0xC0) == 0x80 && (s[2] & 0xC0) == 0x80) {
        *cp = ((uint32_t)(b & 0x0F) << 12) | ((uint32_t)(s[1] & 0x3F) << 6) | (s[2] & 0x3F);
        return 3;
    }
    if ((b & 0xF8) == 0xF0 && n >= 4 && (s[1] & 0xC0) == 0x80 && (s[2] & 0xC0) == 0x80 &&
        (s[3] & 0xC0) == 0x80) {
        *cp = ((uint32_t)(b & 0x07) << 18) | ((uint32_t)(s[1] & 0x3F) << 12) |
              ((uint32_t)(s[2] & 0x3F) << 6) | (s[3] & 0x3F);
        return 4;
    }
    *cp = b; /* invalid byte: treat as latin-1 */
    return 1;
}

/* ---------------- merge hash ---------------- */

static uint32_t hash_pair(uint32_t a, uint32_t b) {
    uint32_t k = (a * g.V + b + 1u) * 2654435761u;
    return k >> (32 - g.hbits);
}
static void hash_put(uint32_t a, uint32_t b, uint32_t idx1) {
    uint32_t mask = (1u << g.hbits) - 1u;
    uint32_t h = hash_pair(a, b);
    for (;;) {
        if (g.hval[h] == 0) { g.hkey[h] = a * g.V + b + 1u; g.hval[h] = idx1; return; }
        h = (h + 1) & mask;
    }
}
/* returns merge index+1 or 0 */
static uint32_t hash_get(uint32_t a, uint32_t b) {
    uint32_t mask = (1u << g.hbits) - 1u;
    uint32_t key = a * g.V + b + 1u;
    uint32_t h = hash_pair(a, b);
    for (;;) {
        if (g.hval[h] == 0) return 0;
        if (g.hkey[h] == key) return g.hval[h];
        h = (h + 1) & mask;
    }
}
/* merged token id for adjacent pair, or UINT32_MAX */
static uint32_t merge_lookup(uint32_t a, uint32_t b) {
    uint32_t idx1 = hash_get(a, b);
    if (!idx1) return 0xFFFFFFFFu;
    return g.mg_m[idx1 - 1];
}

/* ---------------- public API ---------------- */

int mm_tok_load(const char *path) {
    FILE *f = fopen(path, "rb");
    if (!f) { fprintf(stderr, "[tok] open %s failed\n", path); return -1; }
    fseek(f, 0, SEEK_END);
    long sz = ftell(f);
    fseek(f, 0, SEEK_SET);
    if (sz < 32) { fclose(f); return -1; }
    uint8_t *buf = (uint8_t *)malloc((size_t)sz);
    if (!buf) { fclose(f); return -1; }
    if (fread(buf, 1, (size_t)sz, f) != (size_t)sz) { fclose(f); free(buf); return -1; }
    fclose(f);

    if (rd_u32(buf) != TK_MAGIC || rd_u32(buf + 4) != 1) {
        fprintf(stderr, "[tok] bad magic/version\n");
        free(buf);
        return -1;
    }
    uint32_t V = rd_u32(buf + 8), M = rd_u32(buf + 12), S = rd_u32(buf + 16);
    size_t need = 20 + 256 * 4 + 256 * 4;
    if (V == 0 || V > 65536 || M > 100000 || S > 256 || (size_t)sz < need) {
        fprintf(stderr, "[tok] bad header\n");
        free(buf);
        return -1;
    }
    g.buf = buf;
    g.size = (size_t)sz;
    g.V = V; g.M = M; g.S = S;
    g.byte2id = (const uint32_t *)(buf + 20);
    g.byte2cp = (const uint32_t *)(buf + 20 + 1024);

    g.vocab_off = (uint32_t *)calloc(V, sizeof(uint32_t));
    g.vocab_len = (uint32_t *)calloc(V, sizeof(uint32_t));
    g.mg_a = (uint32_t *)calloc(M ? M : 1, sizeof(uint32_t));
    g.mg_b = (uint32_t *)calloc(M ? M : 1, sizeof(uint32_t));
    g.mg_m = (uint32_t *)calloc(M ? M : 1, sizeof(uint32_t));
    g.spec = (tk_special_t *)calloc(S ? S : 1, sizeof(tk_special_t));
    if (!g.vocab_off || !g.vocab_len || !g.mg_a || !g.mg_b || !g.mg_m || !g.spec) return -1;

    size_t off = 20 + 2048;
    for (uint32_t i = 0; i < V; i++) {
        if (off + 4 > g.size) return -1;
        uint32_t len = rd_u32(buf + off);
        off += 4;
        if (off + len > g.size) return -1;
        g.vocab_off[i] = (uint32_t)off;
        g.vocab_len[i] = len;
        off += len;
    }
    g.vocab_base = buf;
    for (uint32_t i = 0; i < M; i++) {
        if (off + 12 > g.size) return -1;
        g.mg_a[i] = rd_u32(buf + off);
        g.mg_b[i] = rd_u32(buf + off + 4);
        g.mg_m[i] = rd_u32(buf + off + 8);
        off += 12;
    }
    for (uint32_t i = 0; i < S; i++) {
        if (off + 8 > g.size) return -1;
        g.spec[i].id = rd_u32(buf + off);
        uint32_t len = rd_u32(buf + off + 4);
        off += 8;
        if (off + len > g.size) return -1;
        g.spec[i].str = buf + off;
        g.spec[i].len = len;
        off += len;
    }

    /* merge hash: >= 2*M slots */
    g.hbits = 4;
    while ((1u << g.hbits) < 4 * (M ? M : 1)) g.hbits++;
    uint32_t hn = 1u << g.hbits;
    g.hkey = (uint32_t *)calloc(hn, sizeof(uint32_t));
    g.hval = (uint32_t *)calloc(hn, sizeof(uint32_t));
    if (!g.hkey || !g.hval) return -1;
    for (uint32_t i = 0; i < M; i++) hash_put(g.mg_a[i], g.mg_b[i], i + 1);

    g.ready = 1;
    return 0;
}

int mm_tok_ready(void) { return g.ready; }

/* BPE over one pretoken piece (UTF-8 bytes).
 * ByteLevel pretokenization maps every input BYTE to one of 256 unicode chars;
 * BPE then merges those char-tokens. Here the byte->token-id map is byte2id, so
 * we start from one token per byte (emoji/CJK included). */
static int bpe_piece(const uint8_t *s, size_t n, int *ids, int max_ids) {
    uint32_t *seq = (uint32_t *)malloc(sizeof(uint32_t) * (n + 1));
    if (!seq) return -1;
    for (size_t i = 0; i < n; i++) seq[i] = g.byte2id[s[i]];
    size_t nsym = n;
    while (nsym > 1) {
        size_t best = 0;
        uint32_t best_rank = 0xFFFFFFFFu;
        uint32_t best_m = 0;
        for (size_t j = 0; j + 1 < nsym; j++) {
            uint32_t idx1 = hash_get(seq[j], seq[j + 1]);
            if (idx1 && (idx1 - 1) < best_rank) {
                best_rank = idx1 - 1;
                best = j;
                best_m = g.mg_m[idx1 - 1];
            }
        }
        if (best_rank == 0xFFFFFFFFu) break;
        seq[best] = best_m;
        memmove(seq + best + 1, seq + best + 2, (nsym - best - 2) * sizeof(uint32_t));
        nsym--;
    }
    int out = 0;
    for (size_t j = 0; j < nsym; j++) {
        if (out >= max_ids) break;
        ids[out++] = (int)seq[j];
    }
    free(seq);
    return out;
}

/* returns end byte index of next pretoken starting at i, or 0 if none */
static size_t next_piece(const uint8_t *s, size_t n, size_t i) {
    uint32_t cp;
    int adv = utf8_next(s + i, n - i, &cp);
    /* contraction */
    if (cp == 0x27 && i + (size_t)adv < n) {
        static const char *tails[] = {"s", "t", "re", "ve", "m", "ll", "d"};
        static const int tlens[] = {1, 1, 2, 2, 1, 2, 1};
        for (int t = 0; t < 7; t++) {
            size_t pos = i + (size_t)adv;
            int ok = 1;
            for (int q = 0; q < tlens[t]; q++) {
                uint32_t tc;
                if (pos >= n) { ok = 0; break; }
                int a2 = utf8_next(s + pos, n - pos, &tc);
                if (tc >= 'A' && tc <= 'Z') tc += 32;
                if (tc != (uint32_t)(unsigned char)tails[t][q]) { ok = 0; break; }
                pos += (size_t)a2;
            }
            if (ok) return pos;
        }
    }
    size_t j = i;
    /* " ?\p{L}+" */
    if (cp == 0x20 && i + (size_t)adv < n) {
        uint32_t c2; (void)utf8_next(s + i + (size_t)adv, n - i - (size_t)adv, &c2);
        if (is_letter(c2)) {
            j = i + (size_t)adv;
            while (j < n) {
                uint32_t c; int a2 = utf8_next(s + j, n - j, &c);
                if (!is_letter(c)) break;
                j += (size_t)a2;
            }
            return j;
        }
    }
    if (is_letter(cp)) {
        j = i;
        while (j < n) {
            uint32_t c; int a2 = utf8_next(s + j, n - j, &c);
            if (!is_letter(c)) break;
            j += (size_t)a2;
        }
        return j;
    }
    /* " ?\p{N}+" */
    if (cp == 0x20 && i + (size_t)adv < n) {
        uint32_t c2; (void)utf8_next(s + i + (size_t)adv, n - i - (size_t)adv, &c2);
        if (is_number(c2)) {
            j = i + (size_t)adv;
            while (j < n) {
                uint32_t c; int a2 = utf8_next(s + j, n - j, &c);
                if (!is_number(c)) break;
                j += (size_t)a2;
            }
            return j;
        }
    }
    if (is_number(cp)) {
        j = i;
        while (j < n) {
            uint32_t c; int a2 = utf8_next(s + j, n - j, &c);
            if (!is_number(c)) break;
            j += (size_t)a2;
        }
        return j;
    }
    /* " ?[^\s\p{L}\p{N}]+" */
    if (cp == 0x20 && i + (size_t)adv < n) {
        uint32_t c2; (void)utf8_next(s + i + (size_t)adv, n - i - (size_t)adv, &c2);
        if (is_punct(c2)) {
            j = i + (size_t)adv;
            while (j < n) {
                uint32_t c; int a2 = utf8_next(s + j, n - j, &c);
                if (!is_punct(c)) break;
                j += (size_t)a2;
            }
            return j;
        }
    }
    if (is_punct(cp)) {
        j = i;
        while (j < n) {
            uint32_t c; int a2 = utf8_next(s + j, n - j, &c);
            if (!is_punct(c)) break;
            j += (size_t)a2;
        }
        return j;
    }
    /* whitespace: "\s+(?!\S)|\s+" — leave the last whitespace char when the run is
     * followed by non-space text (mirrors the regex backtracking). */
    if (is_space(cp)) {
        j = i;
        while (j < n) {
            uint32_t c; int a2 = utf8_next(s + j, n - j, &c);
            if (!is_space(c)) break;
            j += (size_t)a2;
        }
        if (j < n) {
            /* remove one codepoint from the end */
            size_t k = i;
            size_t last = i;
            while (k < j) { last = k; uint32_t c; int a2 = utf8_next(s + k, n - k, &c); k += (size_t)a2; }
            j = last;
        }
        return j;
    }
    return i + (size_t)adv;
}

int mm_tok_encode(const char *text, int *ids, int max_ids) {
    if (!g.ready || !text) return -1;
    const uint8_t *s = (const uint8_t *)text;
    size_t n = strlen(text);
    size_t i = 0;
    int out = 0;
    while (i < n) {
        /* special tokens first (longest match: export sorted by length desc) */
        int hit = 0;
        for (uint32_t sp = 0; sp < g.S; sp++) {
            if (g.spec[sp].len && g.spec[sp].len <= n - i &&
                memcmp(s + i, g.spec[sp].str, g.spec[sp].len) == 0) {
                if (out >= max_ids) return out;
                ids[out++] = (int)g.spec[sp].id;
                i += g.spec[sp].len;
                hit = 1;
                break;
            }
        }
        if (hit) continue;
        size_t end = next_piece(s, n, i);
        if (end <= i) end = i + 1;
        int got = bpe_piece(s + i, end - i, ids + out, max_ids - out);
        if (got < 0) return -1;
        out += got;
        i = end;
    }
    return out;
}

int mm_tok_decode(const int *ids, int n_ids, char *out, int out_cap) {
    if (!g.ready) return -1;
    int o = 0;
    for (int t = 0; t < n_ids; t++) {
        int id = ids[t];
        if (id < 0 || (uint32_t)id >= g.V) return -1;
        const uint8_t *s = g.vocab_base + g.vocab_off[id];
        uint32_t len = g.vocab_len[id];
        size_t i = 0;
        while (i < len) {
            uint32_t cp;
            int adv = utf8_next(s + i, len - i, &cp);
            int byte = -1;
            for (uint32_t b = 0; b < 256; b++) {
                if (g.byte2cp[b] == cp) { byte = (int)b; break; }
            }
            if (byte < 0) return -1;
            if (o >= out_cap - 1) return o;
            out[o++] = (char)byte;
            i += (size_t)adv;
        }
    }
    out[o] = '\0';
    return o;
}

int mm_tok_special(const char *name) {
    if (!g.ready || !name) return -1;
    size_t n = strlen(name);
    for (uint32_t sp = 0; sp < g.S; sp++) {
        if (g.spec[sp].len == n && memcmp(g.spec[sp].str, name, n) == 0)
            return (int)g.spec[sp].id;
    }
    return -1;
}
int mm_tok_eos(void) {
    int id = mm_tok_special("<|im_end|>");
    return id >= 0 ? id : 2;
}
int mm_tok_bos(void) {
    int id = mm_tok_special("<|im_start|>");
    return id >= 0 ? id : 1;
}
