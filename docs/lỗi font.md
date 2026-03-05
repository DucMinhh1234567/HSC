# Gợi ý sửa lỗi encoding font tiếng Việt khi extract PDF

Tài liệu này ghi lại vấn đề và hướng xử lý cho lỗi **text tiếng Việt bị sai ký tự** khi extract từ PDF (ví dụ trong `notebooks/01_extraction_demo.ipynb`, mục 4).

---

## 1. Mô tả vấn đề

### Triệu chứng

- Một số block (đặc biệt **tiêu đề**, font lớn) có text **sai dấu** hoặc **sai ký tự**:
  - **"Giíi thiÖu"** thay vì **"Giới thiệu"**
  - **"Ch-¬ng"** thay vì **"Chương"**
- Block dùng font **TT2A6t00** (15pt) thường lỗi; block dùng **TT190t00** (11.3pt) thường đúng.

Page 4: 6 block(s)
[0] bbox=(93.6, 59.23, 161.3, 74.22)  font=(TT2A6t00, 15.0pt, bold=False)
    Giíi thiÖu

### Nguyên nhân

- PDF dùng **nhiều font**; một số font (ví dụ TT2A6t00) dùng **bảng mã cũ** (TCVN3/ABC, VNI) trong khi file PDF khai báo encoding sai hoặc thiếu ToUnicode CMap.
- PyMuPDF trả về Unicode theo từng font → font “lỗi” cho ra **codepoint sai** (ví dụ Latin-1 thay vì ký tự tiếng Việt chuẩn).

### Ảnh hưởng

| Giai đoạn   | Ảnh hưởng |
|------------|-----------|
| **Chunking** | Nội dung chunk sai; regex heading (vd. "Chương", "Giới thiệu") có thể không match. |
| **Embedding** | Vector của text lỗi khác vector của text đúng → similarity thấp với query chuẩn. |
| **Retrieve**  | Chunk quan trọng dễ bị xếp hạng thấp hoặc bỏ sót. |

---

## 2. Hướng xử lý đề xuất

### Tầng 1: Remap bảng mã legacy (ưu tiên)

- **Ý tưởng**: Sau khi lấy text từ mỗi **span** (trong `_block_text()`), nếu nghi ngờ encoding legacy → áp dụng bảng remap **TCVN3 → Unicode** (và tùy chọn **VNI → Unicode**).
- **Vị trí code**: `hsc_edu/core/extraction/text_extractor.py` — sửa `_block_text()` để gọi bước remap **theo từng span** (vì mỗi span có font riêng).
- **Bảng mã**: Chỉ có **2–3 bảng** tiếng Việt cũ (TCVN3, VNI, VISCII); tập đã đóng, không cần thêm mapping mới khi gặp font khác — chỉ cần **auto-detect** xem span nào cần remap.

**Cách triển khai gợi ý**:

1. Tạo module `hsc_edu/core/extraction/vn_encoding.py`:
   - `TCVN3_TO_UNICODE`: dict mapping codepoint sai → ký tự Unicode đúng (bảng chuẩn TCVN3, tìm sẵn trên mạng).
   - `VNI_TO_UNICODE`: tương tự cho VNI (nếu cần).
   - `remap_text(text: str, encoding: str) -> str`.
   - `looks_like_valid_vietnamese(text: str) -> bool`: heuristic đơn giản (tỷ lệ ký tự thuộc bảng chữ Việt, hoặc regex âm tiết).
   - `auto_remap(text: str, font_name: str = "") -> str`:
     - Nếu `looks_like_valid_vietnamese(text)` → trả về `text`.
     - Ngược lại, thử lần lượt TCVN3, VNI; tính `vietnamese_score(remapped)`; trả về bản remap có score cao nhất nếu > ngưỡng, không thì giữ nguyên.

2. Trong `_block_text(blk)`:
   - Duyệt từng **line** → từng **span**.
   - Với mỗi span: `raw = span.get("text", "")`, `font = span.get("font", "")`.
   - Gọi `raw = auto_remap(raw, font)` (hoặc chỉ `auto_remap(raw)` nếu không dùng font name).
   - Nối span đã remap vào line/block như hiện tại.

3. Kiểm tra: chạy lại notebook, mục 4 — "Giới thiệu", "Chương" phải hiển thị đúng.

### Tầng 2: Auto-detect encoding (không phụ thuộc font name)

- Để **không** phải “font X thì dùng bảng Y”, dùng **heuristic**:
  - Với text nghi ngờ (không pass `looks_like_valid_vietnamese`), thử **tất cả** bảng remap (TCVN3, VNI).
  - Chọn bản remap có `vietnamese_score(remapped)` cao nhất; nếu trên ngưỡng thì dùng, không thì giữ nguyên.
- Như vậy **mọi font lạ** đều được xử lý nếu nội dung thực sự là TCVN3/VNI.

### Tầng 3: OCR fallback (Phase 3)

- Khi đã có pipeline OCR (theo TODO.md):
  - Nếu sau remap mà `vietnamese_score` vẫn thấp → đánh dấu block “cần OCR” → crop **bbox** từ page render → chạy OCR → thay thế `raw_text` bằng kết quả OCR.
- Dùng cho edge case hiếm (encoding hoàn toàn lạ, hoặc font bitmap không có CMap).

---

## 3. File / cấu trúc gợi ý

```
hsc_edu/core/extraction/
├── __init__.py
├── pdf_detector.py
├── text_extractor.py    # sửa _block_text() gọi auto_remap per-span
└── vn_encoding.py       # mới: bảng TCVN3/VNI, looks_like_valid_vietnamese, auto_remap
```

- **Config**: Có thể thêm vào `config/settings.py` (vd. `extraction.vn_remap_enabled: bool`, `extraction.vn_remap_encodings: ["tcvn3", "vni"]`) để bật/tắt hoặc chọn bảng remap mà không sửa code.

---

## 4. Tài liệu tham khảo

- Bảng **TCVN3 (ABC) → Unicode**: chuẩn TCVN 5712:1993, nhiều nguồn GitHub/Stack Overflow có sẵn dict Python.
- Bảng **VNI → Unicode**: tương tự, encoding VNI Windows.
- PyMuPDF: `page.get_text("dict")` — mỗi span có `font`, `text`, `size`; text đã được PyMuPDF map theo font, nên sửa ở tầng “post-process per span” là đủ.

---

## 5. Checklist triển khai (khi thực hiện)

- [ ] Tạo `hsc_edu/core/extraction/vn_encoding.py` với bảng TCVN3 (và tùy chọn VNI).
- [ ] Implement `looks_like_valid_vietnamese()` và `vietnamese_score()`.
- [ ] Implement `auto_remap(text, font_name)`.
- [ ] Sửa `_block_text()` trong `text_extractor.py` để remap từng span.
- [ ] Chạy lại `01_extraction_demo.ipynb` (mục 4, trang 4 Java.pdf) và kiểm tra "Giới thiệu", "Chương".
- [ ] (Tùy chọn) Thêm config bật/tắt remap trong `settings`.
- [ ] (Phase 3) Kết nối OCR fallback cho block remap vẫn lỗi.

---

*Tài liệu tạo để tham khảo khi sửa lỗi encoding font tiếng Việt trong tương lai.*
