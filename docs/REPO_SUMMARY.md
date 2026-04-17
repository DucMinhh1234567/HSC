# TONG HOP KIEN THUC VA THANH QUA — HSC-Edu

## 1) Muc tieu hoc thuat va bai toan da giai quyet

De tai tap trung xay dung he thong RAG cho giao trinh dai hoc, trong do trong tam la:

- Bao toan cau truc hoc thuat cua tai lieu (chuong, muc, tieu muc).
- Truy hoi dung noi dung de sinh cau hoi van dap.
- Dam bao kha nang truy vet nguon (source traceability) cho tung cau tra loi/cau hoi.

Ket qua la mot pipeline end-to-end tu PDF den retrieval va question generation.

---

## 2) Kien thuc cot loi da xay dung duoc

### 2.1 Kien thuc ve xu ly tai lieu (Document Processing)

- Phan biet PDF text-based va PDF scan de chon pipeline phu hop.
- Trich xuat blocks voi thong tin trang + vi tri + noi dung.
- Loc noise co he thong (header/footer lap, so trang, muc luc gay nhieu).

### 2.2 Kien thuc ve phan tich cau truc hoc lieu

- Rule-based classification cho heading, paragraph, table, figure.
- He thong heading level giup chuyen van ban phang thanh cau truc phan cap.
- Tu duy config-driven (regex/font rules trong YAML) de tai su dung cho nhieu mon hoc.

### 2.3 Kien thuc ve Hierarchical Semantic Chunking

- Chunk theo don vi y nghia thay vi cat co dinh theo token.
- Kiem soat kich thuoc chunk bang `max_tokens`, `min_tokens`, overlap.
- Giu ngu canh phan cap qua `header_path` va bo sung context truoc khi embed.

### 2.4 Kien thuc ve RAG va truy hoi ngu nghia

- Tach 2 lop luu tru:
  - MongoDB: noi dung day du + metadata.
  - Qdrant: vector embeddings + payload phuc vu tim kiem nhanh.
- Ket hop semantic search va metadata filter de tim chunk chinh xac theo mon/chuong.
- Dong bo du lieu giua vector store va metadata store trong qua trinh ingest.

### 2.5 Kien thuc ve Prompt Engineering cho giao duc

- Thiet ke prompt sinh cau hoi co rang buoc:
  - Chi dua tren noi dung giao trinh.
  - Co dap an goi y.
  - Co muc do kho va nguon trich dan.
- Chuan hoa output JSON de de parse va danh gia tu dong.

### 2.6 Kien thuc ve thiet ke he thong

- Kien truc module hoa theo layer: extraction -> classification -> linking -> chunking -> assembly -> storage -> generation.
- Tu duy mo rong theo phase (MVP -> nang cao HSC -> OCR -> API/UI).
- Co bo test cho cac khoi logic trong pipeline.

---

## 3) Thanh qua ky thuat da dat duoc

### 3.1 San pham ky thuat da hoan thanh

- Xay dung duoc pipeline chay end-to-end tu PDF den retrieval.
- Tich hop thanh cong embedding + luu tru vector (Qdrant) + metadata (MongoDB).
- Co bo notebook demo theo tung giai doan:
  - extraction
  - chunking
  - retrieval
  - generation

### 3.2 Ket qua thuc nghiem MVP (theo bao cao hien co)

- Da xu ly tong **343 trang PDF** (Java + C).
- Trich xuat duoc **4449 blocks**.
- Tao duoc **437 chunks** phuc vu retrieval/generation.
- Bai test ground truth retrieval dat **Top-1 accuracy: 5/5 (100%)** tren tap cau hoi thu nghiem.

### 3.3 Gia tri thuc tien

- Chung minh duoc huong tiep can chunking theo cau truc hoc thuat co kha nang ap dung tot cho bai toan giao duc.
- Dat nen tang cho cac use case:
  - sinh cau hoi van dap theo chuong/muc
  - tro giang AI tra loi theo giao trinh
  - truy vet nguon kien thuc de giang vien kiem chung

---

## 4) Han che da nhan dien

- Van ton tai chunk qua ngan (heading-only), anh huong den chat luong context.
- Mot so chunk thieu chapter/section path o phan mo dau tai lieu.
- Chua hoan thien xu ly OCR cho tai lieu scan chat luong thap.
- Co nguy co cham do rate limit khi goi API LLM/embedding o quy mo lon.

---

## 5) Bai hoc kinh nghiem rut ra

- Chat luong chunk quyet dinh manh den chat luong retrieval va generation.
- Metadata schema ro rang giup truy van dung nghiep vu va danh gia de dang hon.
- Prompt chat che + source citation la dieu kien can de giam hallucination.
- He thong nao cung can benchmark lien tuc giua chat luong va chi phi van hanh.

---

## 6) Dinh huong phat trien tiep theo

- Cai tien chunking (merge heading-only, calibration token thresholds).
- Nang cap classification/linking cho cac mau tai lieu da dang hon.
- Hoan thien OCR va xu ly cong thuc toan.
- Bo sung API backend va giao dien de trien khai muc production.
- Mo rong bo danh gia voi tap giao trinh lon hon va nhieu bo mon hon.
