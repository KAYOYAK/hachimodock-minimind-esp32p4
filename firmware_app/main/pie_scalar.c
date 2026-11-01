/* Scalar fallback for the Kestrel PIE GEMV symbol.
 *
 * The packed-weight path (MiniMind-3 q4/q3/q2 zero-copy) does not call this
 * function; it only exists so that the legacy expanded-q4 path links when the
 * PIE assembly (firmware/main/pie_dotprod.S) is not included in the build.
 * If the PIE kernel is added later, remove this file from the component. */
#include <stdint.h>
#include <stddef.h>

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

