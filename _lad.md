- 1 Main thread kiểm soát các thread con
- Mỗi thread con đại diện bởi 1 ID của item trong DB
- MainThread có Loop 5 giây 1 lần, list các thread con đang chạy và, list all item trong DB nếu thấy cái nào Enable=1 mà trong list thread running chưa có, thì sẽ start thread con đó.
- Ở mỗi thread con có 1 loop 3 giây để load lại item đó trong DB, và so sánh các trường (enable, name, user_id, url_check, type, maxAlertCount, timeRangeSeconds, result_check, result_error, stopTo, forceRestart)  nếu thấy giá trị khác ban đầu, thì sẽ stop luôn thread đó (để sau đó main thread sẽ tự Start lại thread này)
- MainThread nếu thấy Thread nào đang chạy mà trong DB có enable =0, thì sẽ Kill thread đang chạy đó (có vẻ như thead ko kill được nhau, nhưng cơ bản là muốn vậy)
- các đoạn check_service có thể chia nhỏ thành các hàm riêng
ví dụ check_ping_web, check_ping_icmp. Và bổ xung: check 3 lần mỗi lần cách nhau 3 giây, success thì dừng luôn
