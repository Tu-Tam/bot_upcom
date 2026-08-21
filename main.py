# === GIỮ BOT LUÔN THỨC ===
from flask import Flask
from threading import Thread
import os
import time
import telebot
import requests
from datetime import datetime

app = Flask('')
@app.route('/')
def giu_hoat_dong(): return "✅ Bot đang chạy kiểm tra 2 mã cực đơn giản!"
def chay_server(): app.run(host="0.0.0.0", port=int(os.environ.get("PORT",8080)))
Thread(target=chay_server).start()

# === THÔNG TIN BOT ===
BOT_TOKEN = "8520938638:AAEHwQp89_P2slG7YTkod4z6_XvYbgBD7ns"
CHAT_ID = 7064473358
bot = telebot.TeleBot(BOT_TOKEN)

# === CHỈ 2 MÃ CẦN KIỂM TRA ===
DANH_SACH_MA = [("SHB", "SHB.VN"), ("VCB", "VCB.VN")]
diem_da_tinh = {} # Nơi lưu chắc chắn kết quả khi lấy thành công

# === Lấy dữ liệu & tính điểm ===
def lay_tinh_luu(ma_ten, ma_api):
    try:
        url = f"https://api.polygon.io/v2/aggs/ticker/{ma_api}/range/1/day/2026-07-01/2026-08-21?apiKey=UuL7gF8RqX2ZtO8d9sT6wY7aP5bN4m2"
        res = requests.get(url, timeout=12).json()
        if res.get("results") and len(res["results"])>=50:
            ds = res["results"]
            gia_dong = [x["c"] for x in ds]
            gia_cao = [x["h"] for x in ds]
            gia_thap = [x["l"] for x in ds]
            kl = [x["v"] for x in ds]
            gia_hien = round(gia_dong[-1],2)

            def tinh_ema(ds,ky):
                hs=2/(ky+1); ema=sum(ds[-ky:])/ky
                for g in ds[-ky:]: pass
                return round(ema,2)
            ema12=tinh_ema(gia_dong,12); ema26=tinh_ema(gia_dong,26); sma50=round(sum(gia_dong[-50:])/50,2)
            macd=round(ema12-ema26,4)

            def tinh_rsi(ds,ky):
                tang,giam=[],[]
                for i in range(len(ds)-ky+1,len(ds)):
                    cl=ds[i]-ds[i-1]; tang.append(max(cl,0)); giam.append(max(-cl,0))
                bt=sum(tang)/ky; bg=sum(giam)/ky
                return round(100-(100/(1+bt/bg)),2) if bg>0 else 100
            rsi=tinh_rsi(gia_dong,14)

            sma20=sum(gia_dong[-20:])/20; dl_chuan=round(((sum((x-sma20)**2 for x in gia_dong[-20:])/20))**0.5,2)
            tren_boll=round(sma20+2*dl_chuan,2); duoi_boll=round(sma20-2*dl_chuan,2)
            ho_tro=round(min(gia_thap[-20:]),2); khang_cu=round(max(gia_cao[-20:]),2); kl_tb=round(sum(kl[-20:])/20)

            diem=0
            if ema12>ema26 and ema26>sma50:diem+=2
            if macd>0:diem+=2
            if 35<rsi<70:diem+=2
            if kl[-1]>kl_tb*1.03:diem+=2
            if ho_tro<gia_hien<khang_cu and gia_hien<tren_boll:diem+=2

            gia_cl=round(min(khang_cu,tren_boll)*0.995,2); gia_cat=round(max(ho_tro,duoi_boll)*0.995,2)
            diem_da_tinh[ma_ten]={"gia":gia_hien,"diem":diem,"cl":gia_cl,"catl":gia_cat,"rsi":rsi}
            bot.send_message(CHAT_ID,f"✅ Đã lưu thành công {ma_ten} {len(diem_da_tinh)}/2")
        else: bot.send_message(CHAT_ID,f"⚠️ Chưa lấy đủ dữ liệu {ma_ten} thử lại sau chốc nữa")
    except Exception as e: bot.send_message(CHAT_ID,f"❌ Lỗi lấy {ma_ten}: {str(e)[:35]}...")

# === LỆNH ĐÁNH GIÁ: báo rõ chính xác có bao nhiêu đã lưu được ===
@bot.message_handler(func=lambda m:m.text.strip()=="Đánh giá mã")
def hien_ketqua(m):
    if m.chat.id!=CHAT_ID:return
    if len(diem_da_tinh)==0:
        bot.send_message(CHAT_ID,f"📊 Trạng thái: Đang thu thập... mới lưu được {len(diem_da_tinh)}/2 mã hoàn thành 💪")
        return
    sap_xep=sorted(diem_da_tinh.items(),key=lambda x:x[1]["diem"],reverse=True)
    bot.send_message(CHAT_ID,f"📊 **KẾT QUẢ ĐÃ LƯU: {len(diem_da_tinh)}/2 mã thành công**")
    nd=""
    for ma,tt in sap_xep:
        xep="⭐ TỐT" if tt["diem"]>=7 else "🔸TRUNG BÌNH" if tt["diem"]>=5 else "🔹YẾU"
        nd+=f"""📌{ma}:{tt['diem']}/10 điểm
💵Giá:{tt['gia']:,}đ | RSI:{tt['rsi']}
🎯Chốt lời:{tt['cl']:,}đ |🛡️Bảo vốn:{tt['catl']:,}đ
📝{xep}
——————————\n"""
    bot.send_message(CHAT_ID,nd)

# === Bắt đầu chạy lấy dữ liệu một lần rõ ràng có báo từng bước ===
bot.send_message(CHAT_ID,"🤖🚀 Bắt đầu lấy dữ liệu 2 mã, sẽ báo ngay khi lưu được từng mã nhé!")
lay_tinh_luu("SHB","SHB.VN"); time.sleep(4)
lay_tinh_luu("VCB","VCB.VN")

# === Giữ bot sẵn sàng trả lời lệnh ngay khi đã có dữ liệu lưu trong bộ nhớ ===
while True:
    try: bot.polling(none_stop=True,interval=3)
    except Exception as e: time.sleep(5)
    time.sleep(60)
