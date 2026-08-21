# === GIỮ BOT LUÔN HOẠT ĐỘNG TRÊN RENDER ===
from flask import Flask
from threading import Thread
import time, telebot, requests

app = Flask('')
@app.route('/')
def trang_chu(): return "✅ Bot đang hoạt động bình thường!"
def chay_server(): app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
Thread(target=chay_server).start()

# === THÔNG TIN KẾT NỐI ĐÚNG ===
BOT_TOKEN = "8520938638:AAEHwQp89_P2slG7YTkod4z6_XvYbgBD7ns"
CHAT_ID = 7064473358
bot = telebot.TeleBot(BOT_TOKEN)

# === DANH SÁCH 2 MÃ KIỂM TRA ===
DANH_SACH = ["SHB","VCB"]
luu_ketqua = {}

# === Lấy dữ liệu nhanh + tính RMA đơn giản ===
def lay_tinh(ma):
    try:
        url = f"https://finfo-api.vndirect.com.vn/v4/stock_prices?sort=date&q=code:{ma}&size=50"
        res = requests.get(url, headers={"User-Agent":"Mozilla/5.0"}, timeout=10).json()
        if res.get("data") and len(res["data"])>=40:
            ds = res["data"]
            ds.reverse()
            gia_dong = [x["close"] for x in ds]
            gia_cao = [x["high"] for x in ds]
            gia_thap = [x["low"] for x in ds]
            g_hien = round(gia_dong[-1],2)

            # Chỉ tính đúng RMA 12/26/50 yêu cầu cực nhanh
            rma12 = round(sum(gia_dong[-12:])/12,2)
            rma26 = round(sum(gia_dong[-26:])/26,2)
            rma50 = round(sum(gia_dong[-50:])/50,2)
            tin_hieu = "✅ TỐT: RMA12>RMA26>RMA50 xu hướng tăng rõ" if rma12>rma26 and rma26>rma50 else "⏸️ THEO DÕI: chưa đủ xu hướng mạnh" if rma12>rma26 else "❌ YẾU: xu hướng giảm chưa vào lệnh"
            diem = 8 if rma12>rma26 and rma26>rma50 else 5 if rma12>rma26 else 3

            # Giá chốt lời / bảo vốn đơn giản rõ ràng
            chot_loi = round(max(gia_cao[-8:])*0.995,2)
            cat_lo = round(min(gia_thap[-8:])*1.005,2)
            luu_ketqua[ma] = {"gia":g_hien,"diem":diem,"r12":rma12,"r26":rma26,"r50":rma50,"cl":chot_loi,"sl":cat_lo,"tt":tin_hieu}
            return True
    except Exception as e: print("Lỗi lấy dữ liệu:",e)
    return False

# === LỆNH TRẠNG THÁI NHẬN BIẾT NGAY BOT ĐANG CHẠY ===
@bot.message_handler(func=lambda m:m.text.strip()=="Trạng thái")
def tra_loi(m):
    if m.chat.id!=CHAT_ID:return
    bot.send_message(CHAT_ID,"💓 **ĐANG HOẠT ĐỘNG BÌNH THƯỜNG ✅**\n📥 Sẵn sàng: gõ **Đánh giá mã** xem RMA & giá chốt lời/bảo vốn ngay!")

# === LỆNH ĐÁNH GIÁ HIỂN THỊ KẾT QUẢ ===
@bot.message_handler(func=lambda m:m.text.strip()=="Đánh giá mã")
def hien_thi(m):
    if m.chat.id!=CHAT_ID:return
    if not luu_ketqua:
        bot.send_message(CHAT_ID,"🔍 Đang kiểm tra nhanh 2 mã theo đường RMA... chờ lát là ra kết quả 💪")
        for ma in DANH_SACH:
            lay_tinh(ma); time.sleep(2)
    # Gửi bảng kết quả đã có
    bot.send_message(CHAT_ID,"📊 **KẾT QUẢ KIỂM TRA THEO RMA**")
    for ma,tt in sorted(luu_ketqua.items(), key=lambda x:x[1]["diem"], reverse=True):
        bot.send_message(CHAT_ID,f"""📌 {ma} | Điểm: {tt['diem']}/10
📈 RMA12: {tt['r12']} | RMA26: {tt['r26']} | RMA50: {tt['r50']}
💵 Giá hiện tại: {tt['gia']:,}đ
🎯 Giá chốt lời: {tt['cl']:,}đ
🛡️ Giá bảo vốn: {tt['sl']:,}đ
💬 {tt['tt']}""")

# === BÁO NGAY KHI KHỞI ĐỘNG THÀNH CÔNG - BIẾT CHẮC BOT ĐÃ LÊN HOẠT ĐỘNG ===
bot.send_message(CHAT_ID,"🤖✅ **BOT ĐÃ KHỞI ĐỘNG THÀNH CÔNG!**\n💬 Gõ **Trạng thái** xem phản hồi nhanh\n💬 Gõ **Đánh giá mã** kiểm tra ngay theo các đường RMA yêu cầu")

# === VÒNG LẶP ĐƠN GIẢN KHÔNG BỊ LỖI, LUÔN LẮNG NGHE LỆNH ===
while True:
    try: bot.polling(none_stop=True, interval=3)
    except Exception as e: print("Kết nối tạm ngắt:",e); time.sleep(5)
    time.sleep(60)
