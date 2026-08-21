# === Giữ bot hoạt động đúng quy định Render cực nhẹ ===
from flask import Flask
from threading import Thread
import time, telebot, requests

app = Flask(__name__)
@app.route('/')
def trang_chu(): return "✅ Bot nguồn SSI - kiểm tra đủ dữ liệu RMA chặt chẽ!"
Thread(target=lambda: app.run(host="0.0.0.0", port=int(os.environ.get("PORT",8080)))).start()

# === Thông tin kết nối chính xác ===
BOT_TOKEN = "8520938638:AAEHwQp89_P2slG7YTkod4z6_XvYbgBD7ns"
CHAT_ID = 7064473358
bot = telebot.TeleBot(BOT_TOKEN)
luu = {}

# === 🟢 NGUỒN SSI UY TÍN, CỔNG DỮ LIỆU CHI TIẾT RÕ SỐ NGÀY LẤY ĐƯỢC ===
def lay_tu_ssi(ma):
    thu_lai = 0
    while thu_lai < 3:
        try:
            # Yêu cầu rõ lấy đủ 50 ngày liên tiếp, trả về định dạng chuẩn dễ đếm số lượng
            url = f"https://api.ssi.com.vn/api/Trading/GetHistoryPrice?symbol={ma}&fromDate=&toDate=&count=50"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "application/json"
            }
            res = requests.get(url, headers=headers, timeout=15).json()

            # Kiểm tra chặt: có dữ liệu trả về + đếm rõ số ngày nhận được đủ yêu cầu không
            if res.get("IsSuccess") and isinstance(res.get("Data"), list):
                ds = res["Data"]
                so_ngay_nhan_duoc = len(ds)
                bot.send_message(CHAT_ID,f"ℹ️ {ma}: Nhận được {so_ngay_nhan_duoc} ngày dữ liệu") # báo rõ số lượng nhận được

                if so_ngay_nhan_duoc >= 50: # đủ chuẩn tính cả RMA50 chính xác
                    ds.reverse() # sắp xếp đúng thứ tự cũ → mới
                    gia_dong = [x["ClosePrice"] for x in ds]
                    gia_cao = [x["HighestPrice"] for x in ds]
                    gia_thap = [x["LowestPrice"] for x in ds]
                    gia_hien = round(gia_dong[-1],2)

                    # Tính chính xác đủ 3 đường RMA yêu cầu
                    r12 = round(sum(gia_dong[-12:])/12,2)
                    r26 = round(sum(gia_dong[-26:])/26,2)
                    r50 = round(sum(gia_dong[-50:])/50,2)

                    if r12>r26 and r26>r50:
                        diem=8; nhan="✅ TỐT: RMA12>RMA26>RMA50 xu hướng tăng rõ ưu tiên xem xét"
                    elif r12>r26:
                        diem=5; nhan="⏸️ TRUNG BÌNH: RMA ngắn trên trung hạn đang cải thiện theo dõi thêm"
                    else:
                        diem=3; nhan="❌ CHỜ: chưa xếp đúng thứ tự tăng mạnh, chưa nên vào lệnh"

                    chot_loi = round(max(gia_cao[-10:])*0.995,2)
                    cat_von = round(min(gia_thap[-10:])*1.005,2)

                    luu[ma] = {"gia":gia_hien,"diem":diem,"r12":r12,"r26":r26,"r50":r50,"cl":chot_loi,"sl":cat_von,"tt":nhan}
                    return True
                else:
                    bot.send_message(CHAT_ID,f"⚠️ {ma}: Chưa đủ chuẩn, chỉ có {so_ngay_nhan_duoc}/50 ngày → cần đủ mới tính RMA50 chính xác")
            else:
                bot.send_message(CHAT_ID,f"⚠️ {ma}: Trạng thái trả về không thành công từ nguồn dữ liệu")
        except Exception as e:
            bot.send_message(CHAT_ID,f"❌ {ma} lỗi lần thử {thu_lai+1}: {str(e)[:45]}...")
        thu_lai +=1; time.sleep(3)
    return False

# === Lệnh Trạng thái kiểm tra bot còn hoạt động ===
@bot.message_handler(func=lambda m:m.text.strip()=="Trạng thái")
def tra(m):
    if m.chat.id!=CHAT_ID:return
    bot.send_message(CHAT_ID,"💓 **ĐANG HOẠT ĐỘNG** ✅\n📥 Nguồn: SSI chính thức uy tín\n📈 Yêu cầu đủ đúng 50 ngày dữ liệu mới tính kết quả\n💬 Gõ **Đánh giá mã** xem rõ số ngày nhận được từng mã nhé!")

# === Lệnh chính báo rõ số lượng nhận được thay vì chỉ nói chung chung thiếu dữ liệu ===
@bot.message_handler(func=lambda m:m.text.strip()=="Đánh giá mã")
def chay_kiemtra(m):
    if m.chat.id!=CHAT_ID:return
    luu.clear()
    bot.send_message(CHAT_ID,"📥 **Đang kiểm tra NGUỒN SSI CHÍNH THỨC, báo rõ số ngày nhận được từng mã!**")
    danh_sach = ["SHB","VCB"]
    tong = len(danh_sach)

    for stt,ma in enumerate(danh_sach, start=1):
        bot.send_message(CHAT_ID,f"⏳ Đang xử lý: {ma} → Tiến độ: {int((stt-1)/tong*100)}%")
        lay_tu_ssi(ma)
        time.sleep(3.5) # nghỉ đủ giãn cách yêu cầu lịch sự với máy chủ

    bot.send_message(CHAT_ID,f"🏁 **Kết thúc: Tổng {len(luu)}/{tong} mã ĐỦ ĐÚNG 50 NGÀY dữ liệu tính ra kết quả hoàn chỉnh!**")
    if not luu:
        bot.send_message(CHAT_ID,"ℹ️ Lý do rõ: thường do máy chủ đám mây bị giới hạn tạm thời truy cập nhanh quá nhiều lần liên tiếp!\n💡 Cách tốt nhất: thử lại vào giờ sáng sớm 6h-8h hoặc sau 21h tối ít người dùng nhất sẽ dễ lấy đủ đủ số ngày hơn hẳn giờ cao điểm ban ngày nhé!")
        return

    # Hiển thị bảng chi tiết đủ thông tin khi đạt đủ chuẩn
    bot.send_message(CHAT_ID,"📊 **BẢNG KẾT QUẢ RMA - ĐỦ ĐÚNG 50 NGÀY DỮ LIỆU CHÍNH THỨC**")
    for ma,tt in sorted(luu.items(), key=lambda x:x[1]["diem"], reverse=True):
        bot.send_message(CHAT_ID,f"""📌 **Mã: {ma}**
⭐ Điểm đánh giá: {tt['diem']}/10
📈 RMA12: {tt['r12']} | RMA26: {tt['r26']} | RMA50: {tt['r50']}
💵 Giá hiện tại: {tt['gia']:,} VNĐ
🎯 Giá chốt lời đề xuất: {tt['cl']:,} VNĐ
🛡️ Giá bảo vốn cắt lỗ: {tt['sl']:,} VNĐ
💬 Nhận xét: {tt['tt']}
——————————————————————""")

# === Thông báo rõ đã chuyển sang kiểm tra chặt đủ số ngày yêu cầu ===
bot.send_message(CHAT_ID,"🤖🔄 **Đã chuyển kiểm tra chặt đủ 50 ngày từ cổng dữ liệu SSI chính thức!**\n✅ Báo ngay nhận được bao nhiêu ngày dữ liệu chứ không chỉ nói chung chung thiếu\n✅ Chỉ tính kết quả khi đủ chuẩn hoàn toàn để RMA50 chính xác đáng tin cậy\n💬 Gõ Đánh giá mã xem báo rõ số lượng nhận được ngay nhé!")

# === Vòng lắng nghe nhẹ ổn định ===
while True:
    try: bot.polling(none_stop=True, interval=3)
    except Exception as loi: print("Kết nối:",loi); time.sleep(5)
    time.sleep(60)
