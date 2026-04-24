"""Auto-rate benchmark/manual_eval.csv with Gemini + RAG context.

Usage:
    python -m benchmark.rag_auto_rate_manual_eval
    python -m benchmark.rag_auto_rate_manual_eval --overwrite
    python -m benchmark.rag_auto_rate_manual_eval --input benchmark/manual_eval.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from hsc_edu.generation.llm_client import generate_text
from hsc_edu.storage.retrieval import retrieve_chunks

load_dotenv()

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUT_PATH = PROJECT_ROOT / "benchmark" / "manual_eval.csv"

ALLOWED_RATINGS = {"dung", "chua tot", "sai"}


def _normalize_rating(raw: str) -> str:
    value = (raw or "").strip().lower()
    if value == "đúng":
        return "dung"
    if value == "chưa tốt":
        return "chua tot"
    return value


def _build_context_text(question: str, subject: str, chapter: str, top_k: int) -> str:
    retrieved = retrieve_chunks(
        question,
        subject=(subject or "").strip(),
        top_k=top_k,
    )
    if not retrieved:
        return "Khong tim thay chunk nao tu he thong RAG."

    lines: list[str] = []
    for idx, (chunk, score) in enumerate(retrieved, 1):
        section_path = " > ".join(chunk.section_path) if chunk.section_path else ""
        lines.append(f"[Chunk {idx}] score={score:.4f}")
        lines.append(f"subject={chunk.subject}")
        lines.append(f"chapter={chunk.chapter}")
        lines.append(f"section_path={section_path}")
        lines.append(f"text={chunk.text.strip()}")
        lines.append("")

    if chapter:
        lines.append(f"Chapter mong doi (tu CSV): {chapter}")
    return "\n".join(lines).strip()


def _build_prompts(row: dict[str, str], context_text: str) -> tuple[str, str]:
    system_prompt = (
        "Ban la giao vien danh gia chat luong cau hoi va dap an tham khao. "
        "Ban bat buoc tra ve JSON hop le voi 2 truong: "
        '{"rating":"dung|chua tot|sai","reason":"..."}'
    )

    user_prompt = f"""
Hay danh gia muc do dung cua cap (question, suggested_answer) dua tren context RAG.

Quy tac rating:
- dung: dung voi noi dung tai lieu, cau tra loi chinh xac va day du co ban.
- chua tot: co y dung mot phan nhung thieu/chua ro/chua chuan hoan toan.
- sai: sai kien thuc, sai ban chat, hoac khong duoc context ho tro.

Bat buoc:
- Chi duoc chon mot trong 3 nhan: dung, chua tot, sai.
- Neu context RAG khong du de ket luan chac chan, uu tien "chua tot" thay vi "dung".
- Khong duoc tra them ky tu ngoai JSON.

Thong tin mau:
subject: {row.get("subject", "")}
chapter: {row.get("chapter", "")}
difficulty: {row.get("difficulty", "")}
bloom_level: {row.get("bloom_level", "")}
question: {row.get("question", "")}
suggested_answer: {row.get("suggested_answer", "")}
source: {row.get("source", "")}

Context RAG (Qdrant + MongoDB):
{context_text}
""".strip()

    return system_prompt, user_prompt


def _parse_model_response(text: str) -> tuple[str, str]:
    raw = (text or "").strip()
    if not raw:
        return "chua tot", "Model tra ve rong."

    try:
        data = json.loads(raw)
        rating = _normalize_rating(str(data.get("rating", "")))
        reason = str(data.get("reason", "")).strip()
    except Exception:
        rating = _normalize_rating(raw)
        reason = "Model khong tra ve JSON dung dinh dang."

    if rating not in ALLOWED_RATINGS:
        return "chua tot", f"Nhan khong hop le tu model: {rating or '<empty>'}"
    return rating, reason


def _read_rows(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fields = list(reader.fieldnames or [])
    return rows, fields


def _write_rows(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _extract_retry_after_seconds(error_message: str) -> float | None:
    """Try parse retry delay from Gemini error text, e.g. 'Please retry in 51.1s'."""
    if not error_message:
        return None
    match = re.search(r"retry in\s+([0-9]+(?:\.[0-9]+)?)s", error_message, flags=re.IGNORECASE)
    if not match:
        return None
    try:
        return float(match.group(1))
    except ValueError:
        return None


def _classify_error(error_message: str) -> str:
    msg = (error_message or "").lower()
    if "429" in msg or "resource_exhausted" in msg or "quota" in msg or "rate" in msg:
        return "rate_limit"
    if "503" in msg or "unavailable" in msg:
        return "unavailable"
    return "other"


def _call_model_with_retry(
    system_prompt: str,
    user_prompt: str,
    *,
    llm_max_attempts: int,
    retry_base_sec: float,
    retry_max_sec: float,
) -> tuple[str, str]:
    """Call Gemini with resilient retry and adaptive backoff."""
    last_error = ""
    for attempt in range(1, llm_max_attempts + 1):
        try:
            raw = generate_text(
                system_prompt,
                user_prompt,
                json_output=True,
                max_retries=1,  # manage retries in this script for predictable pacing
            )
            return _parse_model_response(raw)
        except Exception as exc:
            last_error = str(exc)
            kind = _classify_error(last_error)
            if attempt >= llm_max_attempts:
                break

            parsed_retry = _extract_retry_after_seconds(last_error)
            if parsed_retry is not None:
                wait_sec = min(retry_max_sec, max(retry_base_sec, parsed_retry + 1.0))
            elif kind == "rate_limit":
                wait_sec = min(retry_max_sec, retry_base_sec * (2 ** (attempt - 1)))
            elif kind == "unavailable":
                wait_sec = min(retry_max_sec, max(2.0, retry_base_sec * attempt))
            else:
                wait_sec = min(retry_max_sec, max(1.0, retry_base_sec * attempt))

            print(
                f"  -> retry llm ({attempt}/{llm_max_attempts - 1}) "
                f"after {wait_sec:.1f}s because: {last_error[:160]}"
            )
            time.sleep(wait_sec)

    return "chua tot", f"LLM failed after retries: {last_error[:300]}"


def _write_rows_with_retry(
    path: Path,
    rows: list[dict[str, str]],
    fieldnames: list[str],
    *,
    attempts: int = 3,
    delay_sec: float = 1.5,
) -> None:
    last_exc: Exception | None = None
    for i in range(1, attempts + 1):
        try:
            _write_rows(path, rows, fieldnames)
            return
        except PermissionError as exc:
            last_exc = exc
            if i == attempts:
                break
            wait = delay_sec * i
            print(f"  -> file locked, retry write in {wait:.1f}s (attempt {i}/{attempts})")
            time.sleep(wait)
    if last_exc is not None:
        raise last_exc


def auto_rate_csv(
    input_path: Path,
    *,
    top_k: int = 5,
    overwrite: bool = False,
    delay_sec: float = 0.3,
    llm_max_attempts: int = 4,
    retry_base_sec: float = 6.0,
    retry_max_sec: float = 90.0,
    save_every: int = 1,
    write_attempts: int = 5,
) -> dict[str, Any]:
    rows, fieldnames = _read_rows(input_path)
    if not rows:
        return {"total": 0, "updated": 0, "skipped_existing": 0}

    if "rating" not in fieldnames:
        fieldnames.append("rating")
        for row in rows:
            row["rating"] = ""

    updated = 0
    skipped_existing = 0
    errors = 0

    for idx, row in enumerate(rows, 1):
        current_rating = _normalize_rating(row.get("rating", ""))
        if current_rating in ALLOWED_RATINGS and not overwrite:
            skipped_existing += 1
            continue

        question = (row.get("question") or "").strip()
        subject = (row.get("subject") or "").strip()
        chapter = (row.get("chapter") or "").strip()
        if not question:
            row["rating"] = "chua tot"
            errors += 1
            continue

        print(f"[{idx}/{len(rows)}] Rating question: {question[:70]}...")
        try:
            context_text = _build_context_text(question, subject, chapter, top_k=top_k)
            system_prompt, user_prompt = _build_prompts(row, context_text)
            rating, reason = _call_model_with_retry(
                system_prompt,
                user_prompt,
                llm_max_attempts=llm_max_attempts,
                retry_base_sec=retry_base_sec,
                retry_max_sec=retry_max_sec,
            )
            row["rating"] = rating
            updated += 1
            print(f"  -> rating={rating} | reason={reason[:80]}")
        except Exception as exc:
            row["rating"] = "chua tot"
            errors += 1
            print(f"  -> ERROR: {exc}")

        # Persist progress frequently to avoid losing evaluated rows.
        if save_every > 0 and (idx % save_every == 0):
            try:
                _write_rows_with_retry(
                    input_path,
                    rows,
                    fieldnames,
                    attempts=write_attempts,
                )
            except PermissionError:
                fallback = input_path.with_name(f"{input_path.stem}_autosave{input_path.suffix}")
                _write_rows_with_retry(
                    fallback,
                    rows,
                    fieldnames,
                    attempts=write_attempts,
                )
                print(f"  -> cannot write input file, autosaved progress to: {fallback}")

        if delay_sec > 0:
            time.sleep(delay_sec)

    try:
        _write_rows_with_retry(
            input_path,
            rows,
            fieldnames,
            attempts=write_attempts,
        )
    except PermissionError:
        fallback = input_path.with_name(f"{input_path.stem}_rated{input_path.suffix}")
        _write_rows_with_retry(
            fallback,
            rows,
            fieldnames,
            attempts=write_attempts,
        )
        print(f"Cannot write to input file. Saved final result to: {fallback}")
        input_path = fallback

    return {
        "total": len(rows),
        "updated": updated,
        "skipped_existing": skipped_existing,
        "errors": errors,
        "path": str(input_path),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT_PATH,
        help="Path to manual_eval.csv",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Top-k chunks retrieve from RAG for each row",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing ratings",
    )
    parser.add_argument(
        "--delay-sec",
        type=float,
        default=2.0,
        help="Delay between requests to reduce burst traffic",
    )
    parser.add_argument(
        "--llm-max-attempts",
        type=int,
        default=4,
        help="Max attempts per row for Gemini call",
    )
    parser.add_argument(
        "--retry-base-sec",
        type=float,
        default=6.0,
        help="Base wait seconds for retry backoff",
    )
    parser.add_argument(
        "--retry-max-sec",
        type=float,
        default=90.0,
        help="Max wait seconds for retry backoff",
    )
    parser.add_argument(
        "--save-every",
        type=int,
        default=1,
        help="Save progress every N rows (1 = save each row)",
    )
    parser.add_argument(
        "--write-attempts",
        type=int,
        default=5,
        help="Retry attempts when writing CSV file",
    )
    args = parser.parse_args()

    input_path = args.input
    if not input_path.is_absolute():
        input_path = PROJECT_ROOT / input_path
    input_path = input_path.resolve()

    if not input_path.exists():
        raise FileNotFoundError(f"Not found: {input_path}")

    result = auto_rate_csv(
        input_path,
        top_k=args.top_k,
        overwrite=args.overwrite,
        delay_sec=args.delay_sec,
        llm_max_attempts=args.llm_max_attempts,
        retry_base_sec=args.retry_base_sec,
        retry_max_sec=args.retry_max_sec,
        save_every=args.save_every,
        write_attempts=args.write_attempts,
    )

    print("\nDone.")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

