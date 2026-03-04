## C.pdf

### 1. Định nghĩa về Thuật giải (Algorithm)

- **Nội dung**: Thuật giải là một dãy các thao tác xác định trên một đối tượng, sao cho sau khi thực hiện một số hữu hạn các bước thì đạt được mục tiêu đề ra. Các thuật giải và chương trình máy tính đều dựa trên 3 cấu trúc điều khiển cơ bản là: Tuần tự (Sequential), Chọn lọc (Selection) và Lặp lại (Repetition).
- **Câu hỏi**: Thuật giải (Algorithm) là gì và nó dựa trên những cấu trúc điều khiển cơ bản nào?

### 2. Quy trình 5 bước lập trình

- **Nội dung**: Để lập trình giải quyết một vấn đề, người lập trình cần tuân thủ 5 bước:
  - Phân tích vấn đề và xác định các đặc điểm (Input-Process-Output).
  - Lập ra giải pháp (đưa ra thuật giải).
  - Cài đặt (viết chương trình).
  - Chạy thử chương trình (dịch chương trình).
  - Kiểm chứng và hoàn thiện chương trình bằng nhiều số liệu khác nhau.
- **Câu hỏi**: Hãy trình bày quy trình 5 bước để lập trình giải quyết một vấn đề theo tài liệu?

### 3. Quy tắc đặt tên trong ngôn ngữ C

- **Nội dung**: Tên (dùng cho hằng, biến, mảng, hàm...) là một chuỗi ký tự liên tục gồm: Ký tự chữ, số và dấu gạch dưới. Ký tự đầu tiên của tên phải là chữ hoặc dấu gạch dưới. Tên không được trùng với các từ khóa và trong C, tên có phân biệt chữ hoa và chữ thường. Chiều dài tối đa của tên là 32 ký tự.
- **Câu hỏi**: Các quy tắc cần lưu ý khi đặt tên biến hoặc tên hàm trong lập trình C là gì?

### 4. Các kiểu dữ liệu cơ bản và kích thước

- **Nội dung**: Ngôn ngữ C cung cấp các kiểu dữ liệu cơ bản với kích thước bộ nhớ khác nhau:
  - `char`: 1 byte (miền giá trị từ -128 đến 127).
  - `int`: 2 bytes (miền giá trị từ -32,768 đến 32,767).
  - `float`: 4 bytes.
  - `double`: 8 bytes.
  - Ngoài ra còn có các kiểu mở rộng như `long` (4 bytes) hoặc `unsigned int` (2 bytes).
- **Câu hỏi**: Liệt kê các kiểu dữ liệu cơ bản trong C và kích thước bộ nhớ tương ứng của chúng?

### 5. Ý nghĩa của các ký tự điều khiển trong hàm `printf`

- **Nội dung**: Trong chuỗi định dạng của hàm `printf`, các ký tự điều khiển phổ biến bao gồm:
  - `\n`: Nhảy xuống dòng kế tiếp.
  - `\t`: Canh cột tab ngang.
  - `\a`: Phát ra tiếng kêu bip.
  - `\\`: In ra dấu gạch chéo ngược (`\`).
  - `\"`: In ra dấu nháy kép (`"`).
- **Câu hỏi**: Trong hàm `printf`, các ký tự điều khiển `\n`, `\t` và `\a` có tác dụng gì?

### 6. Sự khác biệt giữa vòng lặp `while` và `do...while`

- **Nội dung**: Trong lệnh `while`, biểu thức điều kiện được kiểm tra trước khi thực hiện khối lệnh. Ngược lại, trong lệnh `do...while`, biểu thức điều kiện được kiểm tra sau khi khối lệnh đã thực hiện. Do đó, với `do...while`, khối lệnh luôn được thực hiện ít nhất một lần ngay cả khi điều kiện sai ngay từ đầu.
- **Câu hỏi**: Phân biệt sự khác nhau về cơ chế hoạt động giữa vòng lặp `while` và `do...while`?

### 7. Khái niệm và đặc điểm của biến con trỏ

- **Nội dung**: Biến con trỏ không chứa dữ liệu trực tiếp mà chỉ chứa địa chỉ của ô nhớ chứa dữ liệu. Kích thước của biến con trỏ không phụ thuộc vào kiểu dữ liệu mà nó trỏ tới, luôn có kích thước cố định là 2 byte. Ta dùng toán tử `&` để lấy địa chỉ của một biến và toán tử `*` để truy xuất giá trị tại địa chỉ mà con trỏ đang giữ.
- **Câu hỏi**: Biến con trỏ là gì và kích thước của nó trong bộ nhớ là bao nhiêu?

### 8. Kiểu dữ liệu cấu trúc (`struct`)

- **Nội dung**: Khác với mảng (chỉ lưu các phần tử cùng kiểu), `struct` cho phép lưu trữ nhiều thông tin có kiểu dữ liệu khác nhau trong cùng một tên gọi. Để truy xuất đến các thành phần (phần tử) bên trong một biến `struct`, ta sử dụng dấu chấm `.` (ví dụ: `nv.manv`). Nếu là biến con trỏ cấu trúc, ta dùng ký hiệu `->`.
- **Câu hỏi**: Kiểu dữ liệu `struct` trong C dùng để làm gì và cách truy xuất các phần tử của nó như thế nào?

---

## Python.pdf

### 1. Đặc điểm nổi bật của ngôn ngữ Python

- **Nội dung**: Python là một ngôn ngữ lập trình bậc cao, hướng đối tượng và cực kỳ đa năng với cú pháp đơn giản, dễ nhớ, dễ hiểu. Một số đặc điểm nổi bật bao gồm tính chất miễn phí, mã nguồn mở, khả năng thông dịch cấp cao (tự động quản lý bộ nhớ) và khả năng di động (chạy trên nhiều hệ điều hành như Windows, macOS, Linux mà không cần thay đổi mã nguồn).
- **Câu hỏi**: Ngôn ngữ Python có những đặc điểm nổi bật nào giúp nó trở nên phổ biến và thuận tiện cho người mới bắt đầu?

### 2. Cấu trúc chương trình và quy tắc thụt lề (Indentation)

- **Nội dung**: Một chương trình Python thường gồm ba phần chính: các khai báo thư viện/mã hóa, định nghĩa các hàm và phần thân chương trình chính. Điểm khác biệt quan trọng là Python sử dụng việc thụt lề (khoảng trống hoặc Tab) để phân chia các khối lệnh (như trong hàm hoặc cấu trúc điều khiển) thay vì dùng các cặp dấu ngoặc nhọn `{}` như các ngôn ngữ khác.
- **Câu hỏi**: Cấu trúc một chương trình Python cơ bản gồm những phần nào và cách Python phân chia các khối lệnh có gì đặc biệt?

### 3. Quy tắc đặt tên định danh (Biến, Hằng, Hàm)

- **Nội dung**: Tên trong Python là một chuỗi ký tự dùng để phân biệt các thành phần trong chương trình. Quy tắc đặt tên bao gồm: chỉ sử dụng chữ cái (`a-z`, `A-Z`), chữ số (`0-9`) và dấu gạch dưới (`_`); không được bắt đầu bằng chữ số; có phân biệt chữ hoa và chữ thường; và không được trùng với các từ khóa của hệ thống.
- **Câu hỏi**: Trình bày các quy tắc cần tuân thủ khi đặt tên biến hoặc tên hàm trong Python?

### 4. Các loại ghi chú (Comments) trong mã nguồn

- **Nội dung**: Ghi chú giúp giải thích mã nguồn và sẽ bị trình thông dịch bỏ qua khi chạy chương trình. Python hỗ trợ ghi chú trên một dòng bằng ký hiệu `#` đặt trước nội dung. Đối với ghi chú nhiều dòng hoặc các đoạn tài liệu dài, người lập trình sử dụng cặp ba dấu nháy đơn (`'''...'''`) hoặc ba dấu nháy kép (`"""..."""`).
- **Câu hỏi**: Làm thế nào để tạo ghi chú một dòng và nhiều dòng trong ngôn ngữ lập trình Python?

### 5. Kiểu dữ liệu danh sách (List)

- **Nội dung**: `List` là một "thùng chứa" nhiều phần tử có thể thuộc các kiểu dữ liệu khác nhau, được đặt trong cặp ngoặc vuông `[]` và phân cách bởi dấu phẩy. Các phần tử trong `List` được đánh số thứ tự (index) bắt đầu từ 0 từ trái sang phải, hoặc từ -1 từ phải sang trái, cho phép truy cập, thêm hoặc xóa phần tử linh hoạt.
- **Câu hỏi**: Kiểu dữ liệu `List` trong Python là gì và cách truy cập các phần tử bên trong nó như thế nào?

### 6. Cấu trúc rẽ nhánh với `if`, `elif`, `else`

- **Nội dung**: Cấu trúc rẽ nhánh dùng để thực hiện các hành động khác nhau dựa trên kết quả kiểm tra một biểu thức lô-gic (`True`/`False`). Lệnh `if` kiểm tra điều kiện đầu tiên, `elif` (else if) dùng để kiểm tra các điều kiện bổ sung nếu các điều kiện trước đó sai, và `else` chứa khối lệnh sẽ thực hiện nếu tất cả các điều kiện trên đều không thỏa mãn.
- **Câu hỏi**: Hãy giải thích cơ chế hoạt động của cấu trúc rẽ nhánh `if...elif...else` trong Python?

### 7. Sự khác biệt giữa vòng lặp `while` và `for`

- **Nội dung**: Vòng lặp `while` thực hiện lặp đi lặp lại một khối lệnh khi điều kiện còn đúng (kiểm tra điều kiện trước mỗi lần lặp). Trong khi đó, vòng lặp `for` được thiết kế để duyệt qua các mục của một tập hợp (như danh sách, chuỗi, hoặc dãy số được tạo bởi hàm `range()`) với số lần lặp thường được biết trước dựa trên số lượng phần tử.
- **Câu hỏi**: Phân biệt mục đích sử dụng và cách hoạt động của vòng lặp `while` và vòng lặp `for`?

### 8. Định nghĩa và lợi ích của Hàm (Function)

- **Nội dung**: Hàm là một tập hợp các câu lệnh được gom nhóm lại, đặt tên và có thể tái sử dụng nhiều lần trong chương trình nhằm tránh viết lại mã nguồn giống nhau. Hàm được định nghĩa bằng từ khóa `def`, có thể nhận các tham số đầu vào và trả về kết quả thông qua từ khóa `return`.
- **Câu hỏi**: Hàm (Function) trong Python là gì và tại sao việc sử dụng hàm lại giúp chương trình tối ưu hơn?

### 9. Thao tác với tệp dữ liệu (File)

- **Nội dung**: Quy trình làm việc với tệp gồm ba bước: Mở tệp bằng hàm `open()`, đọc hoặc ghi dữ liệu, và đóng tệp bằng phương thức `close()` để giải phóng tài nguyên. Các chế độ mở tệp phổ biến bao gồm:
  - `'r'`: chỉ đọc.
  - `'w'`: ghi mới (sẽ xóa nội dung cũ).
  - `'a'`: ghi nối thêm vào cuối tệp.
- **Câu hỏi**: Trình bày quy trình các bước để làm việc với một tệp văn bản và ý nghĩa của các chế độ mở tệp `'r'`, `'w'`, `'a'`?

### 10. Giới thiệu về thư viện Pandas

- **Nội dung**: Pandas là một thư viện mã nguồn mở cung cấp các cấu trúc dữ liệu hiệu quả như `DataFrame` để lưu trữ và phân tích dữ liệu dưới dạng bảng (hàng và cột). Nó hỗ trợ nhiều thao tác như đọc/ghi tệp CSV/Excel, thêm/xóa/sửa dữ liệu, sắp xếp, trích rút dữ liệu theo điều kiện và tính toán thống kê.
- **Câu hỏi**: Thư viện Pandas trong Python dùng để làm gì và cấu trúc dữ liệu chính của nó là gì?

---

## Lập trình Java và OOP.pdf

### 1. Khái niệm về Đối tượng và Lớp

- **Nội dung**: Đối tượng (`object`) là một mô hình của một thực thể hay khái niệm trong thế giới thực, là khái niệm trung tâm của lập trình hướng đối tượng. Trong mỗi ứng dụng, các đối tượng có đặc điểm tương tự nhau được xếp vào cùng một nhóm gọi là lớp (`class`). Lớp đóng vai trò là khuôn mẫu để tạo ra các đối tượng, và mỗi đối tượng được tạo ra từ một lớp được gọi là một thực thể (`instance`) của lớp đó.
- **Câu hỏi 1**: Đối tượng và lớp trong lập trình hướng đối tượng có mối quan hệ với nhau như thế nào?
- **Câu hỏi 2**: "Thực thể" (`instance`) trong Java có ý nghĩa gì?

### 2. Bốn nguyên tắc trụ cột của OOP

- **Nội dung**: Lập trình hướng đối tượng dựa trên bốn khái niệm quan trọng:
  - **Trừu tượng hóa (abstraction)**: cơ chế đơn giản hóa các tình huống phức tạp bằng cách tập trung vào các tính chất quan trọng.
  - **Đóng gói (encapsulation)**: giúp bọc các trạng thái và hành vi vào trong một khối duy nhất là lớp.
  - **Thừa kế (inheritance)**: cho phép xây dựng lớp mới dựa trên các lớp đã có.
  - **Đa hình (polymorphism)**: khả năng một cái tên có thể được hiểu theo nhiều cách khác nhau tùy từng tình huống.
- **Câu hỏi 1**: Hãy liệt kê và giải thích ngắn gọn bốn nguyên tắc trụ cột của lập trình hướng đối tượng theo tài liệu?
- **Câu hỏi 2**: Trừu tượng hóa trong OOP giúp ích gì cho người lập trình khi đối mặt với lượng thông tin lớn?

### 3. Đặc tính độc lập nền tảng của Java

- **Nội dung**: Java là ngôn ngữ có tính độc lập nền tảng (platform independent) với khẩu hiệu nổi tiếng là "Write once, run anywhere" (Viết một lần, chạy bất cứ đâu). Điều này có nghĩa là một chương trình Java có thể chạy trên các hệ điều hành khác nhau (Windows, Macintosh, Linux...) mà không cần phải dịch lại mã nguồn. Để làm được việc này, trình biên dịch Java dịch mã nguồn thành bytecode mà máy ảo Java (JVM) có thể hiểu và thực thi.
- **Câu hỏi 1**: Tại sao nói ngôn ngữ Java có tính độc lập nền tảng?
- **Câu hỏi 2**: Bytecode trong Java đóng vai trò gì trong quy trình thực thi chương trình?

### 4. Cấu trúc và quy trình thực thi chương trình Java

- **Nội dung**: Một chương trình Java bao gồm một hoặc nhiều định nghĩa lớp, trong đó mỗi định nghĩa lớp thường được đặt trong một file riêng với phần mở rộng là `.java`. Quy trình thực thi gồm 3 bước cơ bản:
  1. Soạn thảo mã nguồn.
  2. Dịch mã nguồn bằng trình biên dịch `javac` để tạo ra file `.class` (bytecode).
  3. Nạp và chạy chương trình thông qua máy ảo Java.
- **Câu hỏi 1**: Trình bày quy trình 3 bước cơ bản để xây dựng và thực thi một chương trình Java?
- **Câu hỏi 2**: Tên file mã nguồn Java cần tuân theo quy tắc gì so với tên lớp bên trong nó?

### 5. Phương thức `main()` - Điểm khởi đầu của chương trình

- **Nội dung**: Để một lớp có thể chạy như một ứng dụng độc lập, nó phải chứa một phương thức có tên là `main()`. Đây là nơi chương trình bắt đầu thực hiện và cũng là nơi kết thúc; máy ảo Java sẽ tìm và chạy các lệnh bên trong cặp ngoặc `{ }` của phương thức này. Cú pháp bắt buộc của nó là:

  ```java
  public static void main(String[] args)
  ```

- **Câu hỏi 1**: Phương thức `main()` có vai trò gì trong một ứng dụng Java?
- **Câu hỏi 2**: Cú pháp khai báo đầy đủ và bắt buộc của phương thức `main()` là gì?

### 6. Nguyên tắc Đóng gói và Che giấu thông tin

- **Nội dung**: Nguyên tắc đóng gói khuyến cáo: "Đừng để lộ cấu trúc dữ liệu bên trong". Để thực hiện việc này, lập trình viên nên đánh dấu các biến thực thể với từ khóa `private` (chỉ mã bên trong lớp mới có quyền truy nhập) và cung cấp các phương thức `public` `set` và `get` để cho phép bên ngoài truy xuất dữ liệu một cách an toàn. Việc che giấu chi tiết cài đặt giúp giảm sự phụ thuộc lẫn nhau giữa các mô-đun trong hệ thống.
- **Câu hỏi 1**: Làm thế nào để thực hiện nguyên tắc đóng gói đối với các biến thực thể trong một lớp Java?
- **Câu hỏi 2**: Việc sử dụng các từ khóa `private` và `public` đem lại lợi ích gì cho việc quản lý mã nguồn?

### 7. Quan hệ Thừa kế (Inheritance)

- **Nội dung**: Thừa kế là cơ chế cho phép định nghĩa một lớp mới (lớp con/lớp dẫn xuất) dựa trên một lớp có sẵn (lớp cha/lớp cơ sở). Lớp con sẽ tự động thừa hưởng các thành viên (biến và phương thức) của lớp cha và có thể bổ sung thêm các tính năng mới hoặc cài đè (`override`) các phương thức cũ. Trong Java, từ khóa được sử dụng để thiết lập quan hệ này là `extends`.
- **Câu hỏi 1**: Thế nào là quan hệ thừa kế giữa lớp cha và lớp con?
- **Câu hỏi 2**: Trong Java, từ khóa nào được dùng để khai báo một lớp kế thừa từ một lớp khác?

### 8. Tính Đa hình và Cơ chế gọi phương thức

- **Nội dung**: Trong hướng đối tượng, đa hình đi kèm với quan hệ thừa kế, cho phép các đối tượng thuộc các lớp dẫn xuất khác nhau được đối xử thống nhất như thể chúng thuộc lớp cha. Khi gọi một phương thức từ một tham chiếu kiểu lớp cha, máy ảo Java sẽ thực hiện phiên bản phương thức đặc thù nhất dựa trên kiểu của đối tượng thực tế đang được chiếu tới, chứ không phải kiểu của tham chiếu.
- **Câu hỏi 1**: Tính đa hình trong lập trình hướng đối tượng được hiểu như thế nào?
- **Câu hỏi 2**: Khi một biến tham chiếu kiểu lớp cha gọi một phương thức đã bị lớp con cài đè, phiên bản phương thức nào sẽ được thực thi?

### 9. Đặc điểm của Ngôn ngữ Java: Định kiểu mạnh

- **Nội dung**: Java là một ngôn ngữ định kiểu mạnh (strongly-typed language). Điều này có nghĩa là mọi biến đều phải có một kiểu dữ liệu xác định và phải được khai báo trước khi sử dụng. Trình biên dịch sẽ kiểm tra nghiêm ngặt các phép gán; ví dụ, bạn không thể gán một giá trị số thực (`float`) vào một biến số nguyên (`int`) mà không dùng phép đổi kiểu tường minh, vì việc đó có thể làm giảm độ chính xác.
- **Câu hỏi 1**: Java là ngôn ngữ "định kiểu mạnh" có nghĩa là gì?
- **Câu hỏi 2**: Theo tài liệu, chuyện gì xảy ra nếu bạn cố gắng gán một giá trị kiểu `float` vào một biến kiểu `int`?