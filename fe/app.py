"""Simple FE prototype for upload, question generation, and source tracing."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from hsc_edu.generation.question_generator import GeneratedQuestion, generate_questions
from hsc_edu.storage.ingest import ingest_pdf
from hsc_edu.storage.mongo_store import MongoChunkStore
from hsc_edu.storage.retrieval import retrieve_chunks


UPLOAD_DIR = Path("data/uploads")


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
        st.info("Khong co chunk_id de truy xuat.")
        return

    chunks = mongo.get_chunks_by_ids(chunk_ids)
    if not chunks:
        st.info("Khong tim thay chunk trong MongoDB.")
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
        st.info("Nhap query de truy xuat nguon.")
        return

    hits = retrieve_chunks(
        query=query,
        subject=subject,
        chapter=chapter,
        doc_id=doc_id,
        top_k=8,
    )
    if not hits:
        st.info("Khong co ket qua retrieval.")
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
        st.caption("Chua co cau hoi duoc sinh.")
        return

    st.subheader("Ket qua cau hoi + cau tra loi de xuat")
    for idx, item in enumerate(generated, start=1):
        with st.container(border=True):
            st.markdown(f"**{idx}. Cau hoi**")
            st.write(item.question)
            st.markdown("**Tra loi de xuat**")
            st.write(item.suggested_answer)
            st.caption(
                f"difficulty={item.difficulty or '-'} | bloom={item.bloom_level or '-'} | "
                f"chapter={item.chapter or '-'}",
            )

            col1, col2 = st.columns(2)
            with col1:
                if st.button("Xem chunk nguon", key=f"chunk_{idx}"):
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
        "1) Upload tai lieu PDF | 2) Gen cau hoi voi tuy chon doc/chapter/prompt bo sung | "
        "3) Truy xuat chunk/chapter/page tu ket qua.",
    )

    st.subheader("1) Upload tai lieu")
    with st.form("upload_form"):
        uploaded_pdf = st.file_uploader("Chon file PDF", type=["pdf"])
        subject_input = st.text_input("Subject", value="Lap trinh")
        doc_id_input = st.text_input("Doc ID (de trong se tu sinh)", value="")
        do_ingest = st.form_submit_button("Upload + Ingest")

    if do_ingest:
        if not uploaded_pdf:
            st.error("Can chon file PDF.")
        elif not subject_input.strip():
            st.error("Can nhap subject.")
        else:
            save_path = _save_uploaded_pdf(uploaded_pdf)
            with st.spinner("Dang ingest PDF (co the mat vai phut)..."):
                try:
                    ingested = ingest_pdf(
                        pdf_path=save_path,
                        subject=subject_input.strip(),
                        doc_id=doc_id_input.strip() or None,
                    )
                    st.success(f"Ingest xong: {ingested} chunks.")
                except Exception as exc:  # noqa: BLE001
                    st.exception(exc)

    st.subheader("2) Gen cau hoi")
    doc_options = _safe_list(mongo.distinct_values("doc_id"))
    selected_doc = st.selectbox("Chon tai lieu (doc_id)", options=[""] + doc_options, index=0)
    chapter_options = _chapters_for_doc(mongo, selected_doc) if selected_doc else []
    selected_chapter = st.selectbox("Chon chuong", options=[""] + chapter_options, index=0)
    extra_prompt = st.text_area(
        "Prompt bo sung (tieu chi/dieu kien/kien thuc)",
        placeholder="Vi du: uu tien cau hoi van dung, co lien he bai tap thuc te...",
    )
    num_questions = st.slider("So cau hoi", min_value=1, max_value=10, value=5, step=1)

    if st.button("Sinh cau hoi", type="primary"):
        if not selected_doc:
            st.error("Hay chon tai lieu truoc khi sinh cau hoi.")
        else:
            subject = _subject_for_doc(mongo, selected_doc)
            if not subject:
                st.error("Khong tim thay subject cho doc_id da chon.")
            else:
                with st.spinner("Dang sinh cau hoi..."):
                    try:
                        generated = generate_questions(
                            subject=subject,
                            chapter=selected_chapter,
                            num_questions=num_questions,
                            query=extra_prompt.strip(),
                        )
                        st.session_state.generated = generated
                        st.success(f"Sinh xong {len(generated)} cau hoi.")
                    except Exception as exc:  # noqa: BLE001
                        st.exception(exc)

    st.subheader("3) Truy xuat nguon")
    _render_generation_results(mongo, selected_doc, selected_chapter)

    st.markdown("---")
    st.caption("Run: streamlit run fe/app.py")


if __name__ == "__main__":
    main()
