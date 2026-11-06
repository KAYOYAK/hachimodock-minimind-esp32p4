# v0.2.1 — complete frontier artifact

Artifact-completeness release accompanying the revised manuscript. The previous release
(v0.2.0) contained only the deployed q3e4 image; the revised paper's capacity–accuracy frontier
and the q3/q2/mixed comparisons need the other six quantized images, so all seven are published
here with full SHA-256 hashes and the tokenizer.

All images are quantized from the author's own `full_sft_768.pth` with the same block-32 recipe
used by the C kernel (q4_0: 18 B / 32 weights, q3_0: 14 B, q2_0: 10 B; fp16 block scale).

## Deployed image (same as v0.2.0)

| File | Size (B) | SHA-256 |
|---|---|---|
| `selftrained-q3e4.kmcu` | 28,632,448 | `feb574f966980a71c53c6b1f56daf054ff267ed425b72ee5ce93f6002ccf87f0` |

## Frontier / ablation images

| File | Size (B) | SHA-256 |
|---|---|---|
| `selftrained-q4.kmcu` | 36,005,248 | `b1ef7ad512e671cc7d417519174a95cc9fa62c037459b84c120f223e09a75aad` |
| `selftrained-q3.kmcu` | 28,018,048 | `f49db2e99be72e2440e2f987ec535ca1a5aded51e08de67934839a45d1fbe4ae` |
| `selftrained-mixed.kmcu` | 30,401,920 | `b1e70a6a85605891ed101cdad437b8ad85087c08cd0062d80f45cff4041ae45f` |
| `selftrained-mix432.kmcu` | 26,666,368 | `a48215a38284ff23bd4c6b7e6a89fea43f894a2678fe033ce38df14742baffaf` |
| `selftrained-mix42.kmcu` | 24,798,592 | `0d87fcfd59631411bd67b6491202eaa6a239576d193301f00cfc017b6ea4b9b6` |
| `selftrained-q2.kmcu` | 20,030,848 | `2193d5fb4b4a4019b306b8b28c51bd9417bb947a86ae487a77ddc1b134e5035b` |

## Tokenizer

`tokenizer.bin` (151,223 B) is byte-identical to the one in v0.1.0 and v0.2.0.

## Notes

- q4 does **not** fit the 32-MB PSRAM budget (36,005,248 B); it is published as the
  host-simulated CE reference only.
- q3's rule score on the 30-prompt well-formedness set is 21/30 (70%), below the pre-registered
  80% gate; q3e4 scores 24/30 on the host recipe and 22/30 on the device run. Only q3e4 passes
  both criteria on the host recipe.
- The measurement report is in `docs/MEASUREMENTS.md`; the pre-registration record
  (prompt set, rule checker, thresholds) is in `paper/` at commit `be624d7`.
