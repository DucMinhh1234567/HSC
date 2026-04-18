"""Orchestrator — chay ca 3 tier va ghi report tong hop.

Sinh ra:
    benchmark/results/tier1_chunking.json
    benchmark/results/tier2_retrieval.json
    benchmark/results/tier2_retrieval_details.csv
    benchmark/results/tier3_generation.json
    benchmark/results/report.md

Chay:
    python -m benchmark.run_benchmark
    python -m benchmark.run_benchmark --skip-retrieval     # bo qua Tier 2 (goi API)
    python -m benchmark.run_benchmark --only tier1         # chi chay tier1
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv()

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

from benchmark.tier1_chunking import compute_tier1_metrics
from benchmark.tier2_retrieval import evaluate_retrieval
from benchmark.tier3_generation import compute_tier3_metrics

RESULTS_DIR = Path(__file__).parent / "results"
REPORT_PATH = RESULTS_DIR / "report.md"


def _fmt_pct(value: float) -> str:
    return f"{value:.2f}%"


def _md_report(
    tier1: dict[str, Any] | None,
    tier2: dict[str, Any] | None,
    tier3: dict[str, Any] | None,
) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines: list[str] = []
    lines.append("# HSC-Edu — Benchmark Report")
    lines.append("")
    lines.append(f"_Generated: {now}_")
    lines.append("")
    lines.append("Bo 7 con so theo `benchmark/metric.md`:")
    lines.append("")

    # ----- Tier 1 -----
    lines.append("## Tang 1 — Chunking")
    lines.append("")
    if tier1 is None:
        lines.append("_(skipped)_")
    elif tier1.get("error"):
        lines.append(f"Error: {tier1['error']}")
    else:
        tok = tier1["tokens"]
        short = tier1["short_chunk_ratio"]
        cov = tier1["chapter_coverage"]
        lines.append(f"- **(1) Total chunks**: `{tier1['total_chunks']}`")
        lines.append(
            f"- **(1) Avg tokens/chunk**: `{tok['avg']}` "
            f"(median `{tok['median']}`, min `{tok['min']}`, max `{tok['max']}`, "
            f"p25 `{tok['p25']}`, p75 `{tok['p75']}`)"
        )
        lines.append(
            f"- **(2) Short chunk ratio (<{short['threshold']} tok)**: "
            f"`{short['count']}/{tier1['total_chunks']}` = **{_fmt_pct(short['pct'])}**"
        )
        lines.append(
            f"- **(3) Chapter coverage**: "
            f"`{cov['chunks_with_chapter']}/{cov['total']}` = **{_fmt_pct(cov['pct'])}** "
            f"({cov['unique_chapters']} unique chapters)"
        )
        lines.append("")
        lines.append("**Chunks per subject**:")
        for sub, cnt in tier1["chunks_by_subject"].items():
            lines.append(f"  - {sub}: `{cnt}`")
    lines.append("")

    # ----- Tier 2 -----
    lines.append("## Tang 2 — Retrieval")
    lines.append("")
    if tier2 is None:
        lines.append("_(skipped)_")
    else:
        n = tier2["num_questions"]
        h1 = tier2["hit@1"]
        h3 = tier2["hit@3"]
        lines.append(f"- Num questions: `{n}`  (top_k = `{tier2['top_k']}`)")
        lines.append(
            f"- **(4) Hit@1**: `{h1['count']}/{n}` = **{_fmt_pct(h1['pct'])}**"
        )
        lines.append(
            f"- **(5) Hit@3**: `{h3['count']}/{n}` = **{_fmt_pct(h3['pct'])}**"
        )
        lines.append(f"- Avg cosine of top-1: `{tier2['avg_top1_cosine']}`")
        lines.append("")
        lines.append("**Per-query**:")
        lines.append("")
        lines.append("| id | subject | hit@1 | hit@3 | top1_score | top1_chapter |")
        lines.append("|---|---|:-:|:-:|--:|---|")
        for item in tier2["per_query"]:
            if item.get("error"):
                lines.append(
                    f"| {item.get('id')} | {item.get('subject')} | "
                    f"ERROR | ERROR | - | {item.get('error')} |"
                )
                continue
            lines.append(
                f"| {item.get('id')} | {item.get('subject')} | "
                f"{'Y' if item.get('hit@1') else '-'} | "
                f"{'Y' if item.get('hit@3') else '-'} | "
                f"{item.get('top1_score')} | "
                f"{item.get('top1_chapter') or '(empty)'} |"
            )
    lines.append("")

    # ----- Tier 3 -----
    lines.append("## Tang 3 — Generation")
    lines.append("")
    if tier3 is None:
        lines.append("_(skipped)_")
    elif tier3.get("error"):
        lines.append(f"Error: {tier3['error']}")
    else:
        ps = tier3["parse_success"]
        diff = tier3["difficulty_distribution"]
        lines.append(
            f"- Total generated questions: `{tier3['total_questions']}`"
        )
        lines.append(
            f"- **(7a) Parse success rate**: "
            f"`{ps['count']}/{tier3['total_questions']}` = **{_fmt_pct(ps['pct'])}**"
        )
        lines.append("- **(7b) Difficulty distribution**:")
        for k, v in diff.items():
            lines.append(f"  - `{k or '<empty>'}`: {v}")
        fa = tier3["manual_eval"]["factual_accuracy"]
        if fa.get("status") == "ok":
            lines.append(
                f"- **(6) Factual accuracy**: "
                f"**{fa['factual_accuracy_pct']}%** "
                f"(strict `Dung`: {fa['strict_correct_pct']}%, "
                f"n = {fa['rated']})"
            )
            lines.append(f"  - Breakdown: `{fa['breakdown']}`")
        else:
            lines.append(
                "- **(6) Factual accuracy**: _pending manual rating_ "
                f"(template: `benchmark/manual_eval_template.csv`; "
                f"fill and save as `benchmark/manual_eval.csv`)"
            )
    lines.append("")

    # ----- Summary -----
    lines.append("## Tom tat 7 con so")
    lines.append("")
    lines.append("| # | Metric | Value |")
    lines.append("|---|---|---|")
    if tier1 and not tier1.get("error"):
        lines.append(
            f"| 1 | Total chunks + avg tokens | "
            f"{tier1['total_chunks']} chunks, avg = {tier1['tokens']['avg']} tok |"
        )
        lines.append(
            f"| 2 | Short chunk ratio (<64 tok) | "
            f"{_fmt_pct(tier1['short_chunk_ratio']['pct'])} |"
        )
        lines.append(
            f"| 3 | Chapter coverage % | "
            f"{_fmt_pct(tier1['chapter_coverage']['pct'])} |"
        )
    if tier2:
        lines.append(
            f"| 4 | Hit@1 | {_fmt_pct(tier2['hit@1']['pct'])} |"
        )
        lines.append(
            f"| 5 | Hit@3 | {_fmt_pct(tier2['hit@3']['pct'])} |"
        )
    if tier3 and not tier3.get("error"):
        fa = tier3["manual_eval"]["factual_accuracy"]
        val6 = (
            f"{fa['factual_accuracy_pct']}%"
            if fa.get("status") == "ok" else "_pending_"
        )
        lines.append(f"| 6 | Factual accuracy | {val6} |")
        ps = tier3["parse_success"]
        lines.append(
            f"| 7 | Parse success + difficulty | "
            f"{_fmt_pct(ps['pct'])} / "
            f"{tier3['difficulty_distribution']} |"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--only",
        choices=["tier1", "tier2", "tier3"],
        default=None,
        help="Chi chay 1 tier",
    )
    parser.add_argument(
        "--skip-retrieval",
        action="store_true",
        help="Bo qua Tier 2 (tranh ton quota API)",
    )
    args = parser.parse_args()

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    tier1 = tier2 = tier3 = None

    if args.only in (None, "tier1"):
        print("\n>>> Running Tier 1 — Chunking metrics")
        tier1 = compute_tier1_metrics()
        (RESULTS_DIR / "tier1_chunking.json").write_text(
            json.dumps(tier1, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    if args.only in (None, "tier2") and not args.skip_retrieval:
        print("\n>>> Running Tier 2 — Retrieval metrics")
        tier2 = evaluate_retrieval()
        (RESULTS_DIR / "tier2_retrieval.json").write_text(
            json.dumps(tier2, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    if args.only in (None, "tier3"):
        print("\n>>> Running Tier 3 — Generation metrics")
        tier3 = compute_tier3_metrics()
        (RESULTS_DIR / "tier3_generation.json").write_text(
            json.dumps(tier3, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    report = _md_report(tier1, tier2, tier3)
    REPORT_PATH.write_text(report, encoding="utf-8")
    print(f"\n>>> Report saved -> {REPORT_PATH}")


if __name__ == "__main__":
    main()
