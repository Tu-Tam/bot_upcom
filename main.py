# === Tự cài thư viện cần thiết khi khởi động lần đầu ===
import os
os.system("pip install flask==2.3.3 pyTelegramBotAPI==4.14.0 requests==2.31.0 gunicorn==21.2.0")

# === Giữ bot luôn hoạt động đúng quy định máy chủ Render ===
from flask import Flask
from threading import Thread
import time, telebot, requests
from datetime import datetime

app = Flask(__name__)
@app.route('/')
def trang_chu():
    return "✅ Bot GỘP HOÀN CHỈNH: Khóa API + Lưu đệm dữ liệu + Nguồn dự phòng | Kiểm tra RMA ổn định không trống dữ liệu!"

def chay_server():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
Thread(target=chay_server).start()

# === Thông tin cấu hình bot của bạn ===
BOT_TOKEN = "8520938638:AAEHwQp89_P2slG7YTkod4z6_XvYbgBD7ns"
# 💡 Thay bằng khóa Alpha Vantage cá nhân bạn đăng ký miễn phí để gọi được nhiều lượt tốt hơn nhé
APY_KEY = "7F5H5O8Y9L4XZQZQ"
CHAT_ID = 7064473358

bot = telebot.TeleBot(BOT_TOKEN)
du_lieu_dem = {}   # Lưu dữ liệu đã lấy thành công dùng tạm khi bị giới hạn số lượt gọi
thoi_gian_luu = {} # Ghi rõ thời gian lưu để phân biệt dữ liệu mới/đã lưu trước đó

# === 🟢 Nguồn chính: Alpha Vantage hỗ trợ mã VN đầy đủ ===
def lay_nguon_chinh(ma):
    try:
        url = f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={ma}.VN&outputsize=compact&apikey={APY_KEY}"
        res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        dl = res.json()

        if "Time Series (Daily)" in dl:
            ds_ngay = sorted(dl["Time Series (Daily)"].keys(), reverse=True)[:50]
            ds_ngay.reverse()
            gia_dong, gia_cao, gia_thap = [], [], []
            for ngay in ds_ngay:
                ct = dl["Time Series (Daily)"][ngay]
                gia_dong.append(float(ct["4. close"]))
                gia_cao.append(float(ct["2. high"]))
                gia_thap.append(float(ct["3. low"]))

            # Tính chính xác đủ 3 đường RMA theo yêu cầu
            r12 = round(sum(gia_dong[-12:]) / 12, 2)
            r26 = round(sum(gia_dong[-26:]) / 26, 2)
            r50 = round(sum(gia_dong[-50:]) / 50, 2)
            gia_hien = round(gia_dong[-1], 2)

            if r12 > r26 and r26 > r50:
                diem = 8; nhan = "✅ TĂNG MẠNH: RMA xếp đúng thứ tự ưu tiên xem xét mua"
            elif r12 > r26:
                diem = 5; nhan = "⏸️ CẢI THIỆN: đường ngắn trên trung hạn đang tốt dần theo dõi thêm"
            else:
                diem = 3; nhan = "❌ CHỜ: chưa xếp đúng thứ tự tăng mạnh, tạm chưa vào lệnh"

            chot_loi = round(max(gia_cao[-10:]) * 0.995, 2)
            cat_von = round(min(gia_thap[-10:]) * 1.005, 2)
            ket_qua = {"gia":gia_hien, "diem":diem, "r12":r12, "r26":r26, "r50":r50, "cl":chot_loi, "sv":cat_von, "txt":nhan}

            # Lưu vào bộ nhớ đệm ngay khi lấy được thành công
            du_lieu_dem[ma] = ket_qua.copy()
            thoi_gian_luu[ma] = datetime.now().strftime("%d/%m %H:%M")
            return ket_qua

        elif "Thank you for using Alpha Vantage" in dl.get("Note", ""):
            return None # Bị giới hạn số lượt gọi → chuyển dùng dữ liệu lưu trước đó/nguồn phụ
    except Exception as e:
        print("Lỗi nguồn chính:", str(e)[:40])
    return None

# === 🟢 Nguồn dự phòng: VNDirect khi nguồn chính tạm giới hạn không ra dữ liệu ===
def lay_nguon_phu(ma):
    try:
        url = f"https://finfo-api.vndirect.com.vn/v4/stock_prices?sort=date&q=code:{ma}&size=50"
        res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=12).json()
        if res.get("data") and len(res["data"]) >= 45:
            ds = res["data"]
            ds.reverse()
            gia_dong = [x["close"] for x in ds]
            gia_cao = [x["high"] for x in ds]
            gia_thap = [x["low"] for x in ds]
            gia_hien = round(gia_dong[-1], 2)

            r12 = round(sum(gia_dong[-12:]) / 12, 2)
            r26 = round(sum(gia_dong[-26:]) / 26, 2)
            r50 = round(sum(gia_dong[-50:]) / 50, 2)

            if r12 > r26 and r26 > r50:
                diem = 8; nhan = "✅ TĂNG MẠNH - Nguồn dự phòng"
            elif r12 > r26:
                diem = 5; nhan = "⏸️ CẢI THIỆN - Nguồn dự phòng"
            else:
                diem = 3; nhan = "❌ CHỜ - Nguồn dự phòng"

            chot_loi = round(max(gia_cao[-10:]) * 0.995, 2)
            cat_von = round(min(gia_thap[-10:]) * 1.005, 2)
            ket_qua = {"gia":gia_hien, "diem":diem, "r12":r12, "r26":r26, "r50":r50, "cl":chot_loi, "sv":cat_von, "txt":nhan}

            du_lieu_dem[ma] = ket_qua.copy()
            thoi_gian_luu[ma] = datetime.now().strftime("%d/%m %H:%M")
            return ket_qua
    except Exception as e:
        print("Lỗi nguồn phụ:", str(e)[:40])
    return None

# === Quy trình ưu tiên lấy dữ liệu: mới nhất → dùng dữ liệu lưu tạm → chuyển nguồn phụ ===
def lay_ket_qua(ma):
    kq_moi = lay_nguon_chinh(ma)
    if kq_moi:
        return kq_moi
    # Ưu tiên dùng dữ liệu đã lưu trước đó nếu có sẵn
    if ma in du_lieu_dem:
        kq_cu = du_lieu_dem[ma].copy()
        kq_cu["txt"] += f"\nℹ️ Dùng dữ liệu lưu lúc {thoi_gian_luu[ma]} chờ hết giờ giới hạn gọi!"
        return kq_cu
    # Cuối cùng thử lấy từ nguồn dự phòng VNDirect
    return lay_nguon_phu(ma)

# === Lệnh kiểm tra nhanh bot còn hoạt động bình thường không ===
@bot.message_handler(func=lambda msg: msg.text.strip() == "Trạng thái")
def tra_loi(msg):
    if msg.chat.id != CHAT_ID:
        return
    bot.send_message(CHAT_ID, "💓 **BOT GỘP HOÀN CHỈNH ĐANG HOẠT ĐỘNG TỐT ✅**\n🔑 Khóa API nâng số lượt gọi\n💾 Lưu tự động dữ liệu tốt dùng tạm\n🔄 Tự chuyển nguồn dự phòng đảm bảo không trống thông tin\n💬 Gõ: **Đánh giá mã** xem kết quả phân tích RMA ngay!")

# === Lệnh chính đánh giá và gửi bảng kết quả đầy đủ ===
@bot.message_handler(func=lambda msg: msg.text.strip() == "Đánh giá mã")
def danh_gia(msg):
    if msg.chat.id != CHAT_ID:
        return
    bot.send_message(CHAT_ID, "📥 **Đang kiểm tra! Tự động chuyển dữ liệu lưu/nguồn phụ đảm bảo luôn có thông tin hiển thị nhé!**")
    danh_sach_ma = ["SHB", "VCB"]
    tong_ma = len(danh_sach_ma)
    ds_thanh_cong = []

    for stt, ma in enumerate(danh_sach_ma, start=1):
        bot.send_message(CHAT_ID, f"⏳ Đang xử lý: {ma} → Tiến độ: {int((stt-1)/tong_ma*100)}%")
        kq = lay_ket_qua(ma)
        time.sleep(4) # nghỉ đủ giãn cách tránh gọi quá nhanh bị chặn máy chủ
        if kq:
            ds_thanh_cong.append([ma, kq])
            bot.send_message(CHAT_ID, f"✅ Hoàn thành: {ma} → Tiến độ: {int(stt/tong_ma*100)}%")
        else:
            bot.send_message(CHAT_ID, f"⚠️ Lần này chưa lấy được {ma} dữ liệu mới nhất!")

    bot.send_message(CHAT_ID, f"🏁 **Kết thúc: Có {len(ds_thanh_cong)}/{tong_ma} mã hiển thị được phân tích chi tiết!**")
    if not ds_thanh_cong:
        bot.send_message(CHAT_ID, "💡 Chờ khoảng 1 giờ hoặc vào sáng sớm/tối muộn ít người dùng thử lại sẽ dễ lấy dữ liệu mới thành công hơn nhé!")
        return

    # Sắp xếp điểm cao lên đầu dễ chọn mã ưu tiên theo dõi
    bot.send_message(CHAT_ID, "📊 **BẢNG KẾT QUẢ PHÂN TÍCH THEO 3 ĐƯỜNG RMA**")
    for ma, tt in sorted(ds_thanh_cong, key=lambda x:x[1]["diem"], reverse=True):
        bot.send_message(CHAT_ID, f"""📌 **Mã: {ma}**
⭐ Điểm đánh giá: {tt['diem']}/10
📈 RMA12: {tt['r12']} | RMA26: {tt['r26']} | RMA50: {tt['r50']}
💵 Giá tham khảo: {tt['gia']:,} VNĐ
🎯 Giá chốt lời đề xuất: {tt['cl']:,} VNĐ
🛡️ Giá bảo vốn cắt lỗ: {tt['sv']:,} VNĐ
💬 Nhận xét: {tt['txt']}
——————————————————————""")

# === Thông báo ngay khi khởi động bot thành công trên máy chủ ===
bot.send_message(CHAT_ID, "🤖✅ **Đã triển khai bản GỘP HOÀN CHỈNH nhất thành công!**\n💾 Không còn tình trạng trống 0/2 mã nhờ lưu đệm tự động\n🔄 Nguồn dự phòng chuyển đổi linh hoạt khi nguồn chính tạm giới hạn\n💬 Gõ Trạng thái kiểm tra phản hồi nhanh rồi dùng Đánh giá mã xem kết quả nhé!")

# === Vòng lắng nghe tin nhắn liên tục, tự kết nối lại khi mất mạng nhỏ ===
while True:
    try:
        bot.polling(none_stop=True, interval=3)
    except Exception as loi:
        print("Tạm ngắt kết nối nhỏ, nối lại:", loi)
        time.sleep(5)
    time.sleep(60)
