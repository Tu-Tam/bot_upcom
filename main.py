from datetime import datetime # đảm bảo có dòng này ở phần đầu nhập thư viện

@bot.message_handler(func=lambda msg: msg.text.strip()=="Du doan XS")
def tra_ketqua(msg):
    if msg.chat.id != CHAT_ID: return
    bot.send_message(CHAT_ID, "Đang phân tích thống kê 60 ngày gần nhất...")
    top3 = chon_3_so(DU_LIEU)
    
    # === Tự lấy & hiển thị ĐÚNG ngày hôm nay theo múi giờ Việt Nam ===
    from datetime import datetime,timedelta
    gio_vn = datetime.utcnow() + timedelta(hours=7) # +7 giờ chính giờ Việt Nam
    ngay_hien_thi = f"ngày {gio_vn.day} tháng {gio_vn.month} năm {gio_vn.year}"
    
    bot.send_message(CHAT_ID,f"""KẾT QUẢ THỐNG KÊ CHỌN 3 SỐ TIỀM NĂNG NHẤT {ngay_hien_thi}
1. Số: {top3[0][0]} - Xuất hiện {top3[0][1]} lần, đã nghỉ {top3[0][2]} ngày chưa về
2. Số: {top3[1][0]} - Xuất hiện {top3[1][1]} lần, đã nghỉ {top3[1][2]} ngày chưa về
3. Số: {top3[2][0]} - Xuất hiện {top3[2][1]} lần, đã nghỉ {top3[2][2]} ngày chưa về

Lưu ý: Chỉ là kết quả tính theo quy luật thống kê dữ liệu quá khứ, mang tính tham khảo vui, không đảm bảo chính xác tuyệt đối!""")
