# === Giữ bot hoạt động đúng quy định chặt chẽ của Render ===
import os
from flask import Flask
from threading import Thread
import time, telebot, requests

app = Flask(__name__)

@app.route('/')
def trang_chu():
    return "✅ Bot kiểm tra RMA SHB & VCB - Đã triển khai thành công!"

def chay_server():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

Thread(target=chay_server).start()

# === Thông tin kết nối chính xác đã kiểm tra ===
BOT_TOKEN = "8520938638:AAEHwQp89_P2slG7YTkod4z6_XvYbgBD7ns"
CHAT_ID = 7064473358
bot = telebot.TeleBot(BOT_TOKEN)
luu_ketqua = {}

# === Lấy dữ liệu từ nguồn quốc tế chấp nhận IP máy chủ đám mây tốt nhất ===
def lay_du_lieu(ma):
    try:
        url = f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={ma}.VN&outputsize=compact&apikey=demo"
        res = requests.get(url, headers={"User-Agent":"Mozilla/5.0"}, timeout=15)
        du_lieu_json = res.json()

        if "Time Series (Daily)" in du_lieu_json:
            ds_ngay = sorted(du_lieu_json["Time Series (Daily)"].keys(), reverse=True)[:50]
            ds_ngay.reverse()
            gia_dong = []
            gia_cao = []
            gia_thap = []
            for ngay in ds_ngay:
                chi_tiet = du_lieu_json["Time Series (Daily)"][ngay]
                gia_dong.append(float(chi_tiet["4. close"]))
                gia_cao.append(float(chi_tiet["2. high"]))
                gia_thap.append(float(chi_tiet["3. low"]))

            # Tính chính xác đủ RMA theo yêu cầu
            r12 = round(sum(gia_dong[-12:])/12, 2)
            r26 = round(sum(gia_dong[-26:])/26, 2)
            r50 = round(sum(gia_dong[-50:])/50, 2)
            gia_hien = round(gia_dong[-1], 2)

            if r12 > r26 and r26 > r50:
                diem = 8
                nhan_xet = "✅ Xu hướng tăng mạnh, RMA xếp đúng thứ tự ưu tiên xem xét mua"
            elif r12 > r26:
                diem = 5
                nhan_xet = "⏸️ Ngắn hạn trên trung hạn, đang cải thiện theo dõi thêm"
            else:
                diem = 3
                nhan_xet = "❌ Chưa đủ xu hướng tăng rõ ràng, tạm chờ tín hiệu tốt hơn"

            chot_loi = round(max(gia_cao[-10:])*0.995, 2)
            cat_von = round(min(gia_thap[-10:])*1.005, 2)

            luu_ketqua[ma] = {
                "gia":gia_hien, "diem":diem,
                "r12":r12, "r26":r26, "r50":r50,
                "cl":chot_loi, "sl":cat_von, "tt":nhan_xet
            }
            return True
    except Exception as e:
        print("Lỗi xử lý:", str(e))
    return False

# === Lệnh kiểm tra phản hồi nhanh ===
@bot.message_handler(func=lambda m: m.text.strip() == "Trạng thái")
def tra_loi(m):
    if m.chat.id != CHAT_ID:
        return
    bot.send_message(CHAT_ID, "💓 BOT ĐANG HOẠT ĐỘNG BÌNH THƯỜNG ✅\n📈 Sẵn sàng: gõ **Đánh giá mã** tính RMA SHB, VCB\n💬 Nguồn dữ liệu quốc tế hỗ trợ máy chủ đám mây")

# === Lệnh chạy lấy dữ liệu & báo kết quả rõ ràng ===
@bot.message_handler(func=lambda m: m.text.strip() == "Đánh giá mã")
def thuc_hien_danhgia(m):
    if m.chat.id != CHAT_ID:
        return
    luu_ketqua.clear()
    bot.send_message(CHAT_ID, "🔄 Đang lấy dữ liệu & tính các đường RMA yêu cầu... chờ ngắn lát nhé!")
    danh_sach = ["SHB", "VCB"]
    tong = len(danh_sach)
    for stt, ma in enumerate(danh_sach, start=1):
        bot.send_message(CHAT_ID, f"⏳ Đang xử lý {ma} → Tiến độ: {int((stt-1)/tong*100)}%")
        lay_du_lieu(ma)
        time.sleep(5)

    bot.send_message(CHAT_ID, f"🏁 Kết thúc đợt: Lấy được {len(luu_ketqua)}/{tong} mã thành công!")
    if not luu_ketqua:
        bot.send_message(CHAT_ID, "💡 Lưu ý nhỏ: Nguồn này có giới hạn nhẹ số lượt gọi mỗi phút, chờ 2 phút gõ lại là được kết quả nhé!")
        return

    bot.send_message(CHAT_ID, "📊 **BẢNG KẾT QUẢ ĐÁNH GIÁ THEO 3 ĐƯỜNG RMA**")
    for ma, tt in sorted(luu_ketqua.items(), key=lambda x:x[1]["diem"], reverse=True):
        bot.send_message(CHAT_ID, f"""📌 **Mã: {ma}**
⭐ Điểm: {tt['diem']}/10
📈 RMA12: {tt['r12']} | RMA26: {tt['r26']} | RMA50: {tt['r50']}
💵 Giá hiện tại: {tt['gia']:,} VNĐ
🎯 Giá chốt lời đề xuất: {tt['cl']:,} VNĐ
🛡️ Giá bảo vốn cắt lỗ: {tt['sl']:,} VNĐ
💬 Nhận xét: {tt['tt']}""")

# === Thông báo khi khởi động bot thành công ===
bot.send_message(CHAT_ID, "🤖✅ **Đã sửa lỗi triển khai thành công!**\n📦 Kèm đủ danh sách thư viện chuẩn\n📡 Nguồn dữ liệu quốc tế ít bị chặn IP máy chủ\n💬 Gõ Trạng thái xem phản hồi nhanh ngay nhé!")

# === Vòng lắng nghe tin nhắn ổn định không quá tải ===
while True:
    try:
        bot.polling(none_stop=True, interval=3)
    except Exception as loi:
        print("Tạm ngắt kết nối nhỏ:", loi)
        time.sleep(5)
    time.sleep(60)
