# === GIỮ BOT LUÔN HOẠT ĐỘNG ===
from flask import Flask
from threading import Thread
import time, telebot, requests

app = Flask('')
@app.route('/')
def giu(): return "✅ Bot kiểm tra nhanh RMA - đủ giá chốt lời bảo vốn"
Thread(target=lambda: app.run(host="0.0.0.0", port=8080)).start()

# === THÔNG TIN KẾT NỐI ===
BOT_TOKEN = "8520938638:AAEHwQp89_P2slG7YTkod4z6_XvYbgBD7ns"
CHAT_ID = 7064473358
bot = telebot.TeleBot(BOT_TOKEN)
DANH_SACH = ["SHB","VCB"]
tong = len(DANH_SACH)
luu = {}

# === 🚀 LẤY DỮ LIỆU & CHỈ TÍNH RMA ĐỦ ĐIỀU KIỆN THÔI ===
def lay_nhanh(ma):
    try:
        url = f"https://finfo-api.vndirect.com.vn/v4/stock_prices?sort=date&q=code:{ma}&size=50"
        res = requests.get(url, headers={"User-Agent":"Mozilla/5.0"}, timeout=10).json()
        if res.get("data") and len(res["data"])>=40:
            ds = res["data"]
            ds.reverse()
            g_d = [x["close"] for x in ds]
            g_c = [x["high"] for x in ds]
            g_t = [x["low"] for x in ds]
            kl = [x["volume"] for x in ds]
            g_h = round(g_d[-1],2)

            # === CHỈ TÍNH RMA 12,26,50 GỌN NHẤT ===
            rma12 = round(sum(g_d[-12:])/12,2)
            rma26 = round(sum(g_d[-26:])/26,2)
            rma50 = round(sum(g_d[-50:])/50,2)
            tin_hieu = "✅ MUA: RMA tăng đúng thứ tự" if rma12>rma26 and rma26>rma50 else "⏸️ THEO DÕI: chưa mạnh" if rma12>rma26 else "❌ CHỜ: RMA yếu"

            # === Tính đủ chốt lời + bảo vốn đơn giản chính xác ===
            tb20 = sum(g_d[-20:])/20
            tren = round(tb20*1.06,2); duoi = round(tb20*0.94,2)
            chot = round(min(max(g_c[-10:]),tren)*0.995,2)
            von = round(max(min(g_t[-10:]),duoi)*0.995,2)
            diem = 8 if rma12>rma26 and rma26>rma50 else 5 if rma12>rma26 else 3

            luu[ma] = {"gia":g_h,"diem":diem,"rma12":rma12,"rma26":rma26,"rma50":rma50,"chot":chot,"von":von,"tin":tin_hieu}
            return True
        return False
    except: return False

# === THU THẬP BÁO % RÕ RÀNG ===
def chay():
    luu.clear()
    bot.send_message(CHAT_ID,"📥 **Chỉ kiểm tra nhanh RMA, chạy cực nhanh!**")
    for stt,ma in enumerate(DANH_SACH,1):
        bot.send_message(CHAT_ID,f"⏳ {ma} → {int((stt-1)/tong*100)}%")
        if lay_nhanh(ma): bot.send_message(CHAT_ID,f"✅ {ma} OK → {int(stt/tong*100)}%")
        time.sleep(2.5)
    bot.send_message(CHAT_ID,f"🏁 Xong: {len(luu)}/{tong} mã thành công! Gõ Đánh giá mã xem chi tiết RMA ngay")

# === HIỂN THỊ ĐỦ THÔNG TIN RMA + GIÁ ===
@bot.message_handler(func=lambda m:m.text.strip()=="Đánh giá mã")
def xem(m):
    if m.chat.id!=CHAT_ID:return
    if not luu:
        bot.send_message(CHAT_ID,"🔍 Chưa có dữ liệu → đang kiểm tra nhanh RMA ngay bây giờ...")
        chay()
        return
    bot.send_message(CHAT_ID,"📊 **KẾT QUẢ KIỂM TRA RMA NHANH**")
    for ma,tt in sorted(luu.items(), key=lambda x:x[1]["diem"], reverse=True):
        bot.send_message(CHAT_ID,f"""📌 {ma} | Điểm: {tt['diem']}/10
📈 RMA12: {tt['rma12']} | RMA26: {tt['rma26']} | RMA50: {tt['rma50']}
💵 Giá hiện tại: {tt['gia']:,}đ
🎯 Chốt lời: {tt['chot']:,}đ
🛡️ Bảo vốn: {tt['von']:,}đ
💬 {tt['tin']}""")

# === KHỞI ĐỘNG & GIỮ CHẠY ===
bot.send_message(CHAT_ID,"🤖✅ Đã tối ưu chỉ kiểm tra RMA cắt bớt tính toán thừa → cực nhanh ra kết quả!")
chay()
while True:
    try: bot.polling(none_stop=True,interval=3)
    except: time.sleep(5)
    time.sleep(1800)
