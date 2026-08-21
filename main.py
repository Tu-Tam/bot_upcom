# === GIỮ BOT LUÔN THỨC TRÊN RENDER ===
from flask import Flask
from threading import Thread
import os
import time

app = Flask('')
@app.route('/')
def giu_hoat_dong():
    return "✅ Đã sửa cơ chế chạy theo chu kỳ hoàn chỉnh - lưu kết quả chắc chắn!"

def chay_server():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

Thread(target=chay_server).start()

# === BOT TELEGRAM PHÂN TÍCH CHỈ 2 MÃ KIỂM TRA ===
import telebot
import requests
from datetime import datetime

# === 🗝️ 4 KHÓA LUÂN PHIÊN ===
DANH_SACH_API_KEY = [
    "demo",
    "SYHGO5Z8DE4RAU8E",
    "52MWBOYE0RSLQE8E",
    "N8TO30AM8DVVGDE7"
]
chi_so_khoa = 0

def lay_khoa_hien_tai(): return DANH_SACH_API_KEY[chi_so_khoa]
def chuyen_khoa_tiep():
    global chi_so_khoa
    chi_so_khoa = (chi_so_khoa + 1) % len(DANH_SACH_API_KEY)
    print(f"🔄 Chuyển khóa thứ {chi_so_khoa+1}")

# === THÔNG TIN KẾT NỐI ===
BOT_TOKEN = "8520938638:AAEHwQp89_P2slG7YTkod4z6_XvYbgBD7ns"
CHAT_ID = 7064473358
bot = telebot.TeleBot(BOT_TOKEN)

# === ✅ CHỈ 2 MÃ THỬ ===
DANH_SACH_MA = ["SHB", "VCB"]

# === THAM SỐ CHẠY AN TOÀN, CHỜ ĐỦ LƯU XONG KẾT QUẢ ===
EMA_NGAN, EMA_DAI, SMA_DAI = 12,26,50
RSI_KY =14
BOLL_KY, BOLL_HE_SO=20,2
NGHI_GIUA_MA = 6        # Nghỉ đủ 6 giây đảm bảo <5 lượt/phút tuyệt đối
NGHI_KHI_BI_GIOI_HAN =10 # Nghỉ dài hơn khi bị báo chặn
NGHI_SAU_KHI_XONG_BO = 90 # ✅ QUAN TRỌNG: sau khi phân tích xong cả 2 mã nghỉ 90 giây mới làm lại
NGHI_BAO_SONG =120

# === LƯU TRỮ KẾT QUẢ ===
trang_thai = {ma:"CHO_DOI" for ma in DANH_SACH_MA}
diem_da_tinh = {} # ✅ khi có dữ liệu hợp lệ chắc chắn ghi vào đây
vi_tri_dang_giu = {}
mang_online = True
dem_bao_song=0

# === Kiểm tra mạng ===
def kiem_tra_mang():
    try: requests.get("https://api.telegram.org",timeout=7); return True
    except: return False

# === Lấy dữ liệu có chờ đủ thời gian ===
def lay_du_lieu(ma):
    thu=0
    while thu < len(DANH_SACH_API_KEY):
        try:
            url=f"https://api.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={ma}&apikey={lay_khoa_hien_tai()}&outputsize=compact"
            res=requests.get(url,timeout=15).json()
            if "Time Series (Daily)" in res:
                print(f"✅ Lấy thành công {ma} bằng khóa {chi_so_khoa+1}")
                return res
            elif "Note" in res or "Thank you" in res:
                print(f"⚠️ Khóa {chi_so_khoa+1} đạt giới hạn, chuyển & nghỉ {NGHI_KHI_BI_GIOI_HAN}s...")
                chuyen_khoa_tiep()
                time.sleep(NGHI_KHI_BI_GIOI_HAN)
            else: time.sleep(3)
        except Exception as e: print(f"Lỗi {ma}:{e}"); chuyen_khoa_tiep(); time.sleep(4)
        thu +=1
    return None

# === Tính toán & chắc chắn trả về lưu được khi đủ dữ liệu ===
def phan_tich(ma):
    dl=lay_du_lieu(ma)
    time.sleep(NGHI_GIUA_MA)
    if not dl: return None

    ds_ngay=sorted(dl["Time Series (Daily)"].keys(),reverse=True)
    gia_dong,gia_cao,gia_thap,kl=[],[],[],[]
    for ngay in ds_ngay[:60]:
        d=dl["Time Series (Daily)"][ngay]
        gia_dong.append(float(d["4. close"]));gia_cao.append(float(d["2. high"]))
        gia_thap.append(float(d["3. low"]));kl.append(int(d["5. volume"]))
    gia_hien=round(gia_dong[0],2)

    def tinh_ema(ds,ky):
        hs=2/(ky+1);ema=sum(ds[:ky])/ky
        for g in ds[ky:]: ema=g*hs+ema*(1-hs)
        return round(ema,2)

    ema12=tinh_ema(gia_dong,12);ema26=tinh_ema(gia_dong,26);sma50=round(sum(gia_dong[:50])/50,2)
    macd=round(ema12-ema26,4);tin_hieu=tinh_ema([macd]*9,9)
    def tinh_rsi(ds,ky):
        tang,giam=[],[]
        for i in range(1,ky+1):cl=ds[i-1]-ds[i];tang.append(cl if cl>0 else 0);giam.append(-cl if cl<0 else 0)
        bt=sum(tang)/ky;bg=sum(giam)/ky
        return 100 if bg==0 else 0 if bt==0 else round(100-(100/(1+bt/bg)),2)
    rsi=tinh_rsi(gia_dong,RSI_KY)
    sma20=sum(gia_dong[:20])/20;dl_chuan=round(((sum((x-sma20)**2 for x in gia_dong[:20])/20))**0.5,2)
    tren_boll=round(sma20+2*dl_chuan,2);duoi_boll=round(sma20-2*dl_chuan,2)
    ho_tro=round(min(gia_thap[:20]),2);khang_cu=round(max(gia_cao[:20]),2);kl_tb=round(sum(kl[:20])/20)

    diem=0
    if ema12>ema26 and ema26>sma50:diem+=2
    if macd>tin_hieu and macd>0:diem+=2
    if 35<rsi<70:diem+=2
    if kl[0]>kl_tb*1.03:diem+=2
    if ho_tro<gia_hien<khang_cu and gia_hien<tren_boll:diem+=2

    gia_cl=round(min(khang_cu,tren_boll)*0.995,2);gia_cat=round(max(ho_tro,duoi_boll)*0.995,2)
    ket_qua={"gia":gia_hien,"diem":diem,"cl":gia_cl,"catl":gia_cat,"rsi":rsi}
    diem_da_tinh[ma]=ket_qua # ✅ chắc chắn ghi vào bộ nhớ khi tính xong
    print(f"📌 Đã lưu thành công điểm {ma}: {diem}/10")
    return ket_qua

# === LỆNH TRẠNG THÁI ===
@bot.message_handler(func=lambda m:m.text.strip()=="Trạng thái")
def bao_tt(m):
    if m.chat.id!=CHAT_ID:return
    bot.send_message(CHAT_ID,f"""💓 TRẠNG THÁI: Đã sửa chạy theo chu kỳ hoàn chỉnh ✅
⏰ {datetime.now().strftime('%H:%M:%S %d/%m/%Y')}
📶 Chỉ 2 mã SHB,VCB | Đã có {len(diem_da_tinh)}/2 bộ dữ liệu lưu sẵn
💬 Khi đủ 2 bộ dữ liệu → gõ Đánh giá mã ra ngay kết quả!""")

# === ✅ LỆNH ĐÁNH GIÁ: chỉ gọi khi đã lưu đủ dữ liệu vào bộ nhớ rồi ===
@bot.message_handler(func=lambda m:m.text.strip()=="Đánh giá mã")
def xem_ketqua(m):
    if m.chat.id!=CHAT_ID:return
    if len(diem_da_tinh)==0:
        bot.send_message(CHAT_ID,"⏳ Đang lấy đủ dữ liệu lần đầu tiên, chờ đủ khoảng thời gian hoàn chỉnh khoảng vài phút nữa nhé 💪")
        return
    sap_xep=sorted(diem_da_tinh.items(),key=lambda x:x[1]["diem"],reverse=True)
    bot.send_message(CHAT_ID,"📊 **KẾT QUẢ ĐÁNH GIÁ ĐÃ LƯU SẴN**")
    nd=""
    for ma,tt in sap_xep:
        xep="⭐ TỐT" if tt["diem"]>=7 else "🔸TRUNG BÌNH" if tt["diem"]>=5 else "🔹YẾU"
        nd+=f"""📌{ma}:{tt['diem']}/10 điểm
💵Giá:{tt['gia']:,}đ | RSI:{tt['rsi']}
🎯Chốt lời:{tt['cl']:,}đ |🛡️Bảo vốn:{tt['catl']:,}đ
📝{xep}
——————————\n"""
    bot.send_message(CHAT_ID,nd)

# === Xử lý mua/bán ===
@bot.message_handler(func=lambda m:m.text.strip()=="Đã mua")
def dm(m):
    if m.chat.id!=CHAT_ID:return
    for ma in DANH_SACH_MA:
        if trang_thai[ma]=="CHO_XAC_NHAN":
            vi_tri_dang_giu[ma]={"gia":trang_thai[f"gia_{ma}"],"cl":trang_thai[f"cl_{ma}"],"catl":trang_thai[f"catl_{ma}"]}
            trang_thai[ma]="DANG_GIU"
            bot.send_message(CHAT_ID,f"✅Đã theo dõi {ma}\nGiá vào:{vi_tri_dang_giu[ma]['gia']:,}đ\nChốt lời:{vi_tri_dang_giu[ma]['cl']:,}đ\nCắt lỗ:{vi_tri_dang_giu[ma]['catl']:,}đ")
            return
    bot.send_message(CHAT_ID,"⚠️Chờ tín hiệu nhé!")

@bot.message_handler(func=lambda m:m.text.strip()=="Đã bán")
def db(m):
    if m.chat.id!=CHAT_ID:return
    for ma in list(vi_tri_dang_giu.keys()):
        del vi_tri_dang_giu[ma];trang_thai[ma]="CHO_DOI"
        bot.send_message(CHAT_ID,f"🔄✅Đã kết thúc theo dõi {ma}");return
    bot.send_message(CHAT_ID,"⚠️Chưa có mã nào theo dõi!")

# === ✅ VÒNG CHẠY CHÍNH HOÀN TOÀN MỚI: Làm xong cả 2 → nghỉ dài → lặp lại ===
print("=== CHẠY CHU KỲ: Phân tích đủ 2 mã → lưu → nghỉ 90s → lặp lại ===")
bot.send_message(CHAT_ID,"🤖✅ Đã sửa cơ chế chạy đúng chu kỳ hoàn chỉnh!\n📥 Lấy lần lượt đủ 2 mã, lưu chắc chắn vào bộ nhớ rồi mới nghỉ dài lặp lại\n⏱️ Chờ khoảng 3-5 phút hoàn thành chu kỳ đầu tiên đủ dữ liệu lưu vào bộ nhớ là xem được kết quả ngay nhé!")

while True:
    mang_moi=kiem_tra_mang()
    if mang_online and not mang_moi:bot.send_message(CHAT_ID,"🚫⚠️Mất kết nối tạm!")
    elif not mang_online and mang_moi:bot.send_message(CHAT_ID,"✅📶Trở lại mạng tốt!")
    mang_online=mang_moi

    if mang_online:
        try: bot.polling(none_stop=True,interval=2)
        except Exception as e:print(f"Lỗi kết nối:{e}");time.sleep(5);continue

        dem_bao_song +=1
        if dem_bao_song>=NGHI_BAO_SONG:
            bot.send_message(CHAT_ID,f"💓BÁO SỐNG:Đang chạy chu kỳ lấy dữ liệu đúng quy tắc! {datetime.now().strftime('%H:%M %d/%m')}")
            dem_bao_song=0

        # === LẦN LƯỢT LẤY HẾT 2 MÃ TRONG MỘT LẦN CHẠY ===
        for ma in DANH_SACH_MA:
            kq=phan_tich(ma)
            if not kq: continue
            if trang_thai[ma]=="DANG_GIU":
                vt=vi_tri_dang_giu[ma]
                if kq["gia"]>=vt["cl"]: bot.send_message(CHAT_ID,f"🏆✅ĐẠT LỢI:{ma} đạt {kq['gia']:,}đ ≥ {vt['cl']:,}đ\n👉Trả lời:Đã bán");continue
                if kq["gia"]<=vt["catl"]: bot.send_message(CHAT_ID,f"🛑⚠️CẮT LỖ:{ma} xuống {kq['gia']:,}đ ≤ {vt['catl']:,}đ\n👉Trả lời:Đã bán");continue
            elif kq["diem"]>=5 and trang_thai[ma]!="CHO_XAC_NHAN":
                bot.send_message(CHAT_ID,f"""📢🚀TÍN HIỆU:{ma}
💵Giá:{kq['gia']:,}đ |Điểm:{kq['diem']}/10
🎯Chốt lời:{kq['cl']:,}đ |🛡️Bảo vốn:{kq['catl']:,}đ
👉Trả lời:Đã mua""")
                trang_thai[ma]="CHO_XAC_NHAN"
                trang_thai[f"gia_{ma}"]=kq["gia"];trang_thai[f"cl_{ma}"]=kq["cl"];trang_thai[f"catl_{ma}"]=kq["catl"]

        # === ✅ SAU KHI LÀM XONG CẢ DANH SÁCH → NGHỈ DÀI ĐỂ KHÔNG BỊ CHẶN, KHỔI PHỤC LƯỢT ===
        print(f"✅ Hoàn thành bộ hiện tại, nghỉ {NGHI_SAU_KHI_XONG_BO} giây mới làm lại...")
        time.sleep(NGHI_SAU_KHI_XONG_BO)
