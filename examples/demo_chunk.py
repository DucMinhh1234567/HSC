from hsc_edu.core.extraction import extract_document
from hsc_edu.core.classification import classify_blocks
from hsc_edu.core.chunking import chunk_blocks

blocks = extract_document("data/Java.pdf")
classified = classify_blocks(blocks)
chunks = chunk_blocks(classified)

for ch in chunks[:20]:
    print(f"[{ch.block_type}] {ch.token_count} tokens | {' > '.join(ch.section_path)}")
    print(ch.text[:1200], "...")
    print()
