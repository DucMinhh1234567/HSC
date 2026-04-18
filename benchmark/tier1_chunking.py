"""Tier 1 — Chunking metrics (tu dong, khong can ground truth).

Cac con so output:
    1. total_chunks
    2. avg_tokens_per_chunk (+ median / min / max / p25 / p75)
    3. short_chunk_ratio  (chunks co token_count < 64)
    4. chapter_coverage_pct  (chunks co chapter khac rong / total)

Chay:
    python -m benchmark.tier1_chunking
Output:
    benchmark/results/tier1_chunking.json
"""

from __future__ import annotations

import json
import statistics
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv()

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

from hsc_edu.storage.mongo_store import MongoChunkStore

SHORT_TOKEN_THRESHOLD = 64

RESULTS_DIR = Path(__file__).parent / "results"
RESULTS_PATH = RESULTS_DIR / "tier1_chunking.json"


def _quantile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    pos = (len(s) - 1) * q
    lo = int(pos)
    hi = min(lo + 1, len(s) - 1)
    frac = pos - lo
    return s[lo] * (1 - frac) + s[hi] * frac


def compute_tier1_metrics(subject: str = "") -> dict[str, Any]:
    """Tinh metrics Tier 1 tu chunks da luu trong MongoDB.

    Parameters
    ----------
    subject:
        Loc theo subject (vd ``"Lập trình Java"``). Empty = tat ca.
    """
    mongo = MongoChunkStore()
    chunks = mongo.get_chunks_by_filter(subject=subject)

    if not chunks:
        return {
            "subject": subject or "<all>",
            "total_chunks": 0,
            "error": "No chunks found in MongoDB",
        }

    tokens = [c.token_count for c in chunks]
    total = len(chunks)

    short_count = sum(1 for t in tokens if t < SHORT_TOKEN_THRESHOLD)
    with_chapter = sum(1 for c in chunks if (c.chapter or "").strip())

    by_subject = Counter(c.subject for c in chunks)
    by_chapter = Counter(c.chapter for c in chunks if c.chapter)

    metrics: dict[str, Any] = {
        "subject": subject or "<all>",
        "total_chunks": total,
        "tokens": {
            "avg": round(statistics.fmean(tokens), 2),
            "median": int(statistics.median(tokens)),
            "min": min(tokens),
            "max": max(tokens),
            "p25": round(_quantile(tokens, 0.25), 2),
            "p75": round(_quantile(tokens, 0.75), 2),
        },
        "short_chunk_ratio": {
            "threshold": SHORT_TOKEN_THRESHOLD,
            "count": short_count,
            "pct": round(100 * short_count / total, 2),
        },
        "chapter_coverage": {
            "chunks_with_chapter": with_chapter,
            "total": total,
            "pct": round(100 * with_chapter / total, 2),
            "unique_chapters": len(by_chapter),
        },
        "chunks_by_subject": dict(by_subject),
        "top_chapters_by_chunk_count": by_chapter.most_common(10),
    }
    return metrics


def _print_report(metrics: dict[str, Any]) -> None:
    print("=" * 70)
    print(f"TIER 1 — CHUNKING METRICS  (subject={metrics.get('subject')})")
    print("=" * 70)
    if metrics.get("error"):
        print("ERROR:", metrics["error"])
        return

    total = metrics["total_chunks"]
    tok = metrics["tokens"]
    short = metrics["short_chunk_ratio"]
    cov = metrics["chapter_coverage"]

    print(f"Total chunks            : {total}")
    print(f"Avg tokens/chunk        : {tok['avg']}")
    print(f"  median / min / max    : {tok['median']} / {tok['min']} / {tok['max']}")
    print(f"  p25 / p75             : {tok['p25']} / {tok['p75']}")
    print(f"Short chunks (<{short['threshold']} tok) : "
          f"{short['count']}/{total} = {short['pct']}%")
    print(f"Chapter coverage        : "
          f"{cov['chunks_with_chapter']}/{cov['total']} = {cov['pct']}%  "
          f"({cov['unique_chapters']} unique chapters)")

    print("\nChunks per subject:")
    for sub, cnt in metrics["chunks_by_subject"].items():
        print(f"  - {sub:25s} {cnt}")

    print("\nTop 10 chapters by chunk count:")
    for ch, cnt in metrics["top_chapters_by_chunk_count"]:
        print(f"  - [{cnt:3d}] {ch}")


def main() -> None:
    metrics = compute_tier1_metrics()
    _print_report(metrics)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_PATH.write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\nSaved -> {RESULTS_PATH}")


if __name__ == "__main__":
    main()
