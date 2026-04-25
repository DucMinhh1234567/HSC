# Benchmark — Danh gia pipeline HSC-Edu

Bo cong cu cham diem **7 con so** duoc dinh nghia trong [`metric.md`](metric.md).

## Cau truc folder

```
benchmark/
├── metric.md                     # Dinh nghia 7 tieu chi
├── ground_truth.json             # 20 cau hoi de cham Hit@1 / Hit@3 (10 Java + 10 C)
├── tier1_chunking.py             # Tang 1 — Chunking (auto)
├── tier2_retrieval.py            # Tang 2 — Retrieval (auto, goi Qdrant + Gemini)
├── tier3_generation.py           # Tang 3 — Generation (auto + manual template)
├── run_benchmark.py              # Orchestrator — chay ca 3 tier, sinh report.md
├── manual_eval_template.csv      # (tu dong sinh) template cham tay factual accuracy
├── manual_eval.csv               # (ban tu tao) file cham tay sau khi dien rating
└── results/
    ├── tier1_chunking.json
    ├── tier2_retrieval.json
    ├── tier2_retrieval_details.csv
    ├── tier3_generation.json
    └── report.md                 # Bao cao tong hop 7 con so
```

## Yeu cau truoc khi chay

1. **MongoDB + Qdrant da co data** — chay notebook `03_retrieval_demo.ipynb`
   truoc de ingest PDF vao MongoDB + Qdrant.
2. **File `.env` da co** `GOOGLE_API_KEY`, `QDRANT_URL`, `QDRANT_API_KEY`,
   `MONGO_URI` (xem `README.md` cua project).
3. **Cau hoi da sinh** — chay notebook `04_generation_demo.ipynb` de
   tao `data/questions/generated_questions.json`.

## Chay tu dong ca 3 tier

```powershell
python -m benchmark.run_benchmark
```

Ket qua -> `benchmark/results/report.md`.

### Chay tung tier rieng le

```powershell
python -m benchmark.tier1_chunking        # khong goi API
python -m benchmark.tier2_retrieval       # goi Qdrant + Gemini embedding (~18 lan)
python -m benchmark.tier3_generation      # khong goi API
```

### Bo qua Tier 2 khi tiet kiem quota

```powershell
python -m benchmark.run_benchmark --skip-retrieval
```

## Cach cham factual accuracy thu cong (Tieu chi #6)

1. Chay Tier 3 de sinh file mau 20 cau:

   ```powershell
   python -m benchmark.tier3_generation
   ```

2. Mo `benchmark/manual_eval_template.csv`, **luu lai** thanh
   `benchmark/manual_eval.csv`.
3. Dien cot `rating` cho moi cau, gia tri hop le:

   | Gia tri        | Diem |
   |----------------|------|
   | `dung` / `đúng`    | 1.0  |
   | `chua tot` / `chưa tốt` | 0.5  |
   | `sai`          | 0.0  |

4. Chay lai:

   ```powershell
   python -m benchmark.tier3_generation
   # hoac
   python -m benchmark.run_benchmark
   ```

Factual accuracy se tu dong duoc tinh va xuat vao `report.md`.

## 7 con so trong bao cao

| # | Tieu chi | Ngon | Tu dong? |
|---|---|---|:-:|
| 1 | Tong chunks + avg tokens/chunk | Tier 1 | ✓ |
| 2 | Short chunk ratio (<64 tok) | Tier 1 | ✓ |
| 3 | Chapter coverage % | Tier 1 | ✓ |
| 4 | Hit@1 (retrieval) | Tier 2 | ✓ |
| 5 | Hit@3 (retrieval) | Tier 2 | ✓ |
| 6 | Factual accuracy % | Tier 3 | Thu cong (~20 cau) |
| 7 | Parse success rate + difficulty distribution | Tier 3 | ✓ |

## Dinh dang `ground_truth.json`

```json
{
  "questions": [
    {
      "id": "java-02",
      "subject": "Lập trình Java",
      "question": "Bốn nguyên tắc trụ cột của lập trình hướng đối tượng là gì?",
      "expected_chapter_patterns": ["1.3", "NGUYÊN TẮC TRỤ CỘT"],
      "keywords": ["đóng gói", "thừa kế", "đa hình", "trừu tượng"]
    }
  ]
}
```

- `expected_chapter_patterns`: mot trong cac substring ma ta ky vong
  tim thay trong `chunk.chapter` hoac `chunk.section_path` cua top-k
  retrieval. **Match case-insensitive.** Chi can mot pattern trung la
  tinh Hit.
- `keywords`: tham khao — hien chua dung trong Hit@k nhung de san cho
  nguoi cham tay hoac dung lam fallback sau nay.

Them / sua cau hoi: chi can edit `benchmark/ground_truth.json` va chay
lai `python -m benchmark.tier2_retrieval`.
