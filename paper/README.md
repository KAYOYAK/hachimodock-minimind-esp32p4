# Paper sources (IEEE ESL letter)

**Title:** Fully-Resident Weight Storage for Mixed-Precision SLM Inference on a 32-MB PSRAM MCU

## Compile

```powershell
# install once (chocolatey) if tectonic is missing:
#   choco install tectonic -y
# first run needs the TeX bundle; archive.org is blocked on this machine, so use the mirror:
tectonic --web-bundle https://relay.fullyjustified.net/default_bundle.tar ESL-LETTER-DRAFT.tex
```

The result is a 4-page IEEEtran letter (within the ESL page limit).

## Files

| File | Purpose |
|---|---|
| `ESL-LETTER-DRAFT.tex` | main manuscript (author/affiliation still `<...>` placeholders) |
| `figures/fig_frontier_latency.png` | Fig. 1: (a) capacity--accuracy frontier, (b) per-token latency |
| `make_figures.py` | regenerates Fig. 1 from the measured data |
| `RESULTS.md` | all measured numbers, one place |
| `ESL-LETTER-OUTLINE.md` | outline and design decisions |
| `heldout_text.txt`, `heldout_ids.json`, `heldout_en_ids.json` | held-out CE corpora (ZH/EN) |
| `eval_prompts.json`, `score_prompts.py` | 30-prompt deterministic rule scoring |
| `host_ce.py`, `host_rules.py` | host simulation (same block-32 recipe as firmware) |
| `parse_device_log.py` | device log → CE / rule summary |
| `ce_host_zh.csv`, `ce_host_en.csv` | host windowed-CE results |
| `ACKNOWLEDGMENT-AI.md`, `SUBMISSION-CHECKLIST.md`, `RESPONSE-TEMPLATE.md` | submission workflow documents |

## Submission status (2026-11-06)

1. ✅ Author block filled: Shizhou Xu, Guangxi Medical University, Nanning, China,
   X16717701114@outlook.com; manuscript received Nov. 6, 2026; `\markboth` updated.
2. ✅ AI disclosure confirmed: DeepSeek Harness AI coding agent (DeepSeek model), not an author.
3. ✅ Compiled and checked: exactly 4 pages, 1 figure, 4 tables, 14 references, no overfull boxes.
4. ✅ Keywords trimmed to the required five; repository URL added to the reproducibility paragraph.
5. ✅ ORCID iD registered: 0009-0001-1366-8144. Remaining external step: submit through the
   IEEE Author Portal (traditional, free publication); portal copy-paste fields are in
   `paper/submission/AUTHOR-INFO.md`.
6. ⏳ After acceptance: video graphical abstract is required at the minor-revision stage.
