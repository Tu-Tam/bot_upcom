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
def giu_hoat_dong(): return "✅ Bot đang chạy kiểm tra nhanh 2 mã!"
def chay_server(): app.run(host="0.0.0.0", port=int(os.environ.get("PORT",8080)))
Thread(target=chay_server).start()

# === THÔNG TIN BOT ===
BOT_TOKEN = "8520938638:AAEHwQp89_P2slG7YTkod4z6_XvYbgBD7ns"
CHAT_ID = 7064473358
bot = telebot.TeleBot(BOT_TOKEN)

# === ✅ CHỈ 2 MÃ CẦN KIỂM TRA, ĐỊNH DẠNG ĐÚNG CHO NGUỒN ===
DANH_SACH_MA = ["SHB.VN", "VCB.VN"] # Thêm đuôi .VN nhận đúng dữ liệu cổ phiếu Việt Nam

# === LƯU KẾT QUẢ ===
diem_da_tinh = {}
trang_thai = {ma:"CHO_DOI" for ma in DANH_SACH_MA}
vi_tri_dang_giu = {}

# === 📌 Lấy dữ liệu đơn giản từ nguồn miễn phí không giới hạn chặt chẽ ===
def lay_du_lieu_gia(ma):
    try:
        # Sử dụng nguồn dữ liệu thay thế dễ lấy hơn Alpha Vantage
        url = f"https://api.polygon.io/v2/aggs/ticker/{ma}/range/1/day/2026-07-01/2026-08-21?apiKey=UuL7gF8RqX2ZtO8d9sT6wY7aP5bN4m2"
        res = requests.get(url, timeout=10).json()
        if res.get("results"):
            ds = res["results"][:60] # lấy 60 ngày gần nhất
            ds.reverse() # sắp xếp cũ đến mới
            gia_dong = [x["c"] for x in ds]
            gia_cao = [x["h"] for x in ds]
            gia_thap = [x["l"] for x in ds]
            kl = [x["v"] for x in ds]
            return gia_dong,gia_cao,gia_thap,kl
        else: return None
    except Exception as e: print(f"Lỗi lấy dữ liệu: {e}"); return None

# === Tính điểm thang 10 giữ nguyên công thức chuẩn ===
def phan_tich_va_luu(ma_goc, ma_nguon):
    dl = lay_du_lieu_gia(ma_nguon)
    if not dl: return None
    gia_dong,gia_cao,gia_thap,kl = dl
    gia_hien = round(gia_dong[-1],2) # giá cuối cùng mới nhất

    def tinh_ema(ds,ky):
        hs=2/(ky+1); ema=sum(ds[:ky])/ky
        for g in ds[ky:]: ema=g*hs+ema*(1-hs)
        return round(ema,2)
    ema12=tinh_ema(gia_dong,12); ema26=tinh_ema(gia_dong,26); sma50=round(sum(gia_dong[-50:])/50,2)
    macd=round(ema12-ema26,4); tin_hieu=tinh_ema([macd]*9,9)

    def tinh_rsi(ds,ky):
        tang,giam=[],[]
        for i in range(len(ds)-ky,len(ds)):
            cl=ds[i]-ds[i-1]; tang.append(cl if cl>0 else 0); giam.append(-cl if cl<0 else 0)
        bt=sum(tang)/ky; bg=sum(giam)/ky
        return 100 if bg==0 else 0 if bt==0 else round(100-(100/(1+bt/bg)),2)
    rsi=tinh_rsi(gia_dong,14)

    sma20=sum(gia_dong[-20:])/20; dl_chuan=round(((sum((x-sma20)**2 for x in gia_dong[-20:])/20))**0.5,2)
    tren_boll=round(sma20+2*dl_chuan,2); duoi_boll=round(sma20-2*dl_chuan,2)
    ho_tro=round(min(gia_thap[-20:]),2); khang_cu=round(max(gia_cao[-20:]),2); kl_tb=round(sum(kl[-20:])/20)

    diem=0
    if ema12>ema26 and ema26>sma50:diem+=2
    if macd>tin_hieu and macd>0:diem+=2
    if 35<rsi<70:diem+=2
    if kl[-1]>kl_tb*1.03:diem+=2
    if ho_tro<gia_hien<khang_cu and gia_hien<tren_boll:diem+=2

    gia_cl=round(min(khang_cu,tren_boll)*0.995,2); gia_cat=round(max(ho_tro,duoi_boll)*0.995,2)
    ket_qua={"gia":gia_hien,"diem":diem,"cl":gia_cl,"catl":gia_cat,"rsi":rsi}
    diem_da_tinh[ma_goc]=ket_qua
    print(f"✅ Đã tính xong & lưu {ma_goc} thành công!")
    return ket_qua

# === LỆNH XEM KẾT QUẢ ===
@bot.message_handler(func=lambda m:m.text.strip()=="Đánh giá mã")
def hien_thi(m):
    if m.chat.id!=CHAT_ID:return
    if len(diem_da_tinh)==0:
        bot.send_message(CHAT_ID,"⏳ Đang lấy dữ liệu bằng nguồn mới ít chặn hơn, chỉ chờ ngắn lát là có kết quả ngay 💪")
        return
    sap_xep=sorted(diem_da_tinh.items(),key=lambda x:x[1]["diem"],reverse=True)
    bot.send_message(CHAT_ID,"📊 **KẾT QUẢ 2 MÃ SHB & VCB - Thang điểm 10**")
    nd=""
    for ma,tt in sap_xep:
        xep="⭐ TỐT ưu tiên xem xét" if tt["diem"]>=7 else "🔸 TRUNG BÌNH theo dõi thêm" if tt["diem"]>=5 else "🔹 YẾU chưa đủ tín hiệu"
        nd+=f"""📌 {ma}: {tt['diem']}/10 điểm
💵 Giá hiện tại: {tt['gia']:,}đ
📈 RSI: {tt['rsi']}
🎯 Giá chốt lời: {tt['cl']:,}đ
🛡️ Giá bảo vốn: {tt['catl']:,}đ
📝 Nhận xét: {xep}
——————————————\n"""
    bot.send_message(CHAT_ID,nd)

# === LỆNH TRẠNG THÁI ===
@bot.message_handler(func=lambda m:m.text.strip()=="Trạng thái")
def tt(m):
    if m.chat.id!=CHAT_ID:return
    bot.send_message(CHAT_ID,f"💓 Đang chạy nguồn dữ liệu thay thế kiểm tra nhanh | Đã lưu được {len(diem_da_tinh)}/2 mã")

# === CHẠY LẦN LẦU TÍNH LƯU RỒI NGHỈ ===
bot.send_message(CHAT_ID,"🤖✅ Đã chuyển dùng nguồn dữ liệu khác ít bị giới hạn chặn tốc độ hơn!\n⚡ Chỉ 2 mã nên lấy nhanh hơn hẳn, chờ ngắn lát là xem được kết quả Đánh giá mã ngay nhé!")

# Chạy một lượt lấy đủ lưu xong rồi giữ dữ liệu hiển thị khi gọi lệnh
phan_tich_va_luu("SHB","SHB.VN")
time.sleep(3)
phan_tich_va_luu("VCB","VCB.VN")

while True:
    time.sleep(60) # giữ bot sống, dữ liệu đã lưu sẵn gọi lệnh là hiển thị ra ngay
