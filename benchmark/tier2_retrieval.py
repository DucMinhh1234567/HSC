"""Tier 2 — Retrieval metrics.

Cac con so output:
    4. Hit@1  (%)
    5. Hit@3  (%)
    + avg_top1_cosine

Cach cham Hit@k: mot query duoc tinh la hit neu trong top-k chunk tra ve,
co it nhat mot chunk thoa man `_chunk_matches_expected`:
    - chunk.chapter hoac bat ky heading trong chunk.section_path
      chua mot trong cac `expected_chapter_patterns` (case-insensitive).

Chay:
    python -m benchmark.tier2_retrieval
Output:
    benchmark/results/tier2_retrieval.json
    benchmark/results/tier2_retrieval_details.csv
"""

from __future__ import annotations

import csv
import json
import logging
import sys
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.WARNING, format="%(levelname)s | %(name)s | %(message)s")

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

from hsc_edu.core.models import Chunk
from hsc_edu.storage.retrieval import retrieve_chunks

GROUND_TRUTH_PATH = Path(__file__).parent / "ground_truth.json"
RESULTS_DIR = Path(__file__).parent / "results"
RESULTS_JSON = RESULTS_DIR / "tier2_retrieval.json"
RESULTS_CSV = RESULTS_DIR / "tier2_retrieval_details.csv"

TOP_K = 3
REQUEST_DELAY_SEC = 0.5


def _normalize(text: str) -> str:
    return (text or "").strip().lower()


def _chunk_matches_expected(chunk: Chunk, patterns: list[str]) -> bool:
    """Chunk is a hit if chapter or any section_path entry contains any pattern."""
    haystacks = [_normalize(chunk.chapter)] + [_normalize(p) for p in chunk.section_path]
    for pat in patterns:
        p = _normalize(pat)
        if not p:
            continue
        if any(p in h for h in haystacks if h):
            return True
    return False


def _load_questions() -> list[dict[str, Any]]:
    data = json.loads(GROUND_TRUTH_PATH.read_text(encoding="utf-8"))
    return data["questions"]


def evaluate_retrieval(
    *,
    top_k: int = TOP_K,
    delay_sec: float = REQUEST_DELAY_SEC,
) -> dict[str, Any]:
    questions = _load_questions()

    per_query: list[dict[str, Any]] = []
    hits_at_1 = 0
    hits_at_3 = 0
    top1_scores: list[float] = []

    for idx, q in enumerate(questions, 1):
        question = q["question"]
        subject = q.get("subject", "")
        patterns: list[str] = q.get("expected_chapter_patterns", [])

        print(f"[{idx}/{len(questions)}] ({subject}) {question[:70]}...")

        try:
            results = retrieve_chunks(question, subject=subject, top_k=top_k)
        except Exception as exc:
            print(f"  ERROR: {exc}")
            per_query.append({
                "id": q.get("id"),
                "subject": subject,
                "question": question,
                "error": str(exc),
            })
            continue

        matches = [_chunk_matches_expected(ch, patterns) for ch, _ in results]
        hit_at_1 = bool(matches[:1] and matches[0])
        hit_at_3 = any(matches[:3])

        top1_chunk, top1_score = (results[0] if results else (None, 0.0))

        if hit_at_1:
            hits_at_1 += 1
        if hit_at_3:
            hits_at_3 += 1
        top1_scores.append(float(top1_score))

        detail = {
            "id": q.get("id"),
            "subject": subject,
            "question": question,
            "expected_chapter_patterns": patterns,
            "hit@1": hit_at_1,
            "hit@3": hit_at_3,
            "top1_score": round(float(top1_score), 4),
            "top1_chapter": top1_chunk.chapter if top1_chunk else "",
            "top1_section_path": (top1_chunk.section_path if top1_chunk else []),
            "retrieved": [
                {
                    "rank": i + 1,
                    "score": round(float(s), 4),
                    "chapter": ch.chapter,
                    "section_path": ch.section_path,
                    "match": matches[i],
                }
                for i, (ch, s) in enumerate(results)
            ],
        }
        per_query.append(detail)
        status = "HIT@1" if hit_at_1 else ("HIT@3" if hit_at_3 else "MISS ")
        print(f"  -> {status}  top1_score={top1_score:.4f}  "
              f"chapter='{top1_chunk.chapter if top1_chunk else '-'}'")
        time.sleep(delay_sec)

    n = len(questions)
    summary = {
        "top_k": top_k,
        "num_questions": n,
        "hit@1": {"count": hits_at_1, "pct": round(100 * hits_at_1 / n, 2) if n else 0.0},
        "hit@3": {"count": hits_at_3, "pct": round(100 * hits_at_3 / n, 2) if n else 0.0},
        "avg_top1_cosine": round(sum(top1_scores) / len(top1_scores), 4) if top1_scores else 0.0,
        "per_query": per_query,
    }
    return summary


def _print_report(summary: dict[str, Any]) -> None:
    n = summary["num_questions"]
    h1 = summary["hit@1"]
    h3 = summary["hit@3"]
    print("\n" + "=" * 70)
    print("TIER 2 — RETRIEVAL METRICS")
    print("=" * 70)
    print(f"Num questions        : {n}")
    print(f"Hit@1                : {h1['count']}/{n} = {h1['pct']}%")
    print(f"Hit@3                : {h3['count']}/{n} = {h3['pct']}%")
    print(f"Avg cosine of top-1  : {summary['avg_top1_cosine']}")


def _write_csv(summary: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "id", "subject", "question",
            "hit@1", "hit@3", "top1_score",
            "top1_chapter", "top1_section_path",
            "expected_patterns",
        ])
        for item in summary["per_query"]:
            if item.get("error"):
                writer.writerow([
                    item.get("id"), item.get("subject"), item.get("question"),
                    "ERROR", "ERROR", "",
                    "", "", " | ".join(item.get("expected_chapter_patterns", [])),
                ])
                continue
            writer.writerow([
                item.get("id"),
                item.get("subject"),
                item.get("question"),
                int(item.get("hit@1", False)),
                int(item.get("hit@3", False)),
                item.get("top1_score", ""),
                item.get("top1_chapter", ""),
                " > ".join(item.get("top1_section_path", [])),
                " | ".join(item.get("expected_chapter_patterns", [])),
            ])


def main() -> None:
    summary = evaluate_retrieval()
    _print_report(summary)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_JSON.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    _write_csv(summary, RESULTS_CSV)
    print(f"\nSaved -> {RESULTS_JSON}")
    print(f"Saved -> {RESULTS_CSV}")


if __name__ == "__main__":
    main()
