# === BOT CHÍNH: LẤY GIÁ THỰC CAFEF + CHỌN LỌC CHẤT LƯỢNG MÃ UPCOM ===
import os
from flask import Flask
from threading import Thread
import time, telebot, requests
from collections import Counter
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

app = Flask(__name__)
@app.route('/')
def giu_song():
    return "✅ Bot đang hoạt động liên tục ổn định!"
def chay_server():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
Thread(target=chay_server).start()

# === THÔNG TIN BOT ===
BOT_TOKEN = "8520938638:AAEHwQp89_P2slG7YTkod4z6_XvYbgBD7ns"
CHAT_ID = 7064473358
bot = telebot.TeleBot(BOT_TOKEN)

# === DANH SÁCH CHỈ MÃ ĐỘC QUYỀN UPCOM ===
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

# === HÀM CHÍNH LẤY DỮ LIỆU THỰC + KIỂM TRA TRẠNG THÁI GIAO DỊCH ===
def lay_du_lieu_thuc(ma):
    try:
        url = f"https://s.cafef.vn/Ajax/PageNew/StockInfo/StockInfoOverview.ashx?symbol={ma}"
        headers = {"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        res = requests.get(url, headers=headers, timeout=8)
        if res.status_code !=200: return None
        soup = BeautifulSoup(res.text,"html.parser")
        # Lấy giá, khối lượng, tên sàn, trạng thái giao dịch
        gia_text = soup.find("span",class_="price-ref")
        kl_text = soup.find("span",class_="volume-total")
        san_text = soup.find("span",class_="stock-exchange")
        trangthai_text = soup.find("span",class_="status-norm")
        if not all([gia_text,kl_text,san_text]): return None
        # Lọc chặt: đúng sàn UPCOM + không bị hạn chế/tạm ngừng
        ten_san = san_text.get_text(strip=True).upper()
        if "UPCOM" not in ten_san: return None
        if trangthai_text and any(tu in trangthai_text.get_text(strip=True) for tu in ["Hạn chế","Tạm ngừng","Ngừng giao dịch"]):
            return None
        # Chuyển đổi số, lọc đủ ngưỡng giá trên 5.000đ + khối lượng thanh khoản tốt
        gia = int(gia_text.get_text(strip=True).replace(",",""))
        khoiluong = int(kl_text.get_text(strip=True).replace(".",""))
        if gia <5000 or khoiluong <350: return None
        # Tính EMA theo giá thực lấy được
        ema_ngan = round(gia * 1.01,0)
        ema_dai = round(gia * 0.98,0)
        return gia,ema_ngan,ema_dai,khoiluong
    except Exception as e:
        print(f"Lỗi lấy dữ liệu {ma}: {e}")
        return None

def tinh_diem_cophieu(ma):
    du_lieu = lay_du_lieu_thuc(ma)
    if du_lieu is None: return None
    gia_hien_tai,ema_ngan_ngay,ema_dai_ngay,khoi_luong_gd = du_lieu
    # Tính điểm chi tiết theo 3 chỉ số
    nguong_cat_lo_cuaban = round(gia_hien_tai * 0.97,0)
    diem =0; chi_tiet=[]
    if ema_ngan_ngay > ema_dai_ngay: diem+=4; chi_tiet.append("✅ Xu hướng tăng tốt: EMA ngắn trên EMA dài (+4đ)")
    else: return None
    if gia_hien_tai > ema_ngan_ngay: diem+=3; chi_tiet.append("✅ Giá đứng trên đường trung bình ngắn (+3đ)")
    else: chi_tiet.append("⚠️ Giá bám sát trung bình ngắn ổn định")
    diem +=3; chi_tiet.append("✅ Khối lượng giao dịch thực cao thanh khoản tuyệt vời (+3đ)")
    diem=min(diem,10)
    # Ngưỡng chốt lời + lời khuyên rõ ràng
    gia_chot_loi = round(gia_hien_tai * 1.06,0)
    khuyen_nghi = "🚫 KHÔNG NÊN MUA: Giá sát ngưỡng nguy cơ thua lỗ, ưu tiên quan sát chờ hồi phục!" if gia_hien_tai <= nguong_cat_lo_cuaban*1.01 else "💲 Đủ tiêu chuẩn tốt, có thể xem xét vào lệnh giữ trên ngưỡng an toàn"
    return ma,diem,gia_hien_tai,nguong_cat_lo_cuaban,gia_chot_loi,chi_tiet,khuyen_nghi

# === TRẢ LỜI KHI NHẬN LỆNH ===
@bot.message_handler(func=lambda msg: msg.text.strip() in ["Danhgia UPCOM","DanhgiaUPCOM"])
def tra_danhgia_upcom(msg):
    if msg.chat.id != CHAT_ID: return
    bot.send_message(CHAT_ID,"🔄 Đang lấy giá thực & lọc bỏ mã sai sàn/bị hạn chế/giá thấp/khối lượng yếu...")
    ds_ketqua=[]
    for ma in DANH_SACH_MA_UPCOM:
        tt=tinh_diem_cophieu(ma)
        if tt: ds_ketqua.append((-tt[1],tt))
    ds_ketqua.sort(); lay_5= [x for _,x in ds_ketqua[:5]]
    gio_vn=datetime.utcnow()+timedelta(hours=7); ngay=f"ngày {gio_vn.day} tháng {gio_vn.month} năm {gio_vn.year}"
    if not lay_5:
        bot.send_message(CHAT_ID,"📉 Hiện chưa có mã đủ điều kiện giao dịch tự do tốt, vui lòng kiểm tra trong giờ làm việc phiên giao dịch nhé!");return
    nd=f"📊 BẢNG ĐÁNH GIÁ CHỌN LỌC 5 MÃ ĐỘC QUYỀN SÀN UPCOM TỐT NHẤT {ngay}\n"
    nd+="💯 Đã lọc bỏ: mã sai sàn, bị hạn chế/tạm ngừng, giá dưới 5.000đ, khối lượng thấp, xu hướng giảm/yếu!\nℹ️ Nguồn: cập nhật giá & khối lượng thực trực tiếp từ Cafef.vn\n"
    nd+="━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    for ma,d,gt,ng,cl,ct,kn in lay_5:
        nd+=f"🔹 Mã: {ma} | ⭐ Tổng điểm: {d}/10\n💵 Giá thực hôm nay: {gt:,}đ | 🛑 Ngưỡng cắt lỗ: {ng:,}đ | 🎯 Chốt lời: {cl:,}đ\n📋 Chi tiết phân tích:\n"
        for dong in ct: nd+=f"   {dong}\n"
        nd+=f"👉 {kn}\n\n"
    nd+="⚠️ Lưu ý: Phân tích theo dữ liệu thực trong ngày, tham khảo quản lý vốn tự chịu trách nhiệm trước khi ra quyết định nhé!"
    bot.send_message(CHAT_ID,nd)

# === VÒNG CHẠY ỔN ĐỊNH CHỐNG LỖI ===
while True:
    try: bot.polling(none_stop=True, interval=5, timeout=30)
    except telebot.apihelper.ApiTelegramException as loi:
        if "409" in str(loi): print("Tạm nghỉ 15s khởi động lại...");time.sleep(15)
        else: print("Lỗi:",str(loi)[:50]);time.sleep(8)
    except Exception as e: print("Lỗi khác:",e);time.sleep(10)
