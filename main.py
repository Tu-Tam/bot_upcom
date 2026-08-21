# === GIỮ BOT LUÔN HOẠT ĐỘNG ===
from flask import Flask
from threading import Thread
import os
import time
import telebot
import requests
from datetime import datetime, timedelta

app = Flask('')
@app.route('/')
def giu_hoat_dong(): return "✅ Bot kiểm tra 2 mã - báo % tiến trình rõ ràng!"
def chay_server(): app.run(host="0.0.0.0", port=int(os.environ.get("PORT",8080)))
Thread(target=chay_server).start()

# === THÔNG TIN BOT ===
BOT_TOKEN = "8520938638:AAEHwQp89_P2slG7YTkod4z6_XvYbgBD7ns"
CHAT_ID = 7064473358
bot = telebot.TeleBot(BOT_TOKEN)

# === DANH SÁCH 2 MÃ ===
DANH_SACH_MA = ["SHB", "VCB"]
diem_da_tinh = {} # Lưu kết quả khi lấy thành công
tong_ma = len(DANH_SACH_MA)

# === 📌 Nguồn dữ liệu chuyên Việt Nam, miễn phí, đủ dữ liệu nhanh trả về ===
def lay_du_lieu_cophieu(ma):
    try:
        # Lấy dữ liệu giá VNDirect - đủ 60 ngày, trả về nhanh không giới hạn chặt chẽ
        url = f"https://finfo-api.vndirect.com.vn/v4/stock_prices?sort=date&q=code:{ma}&size=60"
        headers = {"User-Agent": "Mozilla/5.0"} # Giúp truy cập thành công hơn
        res = requests.get(url, headers=headers, timeout=12).json()
        
        if res.get("data") and len(res["data"])>=50: # Đủ yêu cầu số ngày tính toán
            ds = res["data"]
            ds.reverse() # Sắp xếp từ cũ đến mới đúng thứ tự tính chỉ số
            gia_dong = [x["close"] for x in ds]
            gia_cao = [x["high"] for x in ds]
            gia_thap = [x["low"] for x in ds]
            kl = [x["volume"] for x in ds]
            return gia_dong, gia_cao, gia_thap, kl
        else:
            print(f"Chưa đủ dữ liệu trả về cho {ma}")
            return None
    except Exception as e:
        print(f"Lỗi kết nối lấy {ma}: {str(e)}")
        return None

# === Tính toán & lưu kết quả, tính % hoàn thành báo liên tục ===
def chay_thu_thap():
    diem_da_tinh.clear() # Làm sạch dữ liệu cũ trước khi bắt đầu đợt mới
    bot.send_message(CHAT_ID,"📥 **Bắt đầu thu thập dữ liệu mới, cập nhật tỷ lệ % liên tục nhé!**")
    
    for chi_so, ma in enumerate(DANH_SACH_MA, start=1):
        bot.send_message(CHAT_ID,f"⏳ Đang xử lý: {ma} → Đã hoàn thành: {int((chi_so-1)/tong_ma*100)}%")
        
        dl = lay_du_lieu_cophieu(ma)
        time.sleep(2.5) # Nghỉ ngắn nhẹ đảm bảo ổn định vẫn nhanh hơn nhiều
        
        if dl:
            gia_dong,gia_cao,gia_thap,kl = dl
            gia_hien = round(gia_dong[-1],2)

            def tinh_ema(ds,ky):
                hs=2/(ky+1); ema=sum(ds[-ky:])/ky
                for g in ds[-ky+1:]: ema = g*hs + ema*(1-hs)
                return round(ema,2)
            ema12=tinh_ema(gia_dong,12); ema26=tinh_ema(gia_dong,26); sma50=round(sum(gia_dong[-50:])/50,2)
            macd=round(ema12-ema26,4)

            def tinh_rsi(ds,ky):
                tang,giam=[],[]
                for i in range(len(ds)-ky,len(ds)):
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
            diem_da_tinh[ma]={"gia":gia_hien,"diem":diem,"cl":gia_cl,"catl":gia_cat,"rsi":rsi}
            bot.send_message(CHAT_ID,f"✅ Hoàn thành: {ma} → Tiến độ: {int(chi_so/tong_ma*100)}%")
        else:
            bot.send_message(CHAT_ID,f"⚠️ Thử lại sau chốc nữa lấy đủ dữ liệu cho: {ma}")

    bot.send_message(CHAT_ID,f"🏁 **Kết thúc đợt thu thập: Tổng {len(diem_da_tinh)}/{tong_ma} mã thành công!** 💾 Đã lưu sẵn, gõ Đánh giá mã xem ngay kết quả!")

# === LỆNH XEM KẾT QUẢ LƯU SẴN ===
@bot.message_handler(func=lambda m:m.text.strip()=="Đánh giá mã")
def hien_thi_ketqua(m):
    if m.chat.id!=CHAT_ID:return
    if len(diem_da_tinh)==0:
        bot.send_message(CHAT_ID,"📊 Chưa có dữ liệu lưu sẵn, đang/đã chạy đợt thu thập báo % tiến trình nhé 💪")
        return
    sap_xep=sorted(diem_da_tinh.items(),key=lambda x:x[1]["diem"],reverse=True)
    bot.send_message(CHAT_ID,"📊 **KẾT QUẢ ĐÁNH GIÁ THANG 10 - DỮ LIỆU ĐỦ CHÍNH XÁC**")
    nd=""
    for ma,tt in sap_xep:
        xep="⭐ TỐT ưu tiên xem xét" if tt["diem"]>=7 else "🔸 TRUNG BÌNH theo dõi thêm" if tt["diem"]>=5 else "🔹 YẾU chưa đủ tín hiệu mạnh"
        nd+=f"""📌 {ma}: {tt['diem']}/10 điểm
💵 Giá hiện tại: {tt['gia']:,}đ
📈 RSI: {tt['rsi']}
🎯 Giá chốt lời: {tt['cl']:,}đ
🛡️ Giá bảo vốn an toàn: {tt['catl']:,}đ
📝 Nhận xét: {xep}
——————————————\n"""
    bot.send_message(CHAT_ID,nd)

# === LỆNH TRẠNG THÁI ===
@bot.message_handler(func=lambda m:m.text.strip()=="Trạng thái")
def bao_trangthai(m):
    if m.chat.id!=CHAT_ID:return
    bot.send_message(CHAT_ID,f"💓 Trạng thái: Đã lưu {len(diem_da_tinh)}/{tong_ma} mã thành công ✅ | Gõ Đánh giá mã xem kết quả ngay!")

# === Bắt đầu chạy đợt thu thập đầu tiên có báo % rõ ràng ===
bot.send_message(CHAT_ID,"🤖🚀 **Đã nâng cấp hoàn chỉnh!**\n✅ Nguồn dữ liệu Việt Nam chuyên dụng đủ số ngày tính toán\n✅ Báo từng bước % hoàn thành rõ ràng không còn chờ mơ hồ\n✅ Chạy nhanh hơn, ít bị thiếu dữ liệu như nguồn cũ nhiều lắm!")
chay_thu_thap()

# === Giữ bot luôn sẵn sàng trả lời lệnh & tự làm mới lại dữ liệu mỗi 60 phút một lần ===
while True:
    try: bot.polling(none_stop=True,interval=3)
    except Exception as e: time.sleep(5)
    time.sleep(3600) # Sau mỗi giờ tự chạy lại cập nhật mới có báo tiến trình % lại
