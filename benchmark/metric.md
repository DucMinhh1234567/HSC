Được, với báo cáo dự án cá nhân thì nên giữ lại những gì **dễ đo, có số liệu cụ thể, và thể hiện được pipeline hoạt động**.

---

## Bộ tiêu chí tối giản cho báo cáo cá nhân

### Tầng 1 — Chunking (đo tự động, không cần ground truth)

| Tiêu chí | Tại sao giữ |
|---|---|
| Tổng chunks, avg tokens/chunk, phân bố token | Bạn đã có sẵn từ notebook 02/03 |
| Short chunk ratio (token < 64) | Chỉ ra điểm yếu đã biết, thành thật trong báo cáo |
| Chapter coverage | % chapter được nhận diện đúng → chứng minh classifier hoạt động |

### Tầng 2 — Retrieval (cần làm thêm một chút)

| Tiêu chí | Tại sao giữ |
|---|---|
| Hit@1 và Hit@3 | Bạn đã có 5 câu, mở rộng lên ~15–20 câu là đủ |
| Cosine score của top-1 | Đã có sẵn trong output notebook 03 |

> Hit@1 và Hit@3 trên ~15–20 câu là đủ thuyết phục cho báo cáo cá nhân. Không cần MRR.

### Tầng 3 — Generation (đánh giá thủ công ~20 câu)

| Tiêu chí | Tại sao giữ |
|---|---|
| Factual accuracy (Đúng / Chưa tốt / Sai) | Tiêu chí quan trọng nhất, dễ tự đánh giá |
| Parse success rate | Tự động, không tốn công |
| Difficulty distribution | Đã có sẵn từ `Counter(difficulty)` |

---

## Bỏ hẳn những gì

- MRR, cross-chapter recall → quá phức tạp cho báo cáo cá nhân
- So sánh HSC vs fixed-size baseline → cần implement thêm một pipeline riêng
- Table integrity, encoding error rate → quá chi tiết, là bug đã biết thì ghi nhận thẳng vào phần hạn chế
- Đánh giá system (throughput, cost) → không cần thiết
- Relevance/Usability/Answerability thang 1–5 → gộp vào Factual accuracy là đủ

---

## Tóm lại chỉ cần 7 con số

1. Tổng chunks + avg tokens/chunk
2. Short chunk ratio
3. Chapter coverage %
4. Hit@1 (retrieval)
5. Hit@3 (retrieval)
6. Factual accuracy % (tự đánh giá ~20 câu)
7. Parse success rate + difficulty distribution

Với 7 con số này, báo cáo cá nhân đã có đủ bằng chứng cho từng tầng của pipeline mà không tốn quá nhiều công.