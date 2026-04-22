"""Simple FE prototype for upload, question generation, and source tracing."""

from __future__ import annotations

from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from hsc_edu.generation.question_generator import GeneratedQuestion, generate_questions
from hsc_edu.storage.ingest import ingest_pdf
from hsc_edu.storage.mongo_store import MongoChunkStore
from hsc_edu.storage.retrieval import retrieve_chunks


PROJECT_ROOT = Path(__file__).resolve().parents[1]
UPLOAD_DIR = PROJECT_ROOT / "data" / "uploads"

# Load both repo-level and fe-level env files.
load_dotenv(PROJECT_ROOT / ".env", override=False)
load_dotenv(Path(__file__).resolve().parent / ".env", override=False)


def _init_state() -> None:
    if "generated" not in st.session_state:
        st.session_state.generated = []


def _safe_list(values: list) -> list[str]:
    result: list[str] = []
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            result.append(text)
    return sorted(set(result))


def _chapters_for_doc(mongo: MongoChunkStore, doc_id: str) -> list[str]:
    if not doc_id:
        return []
    chunks = mongo.get_chunks_by_filter(doc_id=doc_id)
    return _safe_list([chunk.chapter for chunk in chunks])


def _subject_for_doc(mongo: MongoChunkStore, doc_id: str) -> str:
    chunks = mongo.get_chunks_by_filter(doc_id=doc_id)
    if not chunks:
        return ""
    return chunks[0].subject or ""


def _save_uploaded_pdf(uploaded_file) -> Path:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    output_path = UPLOAD_DIR / uploaded_file.name
    output_path.write_bytes(uploaded_file.getbuffer())
    return output_path


def _render_chunk_trace(mongo: MongoChunkStore, chunk_ids: list[str]) -> None:
    if not chunk_ids:
        st.info("Không có chunk_id để truy xuất.")
        return

    chunks = mongo.get_chunks_by_ids(chunk_ids)
    if not chunks:
        st.info("Không tìm thấy chunk trong MongoDB.")
        return

    for idx, chunk in enumerate(chunks, start=1):
        with st.expander(
            f"Chunk {idx}: {chunk.chunk_id} | chapter={chunk.chapter or '-'} | "
            f"page={chunk.page_start}-{chunk.page_end}",
        ):
            st.write(f"doc_id: `{chunk.doc_id}`")
            st.write(f"section: `{chunk.section or '-'}`")
            st.write(chunk.content or chunk.text)


def _render_retrieval_trace(query: str, subject: str, chapter: str, doc_id: str) -> None:
    if not query.strip():
        st.info("Nhập query để truy xuất nguồn.")
        return

    hits = retrieve_chunks(
        query=query,
        subject=subject,
        chapter=chapter,
        doc_id=doc_id,
        top_k=8,
    )
    if not hits:
        st.info("Không có kết quả retrieval.")
        return

    for rank, (chunk, score) in enumerate(hits, start=1):
        with st.expander(
            f"Top {rank} | score={score:.4f} | chunk={chunk.chunk_id}",
            expanded=(rank <= 2),
        ):
            st.write(
                f"doc_id: `{chunk.doc_id}` | chapter: `{chunk.chapter or '-'}` | "
                f"page: `{chunk.page_start}-{chunk.page_end}`",
            )
            st.write(chunk.content or chunk.text)


def _render_generation_results(mongo: MongoChunkStore, selected_doc: str, selected_chapter: str) -> None:
    generated: list[GeneratedQuestion] = st.session_state.generated
    if not generated:
        st.caption("Chưa có câu hỏi được sinh.")
        return

    st.subheader("Kết quả câu hỏi + câu trả lời đề xuất")
    for idx, item in enumerate(generated, start=1):
        with st.container(border=True):
            st.markdown(f"**{idx}. Câu hỏi**")
            st.write(item.question)
            st.markdown("**Trả lời đề xuất**")
            st.write(item.suggested_answer)
            st.caption(
                f"difficulty={item.difficulty or '-'} | bloom={item.bloom_level or '-'} | "
                f"chapter={item.chapter or '-'}",
            )

            col1, col2 = st.columns(2)
            with col1:
                if st.button("Xem chunk nguồn", key=f"chunk_{idx}"):
                    _render_chunk_trace(mongo, item.chunk_ids)
            with col2:
                if st.button("Retrieval trace (Q+A)", key=f"retr_{idx}"):
                    query = f"{item.question}\n{item.suggested_answer}"
                    subject = _subject_for_doc(mongo, selected_doc) if selected_doc else item.subject
                    _render_retrieval_trace(
                        query=query,
                        subject=subject,
                        chapter=selected_chapter or item.chapter,
                        doc_id=selected_doc,
                    )


def main() -> None:
    st.set_page_config(page_title="HSC-Edu FE", layout="wide")
    _init_state()
    mongo = MongoChunkStore()

    st.title("HSC-Edu - Basic Web")
    st.caption(
        "1) Upload tài liệu PDF | 2) Sinh câu hỏi với tùy chọn tài liệu/chương/prompt bổ sung | "
        "3) Truy xuất chunk/chapter/page từ kết quả.",
    )

    st.subheader("1) Upload tài liệu")
    with st.form("upload_form"):
        uploaded_pdf = st.file_uploader("Chọn file PDF", type=["pdf"])
        subject_input = st.text_input("Môn học", value="Lập trình")
        doc_id_input = st.text_input("Doc ID (để trống sẽ tự sinh)", value="")
        do_ingest = st.form_submit_button("Upload + Ingest")

    if do_ingest:
        if not uploaded_pdf:
            st.error("Cần chọn file PDF.")
        elif not subject_input.strip():
            st.error("Cần nhập môn học.")
        else:
            save_path = _save_uploaded_pdf(uploaded_pdf)
            with st.spinner("Đang ingest PDF (có thể mất vài phút)..."):
                try:
                    ingested = ingest_pdf(
                        pdf_path=save_path,
                        subject=subject_input.strip(),
                        doc_id=doc_id_input.strip() or None,
                    )
                    st.success(f"Ingest xong: {ingested} chunks.")
                except Exception as exc:  # noqa: BLE001
                    st.exception(exc)

    st.subheader("2) Sinh câu hỏi")
    doc_options = _safe_list(mongo.distinct_values("doc_id"))
    selected_doc = st.selectbox("Chọn tài liệu (doc_id)", options=[""] + doc_options, index=0)
    chapter_options = _chapters_for_doc(mongo, selected_doc) if selected_doc else []
    selected_chapter = st.selectbox("Chọn chương", options=[""] + chapter_options, index=0)
    extra_prompt = st.text_area(
        "Prompt bổ sung (tiêu chí/điều kiện/kiến thức)",
        placeholder="Ví dụ: ưu tiên câu hỏi vận dụng, có liên hệ bài tập thực tế...",
    )
    num_questions = st.slider("Số câu hỏi", min_value=1, max_value=10, value=5, step=1)

    if st.button("Sinh câu hỏi", type="primary"):
        if not selected_doc:
            st.error("Hãy chọn tài liệu trước khi sinh câu hỏi.")
        else:
            subject = _subject_for_doc(mongo, selected_doc)
            if not subject:
                st.error("Không tìm thấy môn học cho doc_id đã chọn.")
            else:
                with st.spinner("Đang sinh câu hỏi..."):
                    try:
                        generated = generate_questions(
                            subject=subject,
                            chapter=selected_chapter,
                            num_questions=num_questions,
                            query=extra_prompt.strip(),
                        )
                        st.session_state.generated = generated
                        st.success(f"Sinh xong {len(generated)} câu hỏi.")
                    except Exception as exc:  # noqa: BLE001
                        st.exception(exc)

    st.subheader("3) Truy xuất nguồn")
    _render_generation_results(mongo, selected_doc, selected_chapter)

    st.markdown("---")
    st.caption("Run: streamlit run fe/app.py")


if __name__ == "__main__":
    main()
