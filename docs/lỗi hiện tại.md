Đây là review đầy đủ cho lần cập nhật này:

---

## ✅ Đã sửa hoàn toàn

**TOC contamination** — fix rất gọn bằng `_is_toc_entry()` dùng regex `\.{3,}\s*\d+\s*$`. Đúng hướng, không over-engineer. TOC entries bị downgrade thành paragraph với confidence 0.5, không push vào section stack.

**Heading duplication trong chunk text** — fix đúng gốc rễ: heading block tách ra `heading_block` riêng, không còn trong `blocks` list. `full_text` = `heading_text + body_text` không còn lặp. Notebook output mới xác nhận: Chunk 150 text bắt đầu bằng `"7.6. LỢI ÍCH..."` một lần duy nhất.

**`reset_config_cache()` không reset pattern globals** — đã sửa đúng, giờ reset cả `_HEADING_RE` và `_SPECIAL_RE`.

**`_split_group` dùng O(n²) lookup** — đã fix bằng `id_to_block = {b.block_id: b for b in body_blocks}` dict lookup O(1).

**Tests thực sự là pytest** — có 3 file test với assert, fixture, class-based. Đây là cải tiến lớn.

**Scripts test cũ** đã được move sang `examples/` — cấu trúc sạch hơn.

---

## ⚠️ Vấn đề còn tồn tại / mới phát sinh

### 1. TOC fix chưa đủ — vẫn còn contamination (từ notebook output mới)

```
Chunk 1: Section: 2.4.3. Biểu thức điều kiện trong các cấu trúc điều khiển 43
Chunk 7: Section: Chương 10. THÀNH VIÊN LỚP ... > 11.2.3. Khối finally ...
```

Vấn đề: `_is_toc_entry` chỉ check `first_line`, nhưng nhiều TOC entry trong Java.pdf **không có dấu chấm ngay trên dòng đầu** — số trang nằm ở cuối dòng liền sau, hoặc block bị PyMuPDF tách thành 2 dòng như:

```
"5.4. ĐÓNG GÓI VÀ CÁC PHƯƠNG THỨC TRUY NHẬP \n75"
```

Dòng đầu `"5.4. ĐÓNG GÓI..."` không match `_TOC_RE` nên vẫn được classify là heading và push vào stack. Fix: cần check toàn bộ `raw_text`, không chỉ `first_line`:

```python
def _is_toc_entry(block_text: str) -> bool:
    # Check trên toàn bộ text, không chỉ first_line
    return bool(_TOC_RE.search(block_text))
```

Đồng thời cần bổ sung pattern cho số trang đứng riêng dòng sau heading:
```python
_TOC_TRAILING_PAGE_RE = re.compile(r'\n\s*\d{1,4}\s*$')
```

### 2. Section path vẫn sai sau khi fix TOC — TOC pages vẫn ảnh hưởng stack

Từ notebook: Chunk 7 có `section_path = ['Chương 10...', '11.2.3...']` — Chương 10 ở trang 2, nhưng nội dung về chương 11 ở trang 2–3. Đây là do TOC trên các trang 0–3 vẫn có một số entry lọt qua `_is_toc_entry` như đã nói ở trên, và headings của chúng bị push vào stack trước khi heading thật xuất hiện.

### 3. `_is_toc_entry` được gọi trên `first_line` nhưng signature nhận `line: str` — không nhất quán với usage

Trong `classify_blocks`:
```python
first_line = block.raw_text.split("\n", 1)[0].strip()
if _is_toc_entry(first_line):
```

Nhưng function docstring nói "TOC lines typically end with...". Nên đổi tên param và check toàn bộ block text như gợi ý ở trên.

### 4. Test `test_few_dots_not_enough` có thể false positive

```python
def test_few_dots_not_enough(self):
    assert not _is_toc_entry("Xem trang 12.. đúng không?")
```

Pattern `\.{3,}` yêu cầu 3+ dấu chấm, string này chỉ có 2 (`..`) nên test pass đúng. Tuy nhiên, edge case cần thêm: `"Xem mục 12... (xem thêm)"` — có 3 dấu chấm nhưng không phải TOC. Regex hiện tại `\.{3,}\s*\d+\s*$` sẽ không match vì không kết thúc bằng số, nên thực ra ổn. Nhưng nên có test case này.

### 5. `vn_encoding.py` vẫn chưa implement

Notebook vẫn còn `"Giíi thiÖu"` ở page 4. Checklist trong `docs/lỗi font.md` vẫn `[ ]` tất cả. Đây chưa phải blocker cho Tuần 3 nhưng sẽ ảnh hưởng chất lượng embedding.

### 6. `block_type: str = BlockType.UNKNOWN` trong `Block` — type hint vẫn chưa fix

Đã nêu lần trước, vẫn chưa sửa. Nên là `block_type: BlockType = BlockType.UNKNOWN`.

---

## Tóm tắt

| Vấn đề | Trước | Bây giờ |
|---|---|---|
| Heading lặp trong chunk text | ❌ | ✅ |
| `reset_config_cache` không đủ | ❌ | ✅ |
| O(n²) lookup trong split | ❌ | ✅ |
| Tests thực sự | ❌ | ✅ |
| TOC contamination (chính) | ❌ | ⚠️ Sửa một phần |
| Section path sai sau TOC | ❌ | ⚠️ Còn lỗi |
| `vn_encoding.py` | 🔲 | 🔲 |
| `block_type` type hint | ⚠️ | ⚠️ |

**Ưu tiên trước Tuần 3:** Sửa `_is_toc_entry` để check toàn bộ `raw_text` thay vì chỉ `first_line` — đây là nguyên nhân chính khiến section path vẫn sai trong notebook output mới.