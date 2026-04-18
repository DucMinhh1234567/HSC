"""Tier 3 — Generation metrics (auto + manual template).

Cac con so output:
    6. Factual accuracy %   (tu danh gia ~20 cau — can dien vao CSV)
    7. Parse success rate + difficulty distribution

Input:
    data/questions/generated_questions.json   (mac dinh)
    benchmark/manual_eval.csv                 (tuy chon — dien thu cong)

Output:
    benchmark/results/tier3_generation.json
    benchmark/manual_eval_template.csv        (20 cau lay mau de cham tay)

Cach cham factual accuracy:
    Mo benchmark/manual_eval_template.csv, copy sang file ten
    `manual_eval.csv`, dien cot `rating` voi cac gia tri:
        - "dung"     (1.0)
        - "chua tot" (0.5)
        - "sai"      (0.0)
    Chay lai script de cap nhat tier3_generation.json.
"""

from __future__ import annotations

import csv
import json
import random
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv()

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
QUESTIONS_PATH = PROJECT_ROOT / "data" / "questions" / "generated_questions.json"

RESULTS_DIR = Path(__file__).parent / "results"
RESULTS_PATH = RESULTS_DIR / "tier3_generation.json"
MANUAL_TEMPLATE_PATH = Path(__file__).parent / "manual_eval_template.csv"
MANUAL_EVAL_PATH = Path(__file__).parent / "manual_eval.csv"

SAMPLE_SIZE = 20
RATING_MAP = {
    "dung": 1.0,
    "đúng": 1.0,
    "correct": 1.0,
    "chua tot": 0.5,
    "chưa tốt": 0.5,
    "partial": 0.5,
    "sai": 0.0,
    "wrong": 0.0,
}


REQUIRED_FIELDS = ("question", "suggested_answer", "difficulty", "source", "chapter")


def _is_valid_question(item: dict[str, Any]) -> bool:
    for f in REQUIRED_FIELDS:
        v = item.get(f, "")
        if not isinstance(v, str) or not v.strip():
            return False
    return True


def _load_questions(path: Path = QUESTIONS_PATH) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def _write_manual_template(samples: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "idx", "subject", "chapter", "difficulty", "bloom_level",
            "question", "suggested_answer", "source",
            "rating",
        ])
        for i, q in enumerate(samples, 1):
            writer.writerow([
                i,
                q.get("subject", ""),
                q.get("chapter", ""),
                q.get("difficulty", ""),
                q.get("bloom_level", ""),
                q.get("question", ""),
                q.get("suggested_answer", ""),
                q.get("source", ""),
                "",
            ])


def _load_manual_eval(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _compute_factual_accuracy(rows: list[dict[str, Any]]) -> dict[str, Any]:
    scores: list[float] = []
    per_bucket: Counter[str] = Counter()
    for row in rows:
        raw = (row.get("rating") or "").strip().lower()
        if not raw:
            continue
        score = RATING_MAP.get(raw)
        if score is None:
            per_bucket["unknown"] += 1
            continue
        scores.append(score)
        if score == 1.0:
            per_bucket["dung"] += 1
        elif score == 0.5:
            per_bucket["chua_tot"] += 1
        else:
            per_bucket["sai"] += 1

    if not scores:
        return {
            "status": "no_manual_ratings",
            "rated": 0,
            "total_in_csv": len(rows),
            "breakdown": dict(per_bucket),
        }

    return {
        "status": "ok",
        "rated": len(scores),
        "total_in_csv": len(rows),
        "breakdown": dict(per_bucket),
        "factual_accuracy_pct": round(100 * sum(scores) / len(scores), 2),
        "strict_correct_pct": round(
            100 * per_bucket["dung"] / len(scores), 2
        ),
    }


def compute_tier3_metrics(
    *,
    sample_size: int = SAMPLE_SIZE,
    seed: int = 42,
) -> dict[str, Any]:
    questions = _load_questions()
    total = len(questions)

    if total == 0:
        return {
            "total_questions": 0,
            "error": f"Not found: {QUESTIONS_PATH}",
        }

    valid = [q for q in questions if _is_valid_question(q)]
    parse_success = len(valid)

    difficulty_dist = Counter(q.get("difficulty", "") for q in valid)
    bloom_dist = Counter(q.get("bloom_level", "") for q in valid)
    subject_dist = Counter(q.get("subject", "") for q in valid)

    rng = random.Random(seed)
    sample = rng.sample(valid, min(sample_size, len(valid)))
    _write_manual_template(sample, MANUAL_TEMPLATE_PATH)

    rated_rows = _load_manual_eval(MANUAL_EVAL_PATH)
    factual = _compute_factual_accuracy(rated_rows)

    return {
        "total_questions": total,
        "parse_success": {
            "count": parse_success,
            "pct": round(100 * parse_success / total, 2),
        },
        "difficulty_distribution": dict(difficulty_dist),
        "bloom_level_distribution": dict(bloom_dist),
        "subject_distribution": dict(subject_dist),
        "manual_eval": {
            "template_path": str(MANUAL_TEMPLATE_PATH),
            "rated_path": str(MANUAL_EVAL_PATH),
            "sample_size": len(sample),
            "factual_accuracy": factual,
        },
    }


def _print_report(metrics: dict[str, Any]) -> None:
    print("=" * 70)
    print("TIER 3 — GENERATION METRICS")
    print("=" * 70)
    if metrics.get("error"):
        print("ERROR:", metrics["error"])
        return

    total = metrics["total_questions"]
    ps = metrics["parse_success"]
    print(f"Total generated questions : {total}")
    print(f"Parse success             : {ps['count']}/{total} = {ps['pct']}%")

    print("\nDifficulty distribution:")
    for k, v in metrics["difficulty_distribution"].items():
        print(f"  - {k or '<empty>':15s} {v}")

    print("\nBloom level distribution:")
    for k, v in metrics["bloom_level_distribution"].items():
        print(f"  - {k or '<empty>':15s} {v}")

    print("\nPer subject:")
    for k, v in metrics["subject_distribution"].items():
        print(f"  - {k:25s} {v}")

    me = metrics["manual_eval"]
    print(f"\nManual eval template      : {me['template_path']}")
    print(f"Manual eval input (fill!) : {me['rated_path']}")
    fa = me["factual_accuracy"]
    if fa.get("status") == "ok":
        print(f"Factual accuracy          : {fa['factual_accuracy_pct']}%  "
              f"(strict Đúng: {fa['strict_correct_pct']}%)  "
              f"[{fa['rated']} cau da cham]")
        print(f"  Breakdown               : {fa['breakdown']}")
    else:
        print("Factual accuracy          : <chua co rating> "
              f"({fa['total_in_csv']} rows in CSV)")
        print(f"  -> Mo {MANUAL_TEMPLATE_PATH.name}, luu lai thanh "
              f"{MANUAL_EVAL_PATH.name} va dien cot 'rating'.")


def main() -> None:
    metrics = compute_tier3_metrics()
    _print_report(metrics)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_PATH.write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\nSaved -> {RESULTS_PATH}")


if __name__ == "__main__":
    main()
