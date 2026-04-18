# HSC-Edu — Benchmark Report

_Generated: 2026-04-18 20:35:27_

Bo 7 con so theo `benchmark/metric.md`:

## Tang 1 — Chunking

- **(1) Total chunks**: `437`
- **(1) Avg tokens/chunk**: `568.82` (median `572`, min `31`, max `1143`, p25 `151.0`, p75 `980.0`)
- **(2) Short chunk ratio (<64 tok)**: `10/437` = **2.29%**
- **(3) Chapter coverage**: `421/437` = **96.34%** (90 unique chapters)

**Chunks per subject**:
  - Lập trình Java: `322`
  - Lập trình C: `115`

## Tang 2 — Retrieval

_(skipped)_

## Tang 3 — Generation

- Total generated questions: `26`
- **(7a) Parse success rate**: `26/26` = **100.00%**
- **(7b) Difficulty distribution**:
  - `Thông hiểu`: 14
  - `Nhận biết`: 7
  - `Vận dụng`: 4
  - `Vận dụng cao`: 1
- **(6) Factual accuracy**: _pending manual rating_ (template: `benchmark/manual_eval_template.csv`; fill and save as `benchmark/manual_eval.csv`)

## Tom tat 7 con so

| # | Metric | Value |
|---|---|---|
| 1 | Total chunks + avg tokens | 437 chunks, avg = 568.82 tok |
| 2 | Short chunk ratio (<64 tok) | 2.29% |
| 3 | Chapter coverage % | 96.34% |
| 6 | Factual accuracy | _pending_ |
| 7 | Parse success + difficulty | 100.00% / {'Thông hiểu': 14, 'Nhận biết': 7, 'Vận dụng': 4, 'Vận dụng cao': 1} |
