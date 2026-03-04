from pathlib import Path

from hsc_edu.core.extraction.pdf_detector import detect_pdf_type, PDFType

pdf_path = Path("data/Java.pdf")

result = detect_pdf_type(
    pdf_path,
    sample_size=20,        # tùy chọn: kiểm tra tối đa 20 trang, None = tất cả
    threshold=None,        # tùy chọn: None = dùng config mặc định (50 ký tự)
)

print("Loại PDF:", result.pdf_type.value)
print("Tổng số trang:", result.total_pages)
print("Số trang text:", result.text_pages)
print("Số trang scan:", result.scan_pages)
print("Tỉ lệ trang text:", result.text_ratio)

if result.pdf_type is PDFType.SCANNED:
    print("Nên dùng OCR (ví dụ Tesseract) để trích xuất.")
elif result.pdf_type is PDFType.TEXT_BASED:
    print("Có thể trích xuất text trực tiếp (PyMuPDF, pdfminer, v.v.).")