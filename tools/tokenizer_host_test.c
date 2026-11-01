/* Host round-trip test for the MiniMind-3 tokenizer (same tokenizer.c as firmware).
 * Reads a cases file: each line is a hex-encoded UTF-8 string.
 * For each line prints:
 *   E <comma-separated token ids>   (encode)
 *   D <hex bytes>                  (decode back)
 * The Python driver compares E with the HF tokenizer and D with the input.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "tokenizer.h"

static int hexval(int c) {
    if (c >= '0' && c <= '9') return c - '0';
    if (c >= 'a' && c <= 'f') return c - 'a' + 10;
    if (c >= 'A' && c <= 'F') return c - 'A' + 10;
    return -1;
}

int main(int argc, char **argv) {
    if (argc < 3) {
        fprintf(stderr, "usage: %s <tokenizer.bin> <cases.hex>\n", argv[0]);
        return 2;
    }
    if (mm_tok_load(argv[1]) != 0) {
        fprintf(stderr, "load failed\n");
        return 2;
    }
    FILE *f = fopen(argv[2], "r");
    if (!f) { perror("cases"); return 2; }

    char line[8192];
    while (fgets(line, sizeof(line), f)) {
        size_t n = strlen(line);
        while (n && (line[n - 1] == '\n' || line[n - 1] == '\r')) line[--n] = '\0';
        uint8_t buf[4096];
        size_t blen = 0;
        for (size_t i = 0; i + 1 < n; i += 2) {
            int hi = hexval((unsigned char)line[i]), lo = hexval((unsigned char)line[i + 1]);
            if (hi < 0 || lo < 0) break;
            if (blen < sizeof(buf)) buf[blen++] = (uint8_t)((hi << 4) | lo);
        }
        buf[blen] = 0;

        int ids[2048];
        int n_ids = mm_tok_encode((const char *)buf, ids, 2048);
        printf("E");
        if (n_ids < 0) {
            printf(" ERR\n");
        } else {
            for (int i = 0; i < n_ids; i++) printf(" %d", ids[i]);
            printf("\n");
        }

        char out[8192];
        int got = (n_ids < 0) ? -1 : mm_tok_decode(ids, n_ids, out, sizeof(out));
        printf("D ");
        if (got < 0) {
            printf("ERR\n");
        } else {
            for (int i = 0; i < got; i++) printf("%02x", (unsigned char)out[i]);
            printf("\n");
        }
    }
    fclose(f);
    return 0;
}
