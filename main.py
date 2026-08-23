import telebot, json, os, re, time, requests
from datetime import datetime
from collections import defaultdict
from flask import Flask
from threading import Thread
from bs4 import BeautifulSoup # Thêm thư viện phân tích trang web

# ======================== BIẾN MÔI TRƯỜNG AN TOÀN ========================
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
CHAT_ID = int(os.getenv("CHAT_ID", 0))

if not BOT_TOKEN or ":" not in BOT_TOKEN:
    print("❌ Lỗi BOT_TOKEN không hợp lệ! Kiểm tra lại biến môi trường trên Render")
    exit(1)
if CHAT_ID <= 0:
    print("❌ Lỗi CHAT_ID phải là số dương hợp lệ!")
    exit(1)
# ===========================================================================

bot = telebot.TeleBot(BOT_TOKEN)
TEN_TEP = "dulieu_xsmb.json"

app = Flask(__name__)
@app.route('/')
def giu_song(): return "✅ Bot HOẠT ĐỘNG: Tự lấy dữ liệu + Nhập tay được | top3 → 3 đuôi tốt nhất giai đoạn 10/03-23/03 | db → TOP10 Giải Đặc Biệt dự đoán ngày tiếp theo"

def chay_web():
    cong = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=cong, debug=False, use_reloader=False)

# ✅ PHÂN CẤP TRỌNG SỐ: Giải Đặc Biệt được ưu tiên trọng số cao nhất
TRONG_SO = {
    "DB": 2.5, "G1": 1.6, "G2": 1.3, "G3": 1.1,
    "G4": 0.9, "G5": 0.8, "G6": 0.7, "G7": 0.6
}

def lay_2cuoi(s): return str(s).strip()[-2:]
def lay_chuc(d): return str(d)[0] if len(str(d))==2 else "0"
def tai_dulieu():
    try:
        with open(TEN_TEP,"r",encoding="utf-8") as f: return json.load(f) if os.path.exists(TEN_TEP) else {}
    except: return {}

def luu_dulieu_va_giu_60ngay(ngay, d):
    dl = tai_dulieu()
    dl[ngay] = d
    try:
        with open(TEN_TEP,"w",encoding="utf-8") as f: json.dump(dl,f,ensure_ascii=False,indent=2)
    except: pass
    return len(dl)

# === ✅ CHỨC NĂNG MỚI: TỰ ĐI LẤY ĐỦ NGÀY 10/03 → 23/03 LƯU VÀO TỆP ===
def chuyen_dinh_dang_ngay_web(ngay_str):
    # Đổi 12/03 thành 12-03-2026 phù hợp đường link
    n, thang = ngay_str.split("/")
    return f"{n.zfill(2)}-{thang.zfill(2)}-2026"

def tu_lay_du_lieu_giai_doan():
    """Tự động lấy đủ 14 ngày từ 10/03 đến 23/03, lưu vào tệp dữ liệu"""
    dl = tai_dulieu()
    batdau = datetime(2026,3,10)
    ketthuc = datetime(2026,3,23)
    so_lay_thanhcong=0

    while batdau <= ketthuc:
        ngay_ddmm = batdau.strftime("%d/%m")
        # Bỏ qua nếu đã có rồi không lấy lại tốn thời gian
        if ngay_ddmm in dl and dl[ngay_ddmm].get("DB"):
            batdau = batdau.__add__(__import__('datetime').timedelta(days=1))
            so_lay_thanhcong +=1
            continue
        try:
            # Sử dụng nguồn ketqua.net đáng tin cậy, cấu trúc ổn định
            ngay_link = chuyen_dinh_dang_ngay_web(ngay_ddmm)
            url = f"https://ketqua.net/ngay-{ngay_link}"
            res = requests.get(url, timeout=15, headers={"User-Agent":"Mozilla/5.0"})
            res.raise_for_status()
            soup = BeautifulSoup(res.text,"html.parser")

            du_lieu_ngay = {}
            # Lấy đúng thứ tự giải chuẩn
            db_elem = soup.find("td",attrs={"id":"rs_0_0"})
            du_lieu_ngay["DB"] = db_elem.get_text(strip=True) if db_elem else ""

            g1_elem = soup.find("td",attrs={"id":"rs_1_0"})
            du_lieu_ngay["G1"] = g1_elem.get_text(strip=True) if g1_elem else ""

            g2_list = [s.get_text(strip=True) for s in soup.find_all("td",attrs={"class":"giai2"})]
            du_lieu_ngay["G2"] = g2_list if len(g2_list)==2 else ""

            g3_list = [s.get_text(strip=True) for s in soup.find_all("td",attrs={"class":"giai3"})]
            du_lieu_ngay["G3"] = g3_list if len(g3_list)==6 else ""

            g4_list = [s.get_text(strip=True) for s in soup.find_all("td",attrs={"class":"giai4"})]
            du_lieu_ngay["G4"] = g4_list if len(g4_list)==4 else ""

            g5_list = [s.get_text(strip=True) for s in soup.find_all("td",attrs={"class":"giai5"})]
            du_lieu_ngay["G5"] = g5_list if len(g5_list)==6 else ""

            g6_list = [s.get_text(strip=True) for s in soup.find_all("td",attrs={"class":"giai6"})]
            du_lieu_ngay["G6"] = g6_list if len(g6_list)==3 else ""

            g7_list = [s.get_text(strip=True) for s in soup.find_all("td",attrs={"class":"giai7"})]
            du_lieu_ngay["G7"] = g7_list if len(g7_list)==4 else ""

            if du_lieu_ngay["DB"]:
                dl[ngay_ddmm]=du_lieu_ngay
                so_lay_thanhcong +=1
                print(f"✅ Lấy thành công ngày {ngay_ddmm}")
        except Exception as e:
            print(f"⚠️ Không lấy được {ngay_ddmm}: {e}")
        batdau = batdau.__add__(__import__('datetime').timedelta(days=1))

    # Lưu lại toàn bộ sau khi lấy xong
    try:
        with open(TEN_TEP,"w",encoding="utf-8") as f: json.dump(dl,f,ensure_ascii=False,indent=2)
    except: pass
    return f"📥 Đã tự nạp: {so_lay_thanhcong}/14 ngày giai đoạn 10/03→23/03 vào tệp dữ liệu!"

# === ✅ LỆNH TOP3: CHỌN LỌC TRONG GIAI ĐOẠN CHÍNH XÁC ===
def tinh_top3_giai_doan(dl):
    ds_ngay = sorted(dl.keys(), key=lambda x:datetime.strptime(x,"%d/%m"))
    ngay_batdau = "10/03"
    ngay_ketthuc = 
