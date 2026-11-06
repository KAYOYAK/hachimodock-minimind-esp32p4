# Response to simulated reviews — revision plan (v2 draft, 2026-11-06)

> Note: the eight review documents are **AI-simulated** (provided by the author's external
> prompts), not real IEEE reviews. This file maps every substantive point to its disposition in
> the v2 manuscript draft. The v2 draft is **not** submitted; it is prepared for the real
> revision round if a Major Revision decision arrives.

## Legend

- **Fixed (text)** — corrected in `ESL-LETTER-DRAFT.tex` v2
- **Fixed (data)** — new measurement or artifact added
- **Deferred** — requires board/hardware or a new experiment; planned for the real revision
- **Not reproducible** — reviewer misread a PDF-extraction artefact or an older draft

## A. Accuracy bound and evaluation

| # | Review point | Disposition | Where in v2 |
|---|---|---|---|
| A1 | mixed/mix42/mix432 rule < 80% but text says "satisfy the bound" | **Fixed (text)**: only q3e4 passes both criteria (host recipe); mixed/mix42/mix432 are "CE-feasible but rule-infeasible" | Abstract; Results Sec. III; Table III |
| A2 | device q3e4 rule score 22/30 not reported; only host 80% | **Fixed (text)**: both reported (host 24/30 = 80%, device 22/30 = 73.3%); bound is defined on the host recipe because the frontier is host-simulated, device score is a cross-check | Method "Accuracy bound"; Results |
| A3 | q4 rule 73.3% vs "fp32 also 80%" | **Fixed (text)**: fp32 row added (CE 6.973, rule 80%); q4 73.3% explained as n=30 noise; CE and rule references separated | Table III; Results |
| A4 | q3 rule score missing; q3 smaller with same CE | **Fixed (data)**: q3 rule = 21/30 = 70% (below gate). q3e4's q4 embedding is now justified by the rule criterion, not CE | Table III; Method "Bit allocation" |
| A5 | rule set measures well-formedness, not accuracy; n=30 CI wide | **Fixed (text)**: renamed "well-formedness score", rules listed; CI/per-prompt details remain in the artifact. A true task-accuracy evaluation is **deferred** (needs new prompts + semantic scoring) | Method; Results |
| A6 | no evidence for "pre-registered" | **Fixed (text)**: commit `be624d7` (2026-11-05 17:46) archives prompts/rules/thresholds, 3.6 h before the first q3e4 device log (21:24) | Method |
| A7 | model quality/training not established; loss vs CE gap | **Deferred**: v2 states the model configuration, corpus documentation pointer, and that absolute quality is not claimed. A public held-out CE and a semantic evaluation are planned; the held-out text is author-written and described as such | Method "Model"; Limitations |

## B. Speed, latency and attribution

| # | Review point | Disposition | Where in v2 |
|---|---|---|---|
| B1 | five different latency/throughput numbers from different builds | **Fixed (text)**: final build 1,612 ms / 0.620 tok/s everywhere (Table II, Table III q3e4, Table IV, abstract, conclusion); pre-final values appear only as intermediate ablation rows | Tables II–IV; abstract; conclusion |
| B2 | Amdahl 1.97× not reproducible; circular "kernel gains" | **Fixed (text)**: post-change r gives 2.10/1.22/1.32; baseline share f=0.994 gives 2.13 for stage 1; explicitly labelled as an attribution, not an independent prediction | Results |
| B3 | bandwidth ranges inconsistent with Table II | **Fixed (text)**: 11.7/14.4/19.2 MB/s total and 10.98/13.5/18.2 MB/s weight-only, for the three builds; microbenchmark now described (1 MB buffer, four accumulators) | Results |
| B4 | "instruction-bound" only circumstantial; no cycles/CPI | **Partially fixed (text)**: 9.1 cycles/weight added as supporting accounting; a read-only/PMU control experiment is **deferred** (needs board time) | Discussion |
| B5 | "end-to-end" is actually decode; startup/prefill omitted from conclusion | **Fixed (text)**: "decode" used throughout; conclusion states boot 20.6 s, token-by-token prefill, single-turn use | Abstract; Results; Discussion; Conclusion |
| B6 | FP16 K/V "statistically unchanged"; context effect conflated with precision | **Fixed (text)**: ΔCE=0.0014 stated; "within run-to-run variation (pre-optimization kernel)"; 15% is attributed to context length | Results "FP16 K/V" |
| B7 | FP16 K/V latency not re-measured on final build | **Deferred** (board needed) | — |

## C. Tables, numbers and units

| # | Review point | Disposition | Where in v2 |
|---|---|---|---|
| C1 | Table I does not close (209,860 B) | **Fixed (text)**: row "Runtime PSRAM (heap/USB) 209,860" added; table now sums to 33,554,432 | Table I |
| C2 | Intro 244 MiB FP16 / 128 MiB INT8 | **Fixed (text)**: 122 MiB FP16 / 61 MiB INT8 (244 MiB FP32) | Introduction |
| C3 | Table III mixes host accuracy with device ms; stale build | **Fixed (text)**: caption states host CE/rule + device final-build ms; q3e4 ms = 1,612; fp32 row added; q3 rule = 70% | Table III |
| C4 | Table IV 0.465 stale; caption conflicts with "all numbers regenerable" | **Fixed (text)**: 0.620; caption distinguishes prior-work values from this work; regeneration claim narrowed | Table IV; Reproducibility |
| C5 | Fig. 1a budget line at 32.0 (decimal MB) | **Fixed (data)**: line moved to the image budget 31.0 MB (32 MiB − KV − runtime), labelled; q4* defined in caption | Fig. 1a; caption |
| C6 | Fig. 1b n=32 vs text n=64; truncated y-axis | **Fixed (data)**: panel (b) replaced by histogram of all 64 measured steps (mean 1,620.5, p95 1,645.5); full y range | Fig. 1b |
| C7 | PPL 1,107 should be 1,112 | **Fixed (text)**: 1,112 | Results "FP16 K/V" |
| C8 | Method says KV remains FP32 | **Fixed (text)**: deployed FP16 at 192 tokens; FP32 at 96 tokens is the earlier/fallback configuration | Method |
| C9 | "attention compressed less aggressively than FFN" describes mixed, not q3e4 | **Fixed (text)**: q3e4 has both q3; mixed promotes attention to q4 | Method "Bit allocation" |
| C10 | 1.34× should be 1.33×; units mixed; "on-package" wrong | **Fixed (text)**: 1.33× (2,152/1,612 = 1.33499); MB/MiB used consistently; "on-board PSRAM" (hex_psram shows an external 256-Mbit device) | Abstract; Tables |

## D. Provenance, artifact and references

| # | Review point | Disposition | Where in v2 |
|---|---|---|---|
| D1 | Kestrel-MCU engine not cited; no reused/modified/new split | **Fixed (text)**: cited (ref. [3]); paragraph lists reused (q4_0/q3_0 formats, packed GEMV) vs new (int16 integer path, 3-bit unpack, hoisting, block sums, two-row unroll, FP16 K/V); explains why Kestrel's PIE w8a16 path (int8 expansion, 61 MB) cannot fit 32 MB | Method "Zero-copy packed GEMV"; references |
| D2 | Frontier images not published; artifact claim overreach | **Fixed (data)**: release **v0.2.1** with all seven images + tokenizer, full SHA-256s | Repository release |
| D3 | SHA truncated; no commit/tag; regeneration claim | **Fixed (text)**: full SHA-256; release tag v0.2.1; claim narrowed to Tables I–III + this-work row | Reproducibility |
| D4 | [13] ternary ViT uncited | **Fixed (text)**: cited in the Introduction | Introduction |
| D5 | Repository README/docs stale numbers | **Fixed (docs)**, ongoing sweep | `docs/`, `README.md` |

## E. Claims that the simulated reviewers misread (recorded, not changed)

| Claim in review | Reality |
|---|---|
| Table II header "rMB/s / 0.98810.98" | Render/PDF text-extraction artefact; the table has separate `r` and `MB/s` columns |
| Fig. 1b "1.629 ms / 1.648 ms" unit error | It is the thousands separator (`1,629 ms`); the real issue was two different runs, now fixed |
| "Introduction repeats a paragraph / 'on a 26 microcontroller'" | Not present in the submitted PDF; "26" is a line number |
| "5,622 ms expanded FP32 baseline is physically impossible" | The physical-impossibility point is valid for an *expanded copy*; the measurement was an earlier **packed** path with per-weight float dequantization. v2 relabels it and describes it; a rebuilt same-board baseline is deferred |

## F. Deferred experiments (needed only if the real revision asks)

1. Rebuild a float-dequant baseline variant on the board (3 runs).
2. 192-token-window CE for all configurations (currently 96-token windows; deployment is 192).
3. Prompt set expanded to ≥100 with Wilson CIs and per-prompt pass/fail.
4. Public held-out corpus CE / bits-per-byte and one small instruction-following evaluation.
5. Same-access-pattern memory-only control or PMU/cache counters for the bandwidth argument.
6. UART boot log to itemize the 209,860 B runtime allocation (currently reasoned, not logged).
7. FP16-vs-FP32 K/V latency on the final build.
8. Energy-per-token (needs a USB power meter).
