# Daily Report — 25-26/06/2026

**NickName:** Kain

---

## Kết quả làm việc ngày 25/06/2026

### 1. Tính năng xem video của từng kênh YouTube (Phase 3)

Trước đây hệ thống chỉ theo dõi số liệu tổng quan của kênh (lượt theo dõi, bài đăng). Nay bổ sung khả năng lấy danh sách video của từng kênh YouTube, lưu vào database, hiển thị trong mini-app.

**Cụ thể đã làm:**
- **Tạo bảng `videos` trong database:** Lưu title, view count, like count, comment count, thumbnail URL, duration của từng video.
- **Cập nhật collector:** Khi đồng bộ kênh YouTube, tự động gọi API YouTube để lấy danh sách video mới nhất (tối đa 50 video) và lưu vào DB.
- **Viết API cho frontend:** Endpoint `GET /v1/subjects/{id}/videos` trả về danh sách video của một subject.
- **Hiển thị trong mini-app:** Thêm section "Videos" trên trang chi tiết subject, hiển thị danh sách video dạng card. Click vào video → mở YouTube trong tab mới.
- **Sửa bug:** Phát hiện collector không commit dữ liệu video vào database (lỗi thiếu `session.commit()`), khi crawl xong dữ liệu biến mất. Đã fix.

### 2. Cải thiện UI/UX

- **Luôn hiển thị section Videos** cho kênh YouTube (không ẩn đi khi chưa có video) — hiển thị trạng thái loading/empty/data để người dùng biết đang load.
- **Tách code giao diện** Facebook và YouTube ra file riêng (`YouTubeEngagementPanel`, `FacebookEngagementPanel`) để dễ bảo trì.
- **Tách kiểu dữ liệu** `ExtendedData` thành 2 loại riêng biệt cho Facebook và YouTube.

### 3. Kết nối Telegram Mini App

- **CORS:** Cho phép mini-app (chạy ở `localhost:5173`) gọi API gateway.
- **API key:** Seed key vào database để mini-app có thể xác thực.
- **Config:** Set URL API cho mini-app qua biến môi trường `VITE_API_BASE_URL`.

### 4. Lên kế hoạch Phase 4 (Alert Engine)

Quyết định các vấn đề kiến trúc cho Phase 4:
- **Alert Engine** là service riêng, không gộp chung với collector (dễ deploy độc lập).
- **Gửi Telegram** qua HTTP trực tiếp (không dùng thư viện aiogram) — giống pattern gateway đang dùng.
- **Tính baseline** dựa trên khung thời gian (24h gần nhất, tối thiểu 3 mẫu) thay vì đếm số lượng snapshot — vì tần suất đồng bộ có thể khác nhau giữa các kênh.
- **Bảng `alert_logs`** (lịch sử cảnh báo) thuộc sở hữu của alert-engine, không phải collector.

---

## Công việc hôm nay — 26/06/2026

### Phase 4: Xây dựng Alert Engine (Công cụ cảnh báo tự động)

Đây là tính năng lớn: hệ thống tự động kiểm tra số liệu của các kênh Facebook/YouTube, nếu phát hiện bất thường (theo luật do người dùng đặt) thì gửi cảnh báo qua Telegram.

**Ví dụ:** Người dùng đặt luật "nếu follow giảm quá 10% so với trung bình 24h thì cảnh báo" → Alert Engine sẽ tự động kiểm tra sau mỗi lần đồng bộ dữ liệu và gửi tin nhắn Telegram.

#### Kiến trúc tổng thể

```
1. Collector đồng bộ dữ liệu YouTube/Facebook
       │
2. Gửi tín hiệu "hãy kiểm tra subject này" → Celery queue
       │
3. Alert Engine nhận tín hiệu
       │
4. Đọc dữ liệu 24h gần nhất → tính baseline (trung bình, độ lệch chuẩn)
       │
5. So sánh số liệu hiện tại với baseline theo từng luật
       │
6. Nếu vượt ngưỡng → gửi Telegram → ghi log
```

#### Các thành phần đã xây dựng

**Tầng nền tảng (shared - social-common):**
- **Kiểu dữ liệu `AlertLog`:** Định nghĩa cấu trúc của một bản ghi cảnh báo (ID, subject, rule, thời gian, giá trị, ngưỡng, nội dung, trạng thái gửi).
- **Hằng số tên task:** Đảm bảo collector và alert-engine dùng chung tên để gọi nhau không bị lệch.

**Core Alert Engine (6 file logic):**
- **`db.py`** + **`models.py`:** Kết nối database. Định nghĩa bảng `alert_logs`, đồng thời mirror bảng subjects/snapshots/rules của các service khác (để đọc được dữ liệu).
- **`celery_app.py`:** Tạo Celery app riêng cho alert-engine (cùng Redis với collector). Có lịch chạy định kỳ (Beat) để quét toàn bộ subject.
- **`baseline.py`:** Tính baseline từ dữ liệu 24h gần nhất. Trả về mean và stdev của followers và activity frequency. Yêu cầu tối thiểu 3 snapshot để tính.
- **`evaluator.py`:** Bộ não — so sánh số liệu hiện tại với baseline. Hỗ trợ 5 loại luật:
  - `follower_spike`: Follow tăng đột biến
  - `follower_drop`: Follow giảm mạnh
  - `activity_spike`: Hoạt động tăng đột biến
  - `activity_silence`: Hoạt động giảm dưới ngưỡng
  - `status_change`: Trạng thái subject thay đổi (active → inactive...)
  - Có **cooldown** (1h) tránh gửi cảnh báo liên tục.
- **`notifier.py`:** Gửi tin nhắn Telegram qua HTTP trực tiếp. Gửi đến `channel_id` của từng rule (không dùng chat ID mặc định). Nếu không có chat ID → log cảnh báo, ghi `delivered=False`.
- **`tasks.py`:** Task Celery — `evaluate_all_alerts` (chạy định kỳ), `evaluate_subject_alerts` (gọi sau mỗi sync).
- **`__main__.py`:** CLI để chạy thủ công: `evaluate-all`, `evaluate-one <subject_id>`, `run-worker`.

**Cập nhật Collector (bên gửi tín hiệu):**
- Thêm read-only model cho `alert_logs`.
- Sau mỗi lần sync thành công → gọi `send_task` báo Alert Engine kiểm tra subject đó.

**Cập nhật Gateway (API cho frontend):**
- Endpoint mới: `GET /v1/subjects/{id}/alerts/logs` — trả về lịch sử cảnh báo của subject (phân trang, mới nhất trước).
- Thêm `CORS_ALLOW_ORIGINS` — cho phép cấu hình CORS qua biến môi trường thay vì hardcode (quan trọng khi dùng ngrok vì URL thay đổi mỗi lần restart).

**Cập nhật Mini App (giao diện người dùng):**
- `useAlertLogs` hook — gọi API lấy lịch sử cảnh báo.
- `AlertHistoryPanel` component — hiển thị danh sách cảnh báo ngay dưới phần cấu hình luật trong section "Alerts". 3 trạng thái: loading → spinner, không có dữ liệu → "No alerts triggered yet", có dữ liệu → danh sách card với badge xanh "Sent" / đỏ "Failed".

**Migration & Database:**
- Tạo `alembic.ini` + `env.py` + migration file cho alert-engine (dùng version table riêng: `alembic_version_alert_engine`).
- Migration đã chạy thành công trên database, bảng `alert_logs` đã tồn tại.

**Tài liệu:**
- `AGENTS.md`: Cập nhật thông tin alert-engine (cách chạy, lưu ý).
- `README.md` của alert-engine: Viết lại đầy đủ.
- Tracking file `docs/tracking/phase-4-implementation.md`: Ghi lại toàn bộ file manifest, ADR decisions, gotchas — để bất kỳ ai resume sau cũng không mất context.

#### Kiểm tra chất lượng

- **Ruff (lint):** Pass cả 4 Python packages.
- **Mypy (type check):** Pass cả 4 packages (riêng collector có 1 lỗi pre-existing không liên quan đến code mới).
- **Format:** Pass.
- **Build frontend:** `npm run build` thành công (TypeScript check + Vite build).
- **Migration:** Đã chạy `alembic upgrade head` trên database live.

---

## Công việc tiếp theo

### 1. Kiểm tra end-to-end
- Chạy thử alert-engine worker: `social-alert-engine run-worker`
- Trigger sync một subject → kiểm tra xem alert evaluation có chạy không
- Kiểm tra Telegram có gửi notification không

### 2. Kiểm tra kết nối ngrok
- Hiện tại mini-app dùng ngrok URL `https://2a6b-167-179-66-125.ngrok-free.app`
- Gateway CORS đã hỗ trợ config qua env var — cần update `CORS_ALLOW_ORIGINS` trong `.env`
- Verify mini-app + API hoạt động qua HTTPS

### 3. Unit tests
- Viết test cho baseline computation
- Viết test cho evaluator
- Viết test cho notifier

### 4. Xử lý pre-existing mypy error ở collector
- Dòng 293 `tasks.py`: `list[Video | None]` vs `list[Video]` — cần filter None trước khi truyền vào `sync_videos`.

---
