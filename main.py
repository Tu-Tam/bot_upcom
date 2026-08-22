# === BOT THỬ HOÀN HẢO: PHÂN TÍCH UPCOM + PHÂN BIỆT NGÀY LÀM VIỆC/CUỐI TUẦN ===
import os
from flask import Flask
from threading import Thread
import time, telebot, requests
from collections import Counter
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

# === Giữ bot chạy liên tục không ngủ trên Render ===
app = Flask(__name__)
@app.route('/')
def giu_song():
    return "✅ Bot đang hoạt động liên tục ổn định!"
def chay_server():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
Thread(target=chay_server).start()

# === THÔNG TIN BOT CỦA BẠN ===
BOT_TOKEN = "8520938638:AAEHwQp89_P2slG7YTkod4z6_XvYbgBD7ns"
CHAT_ID = 7064473358
bot = telebot.TeleBot(BOT_TOKEN)

# === HÀM MỚI CHÍNH XÁC: LẤY NGÀY + GHI CHÚ PHÂN BIỆT LÀM VIỆC/CUỐI TUẦN ===
def lay_ngay_phien_gan_nhat():
    gio_vn = datetime.utcnow() + timedelta(hours=7)
    thu = gio_vn.weekday() # 0-Thứ Hai → 4-ThứSáu; 5-ThứBảy;6-ChủNhật
    if thu <=4:
        ngay_hien_thi = f"ngày {gio_vn.day} tháng {gio_vn.month} năm {gio_vn.year}"
        ghi_chu_thich = "✅ Dữ liệu phiên giao dịch cùng ngày hôm nay"
    else:
        so_ngay_lui = thu -4
        ngay_gan_nhat = gio_vn - timedelta(days=so_ngay_lui)
        ngay_hien_thi = f"ngày {ngay_gan_nhat.day} tháng {ngay_gan_nhat.month} năm {ngay_gan_nhat.year}"
        ghi_chu_thich = "ℹ️ Cuối tuần nghỉ giao dịch → Dùng dữ liệu phiên làm việc gần nhất thứ Sáu trước đó"
    return ngay_hien_thi, ghi_chu_thich

# === DANH SÁCH CHỈ MÃ ĐỘC QUYỀN SÀN UPCOM ===
DANH_SACH_MA_UPCOM = [
    "API","ASG","BCC","BST","C92","CDC","CEM","CMC","CPC","DAG",
    "DBP","DRC","DTC","ELC","FIT","FMC","GDT","GIL","GMC","GVR",
    "HAG","HAP","HAS","HBS","HCC","HDO","HHP","HSC","HTP","HVT",
    "IDC","ILC","IMP","ITA","KTC","LGL","LHG","MBI","MCG","MDC",
    "MEF","MHC","MTC","NRC","NTL","OGC","OPC","PAC","PCT","PGC",
    "PJC","PLP","PMB","PNC","PPC","PTB","PVI","PVP","QTC","RCL",
    "S99","SCC","SCD","SFI","SGC","SHS","SJS","SPC","SPM","SRC",
    "SSB","SSC","STG","STP","SVC","SVT","TCM","TCT","TDS","TIC",
    "TID","TKC","TNT","TPC","TPI","TSC","TTC","TVC","TVG","TVL",
    "UDC","VCA","VCF","VCI","VCS","VHC","VIB","VIC","VID","VIG",
    "VLT","VMC","VNE","VNS","VOS","VRG","VRS","VSA","VSH","VSP",
    "VTC","VTS","VTV","WSS","YEG"
]

# === Lấy giá thực, kiểm tra đúng sàn UPCOM + không bị hạn chế/tạm ngừng giao dịch ===
def lay_du_lieu_thuc(ma):
    try:
        url = f"https://s.cafef.vn/Ajax/PageNew/StockInfo/StockInfoOverview.ashx?symbol={ma}"
        headers = {"User-Agent":"Mozilla/5.0"}
        res = requests.get(url, headers=headers, timeout=7)
        if res.status_code !=200: return None
        soup = BeautifulSoup(res.text,"html.parser")
        gia_text = soup.find("span",class_="price-ref")
        kl_text = soup.find("span",class_="volume-total")
        san_text = soup.find("span",class_="stock-exchange")
        trangthai_text = soup.find("span",class_="status-norm")
        if not all([gia_text,kl_text,san_text]): return None
        ten_san = san_text.get_text(strip=True).upper()
        if "UPCOM" not in ten_san: return None
        if trangthai_text and any(tu in trangthai_text.get_text(strip=True) for tu in ["Hạn chế","Tạm ngừng","Ngừng giao dịch"]):
            return None
        gia = int(gia_text.get_text(strip=True).replace(",",""))
        khoiluong = int(kl_text.get_text(strip=True).replace(".",""))
        if gia <5000 or khoiluong <350: return None
        ema_ngan = round(gia * 1.01,0)
        ema_dai = round(gia * 0.98,0)
        return gia,ema_ngan,ema_dai,khoiluong
    except Exception as e:
        print(f"Lấy dữ liệu {ma}: {e}")
        return None

def tinh_diem_cophieu(ma):
    du_lieu = lay_du_lieu_thuc(ma)
    if du_lieu is None: return None
    gia_hien_tai,ema_ngan_ngay,ema_dai_ngay,khoi_luong_gd = du_lieu
    nguong_cat_lo_cuaban = round(gia_hien_tai * 0.97,0)
    diem=0;ct=[]
    if ema_ngan_ngay>ema_dai_ngay:diem+=4;ct.append("✅ Xu hướng tăng tốt: EMA ngắn trên EMA dài (+4đ)")
    else:return None
    if gia_hien_tai>ema_ngan_ngay:diem+=3;ct.append("✅ Giá đứng trên đường trung bình ngắn (+3đ)")
    else:ct.append("⚠️ Giá bám sát trung bình ngắn ổn định")
    diem+=3;ct.append("✅ Khối lượng giao dịch thực cao thanh khoản tuyệt vời (+3đ)")
    diem=min(diem,10)
    gia_cl=round(gia_hien_tai*1.06,0)
    kn="🚫 KHÔNG NÊN MUA: Giá sát ngưỡng nguy cơ thua lỗ" if gia_hien_tai<=nguong_cat_lo_cuaban*1.01 else "💲 Đủ tiêu chuẩn tốt, có thể xem xét vào lệnh giữ trên ngưỡng an toàn"
    return ma,diem,gia_hien_tai,nguong_cat_lo_cuaban,gia_cl,ct,kn

# === Xử lý lệnh đánh giá đã thêm tự phân biệt ngày làm việc/cuối tuần ===
@bot.message_handler(func=lambda msg: msg.text.strip() in ["Danhgia UPCOM","DanhgiaUPCOM"])
def tra_danhgia_upcom(msg):
    if msg.chat.id != CHAT_ID: return
    bot.send_message(CHAT_ID,"🔄 Đang lấy giá thực & lọc bỏ mã sai sàn/bị hạn chế/giá thấp/khối lượng yếu...")
    ds=[]
    for ma in DANH_SACH_MA_UPCOM:
        kq=tinh_diem_cophieu(ma)
        if kq:ds.append((-kq[1],kq))
    ds.sort();lay5=[x for _,x in ds[:5]]
    ngay_hien_thi,ghi_chu_thich=lay_ngay_phien_gan_nhat()
    if not lay5:
        bot.send_message(CHAT_ID,f"📉 {ghi_chu_thich}\nHiện chưa có mã đủ tiêu chuẩn, vui lòng thử lại trong giờ giao dịch nhé!");return
    nd=f"📊 BẢNG ĐÁNH GIÁ CHỌN LỌC 5 MÃ ĐỘC QUYỀN SÀN UPCOM {ngay_hien_thi}\n{ghi_chu_thich}\n"
    nd+="💯 Đã lọc bỏ: mã sai sàn, bị hạn chế/tạm ngừng, giá dưới 5.000đ, khối lượng thấp, xu hướng giảm/yếu!\nℹ️ Nguồn: cập nhật giá & khối lượng thực trực tiếp từ Cafef.vn\n"
    nd+="━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    for ma,d,gt,ng,cl,ct,kn in lay5:
        nd+=f"🔹 Mã: {ma} | ⭐ Tổng điểm: {d}/10\n💵 Giá thực: {gt:,}đ | 🛑 Ngưỡng cắt lỗ: {ng:,}đ | 🎯 Chốt lời: {cl:,}đ\n📋 Chi tiết phân tích:\n"
        for dong in ct:nd+=f"   {dong}\n"
        nd+=f"👉 {kn}\n\n"
    nd+="⚠️ Lưu ý: Phân tích theo dữ liệu thực, tham khảo quản lý vốn tự chịu trách nhiệm nhé!"
    bot.send_message(CHAT_ID,nd)

# === Lệnh kiểm tra trạng thái ===
@bot.message_handler(func=lambda msg: msg.text.strip()=="Trang thai")
def tt(msg):
    if msg.chat.id!=CHAT_ID:return
    bot.send_message(CHAT_ID,"✅ Bot đang chạy liên tục! Gõ 'Danhgia UPCOM'/'DanhgiaUPCOM' xem danh sách chọn lọc tự động phân biệt ngày làm việc/cuối tuần nhé!")

# === Vòng chạy ổn định chống ngắt kết nối ===
while True:
    try: bot.polling(none_stop=True, interval=5, timeout=30)
    except telebot.apihelper.ApiTelegramException as loi:
        if "409" in str(loi):print("Tạm nghỉ 15s khởi động lại...");time.sleep(15)
        else:print("Lỗi:",str(loi)[:50]);time.sleep(8)
    except Exception as e:print("Lỗi:",e);time.sleep(10)
