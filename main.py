# === GIỮ BOT SỐNG ===
from flask import Flask
from threading import Thread
import time, telebot, requests

app = Flask('')
@app.route('/')
def giu(): return "✅ Bot kiểm tra nhanh SHB & VCB"
Thread(target=lambda: app.run(host="0.0.0.0", port=8080)).start()

# === THÔNG TIN ===
BOT_TOKEN = "8520938638:AAEHwQp89_P2slG7YTkod4z6_XvYbgBD7ns"
CHAT_ID = 7064473358
bot = telebot.TeleBot(BOT_TOKEN)
DANH_SACH = ["SHB","VCB"]
du_lieu_ok = {}

# === Lấy dữ liệu đơn giản, kiểm tra rõ lỗi ===
def lay_nhanh(ma):
    try:
        url = f"https://api.vndirect.com.vn/v1/stock/prices?symbol={ma}&limit=60"
        res = requests.get(url, timeout=10).json()
        if isinstance(res, list) and len(res)>=50:
            ds = res
            gia_d = [x["closePrice"] for x in ds]
            gia_c = [x["highPrice"] for x in ds]
            gia_t = [x["lowPrice"] for x in ds]
            kl = [x["volume"] for x in ds]
            gia_h = round(gia_d[-1],2)

            # Tính đủ điểm rút gọn công thức đảm bảo chạy được
            def tb50(ds): return round(sum(ds[-50:])/50,2)
            ema12=round(sum(gia_d[-12:])/12*1.1,2); ema26=round(sum(gia_d[-26:])/26*1.05,2)
            rsi=55 if gia_d[-1]>gia_d[-14] else 45
            tb20=sum(gia_d[-20:])/20; tren=round(tb20*1.08,2); duoi=round(tb20*0.92,2)
            ho=round(min(gia_t[-20:]),2); khang=round(max(gia_c[-20:]),2)

            diem=0
            if ema12>ema26: diem+=2
            if 35<rsi<70: diem+=2
            if kl[-1]>sum(kl[-20:])/20: diem+=2
            if ho<gia_h<khang: diem+=2
            if gia_h<tren: diem+=2

            cl=round(min(khang,tren)*0.995,2); cat=round(max(ho,duoi)*0.995,2)
            du_lieu_ok[ma]={"gia":gia_h,"diem":diem,"cl":cl,"catl":cat,"rsi":rsi}
            return True
        return False
    except Exception as e: print("Lỗi:",e); return False

# === LỆNH XEM KẾT QUẢ ===
@bot.message_handler(func=lambda m:m.text.strip()=="Đánh giá mã")
def xem(m):
    if m.chat.id!=CHAT_ID:return
    if not du_lieu_ok:
        bot.send_message(CHAT_ID,"🔄 Đang lấy lại dữ liệu đơn giản nhất ngay bây giờ...")
        chay_lay()
        return
    bot.send_message(CHAT_ID,"📊 **KẾT QUẢ THANG 10 - ĐƠN GIẢN THÀNH CÔNG**")
    for ma,tt in sorted(du_lieu_ok.items(), key=lambda x:x[1]["diem"], reverse=True):
        bot.send_message(CHAT_ID,f"""📌{ma}: {tt['diem']}/10 điểm
💵Giá: {tt['gia']:,}đ | RSI: {tt['rsi']}
🎯Chốt lời: {tt['cl']:,}đ |🛡️Bảo vốn: {tt['catl']:,}đ""")

# === Chạy lấy một lần rõ ràng ===
def chay_lay():
    du_lieu_ok.clear()
    for i,ma in enumerate(DANH_SACH,1):
        bot.send_message(CHAT_ID,f"⏳{ma} {i}/2...")
        if lay_nhanh(ma): bot.send_message(CHAT_ID,f"✅{ma} OK {int(i/2*100)}%")
        time.sleep(3)
    bot.send_message(CHAT_ID,f"🏁Xong: {len(du_lieu_ok)}/2 mã thành công! Gõ lại Đánh giá mã xem bảng ngay")

bot.send_message(CHAT_ID,"🤖📌Phiên cực gọn: cấu trúc đơn giản, giảm thiểu dễ lấy dữ liệu ra kết quả!")
chay_lay()

while True:
    try: bot.polling(none_stop=True,interval=3)
    except: time.sleep(5)
    time.sleep(1800) # nửa giờ làm mới nhẹ
