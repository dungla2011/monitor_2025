- 1 Main thread kiểm soát các thread con
- Mỗi thread con đại diện bởi 1 ID của item trong DB
- MainThread có Loop 5 giây 1 lần, list các thread con đang chạy và, list all item trong DB nếu thấy cái nào Enable=1 mà trong list thread running chưa có, thì sẽ start thread con đó.
- Ở mỗi thread con có 1 loop 3 giây để load lại item đó trong DB, và so sánh các trường (enable, name, user_id, url_check, type, maxAlertCount, check_interval_seconds, result_valid, result_error, stopTo, forceRestart)  nếu thấy giá trị khác ban đầu, thì sẽ stop luôn thread đó (để sau đó main thread sẽ tự Start lại thread này)
- MainThread nếu thấy Thread nào đang chạy mà trong DB có enable =0, thì sẽ Kill thread đang chạy đó (có vẻ như thead ko kill được nhau, nhưng cơ bản là muốn vậy)
- các đoạn check_service có thể chia nhỏ thành các hàm riêng
ví dụ check_ping_web, check_ping_icmp. Và bổ xung: check 3 lần mỗi lần cách nhau 3 giây, success thì dừng luôn

----------------------------
- Viết 1 hàm lấy ra <bot_token>,<chat_id> của một id trong monitor_items đang monitor, và dùng nó thay telegram token trong .env:

2 bảng monitor_items và monitor_configs
1 bảng monitor_and_configs : là bảng pivottable, 
có monitor_item_id và config_id là id của 2 bảng monitor_items, monitor_configs

- trong monitor_configs có trường  alert_type, nếu alert_type = 'telegram'
thì hãy xem trường alert_config
trường này sẽ là chuỗi 2 tham số cách nhau dấu phẩy: <bot_token>,<chat_id>

Vậy mỗi khi monitor một item trong monitor_items, thì hãy tìm ra alert_config để có thể gửi tin telegram nếu 2 tham số đó Có và hợp lệ (độ dài , format)

----------------------------

mỗi thread, nếu check_interval < 5 phút và nếu số lần lỗi lên tiếp là 10 (là sẽ gửi 10 lần alert telegram), thì sau lần thứ 10, sẽ giãn alert telegram ra 5 phút 1 lần (số 5 phút này có 1 biến global đặt, nếu =0 thì ko giãn, để bình thường)
vậy cũng sẽ có biến count số lần lỗi liên tiếp của thread, và số lần lỗi liên tiếp này sẽ trở lại = 0 nếu Không còn lỗi, hoặc lúc start thread

----------------------------

Bảng monitor_settings có các trường sau:

id
user_id
status
created_at
updated_at
deleted_at
log
alert_time_rangs
timezone
global_stop_alert_to

và user_id là duy nhất, nghĩa là setting riêng cho mỗi user:
- với alert_time_rangs là khoảng thời gian trong ngày cho phép gửi alert telegram (vì ngoài khoảng đó thì đi ngủ, ko nên gửi tin nhắn alert), với cấu trúc timeStart-TimeEnd trong ngày (cụ thể là H:i-H:i, ví dụ 05:30-23:00)
- global_stop_alert_to: datetime, dừng alert telegram đến lúc đó, tránh làm phiền
- mỗi một thread, đại diện là 1 hàng của monitor_items, có một trường là user_id
từ monitor_items.user_id  sẽ tìm ra monitor_settings.user_id để lấy ra các setting trên của user_id
sau đó dựa thêm vào alert_time_rangs, global_stop_alert_to để quyết định alert telegram có phép hiện tại hay ko


-------------

Check dạng 'web_content'
check bằng cách  fetch web content của url_check về
(fech tối đa 10KB)
sau đó kiểm tra nội dung trên 2 trường 

- result_valid : gồm các chuỗi con cách nhau bởi dấu phẩy, nếu content web có chứa tất cả các chuỗi con thì check là success (trim các chuỗi con trước khi check)
- result_error: gồm các chuỗi con cách nhau bởi dấu phẩy, nếu content web có chứa một trong các chuỗi con thì check là error (trim các chuỗi con trước khi check)

