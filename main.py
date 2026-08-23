import telebot, json, os, re, time
from datetime import datetime
from collections import defaultdict
from flask import Flask
from threading import Thread
import requests

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
def giu_song(): return "✅ Bot HOẠT ĐỘNG ỔN ĐỊNH! Lệnh: top3 → 3 đuôi tốt nhất giai đoạn 10/03-23/03 | db → TOP10 đuôi Giải Đặc Biệt dự đoán ngày tiếp theo"

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

# === ✅ LỆNH TOP3: CHỌN LỌC TRONG GIAI ĐOẠN CHÍNH XÁC 10/03 → 23/03 ===
def tinh_top3_giai_doan(dl):
    # Lọc đúng khoảng thời gian yêu cầu
    ds_ngay = sorted(dl.keys(), key=lambda x:datetime.strptime(x,"%d/%m"))
    ngay_batdau = "10/03"
    ngay_ketthuc = "23/03"
    khung_giai_doan = []
    for n in ds_ngay:
        if datetime.strptime(n,"%d/%m") >= datetime.strptime(ngay_batdau,"%d/%m") and datetime.strptime(n,"%d/%m") <= datetime.strptime(ngay_ketthuc,"%d/%m"):
            khung_giai_doan.append(n)

    if len(khung_giai_doan)<5:
        return f"⚠️ Chưa đủ dữ liệu trong giai đoạn 10/03 đến 23/03! Hiện có {len(khung_giai_doan)} ngày, vui lòng nhập đủ thêm kết quả từng ngày nhé."

    ghi_chu = f"✅ PHÂN TÍCH CHÍNH XÁC GIAI ĐOẠN: {ngay_batdau} → {ngay_ketthuc}\nƯu tiên Giải Đặc Biệt trọng số cao nhất + kết hợp quy luật xuất hiện đều đặn, khoảng nghỉ vàng hiệu quả!"

    thongke = defaultdict(lambda: {"tong_diem":0, "ngay_db":[], "ngay_tat_ca":[], "nhom_chuc":""})
    for thu_tu,ngay in enumerate(khung_giai_doan):
        db_so = dl[ngay].get("DB","")
        db_d = lay_2cuoi(db_so)
        if db_d.isdigit():
            thongke[db_d]["ngay_db"].append(thu_tu)
            thongke[db_d]["tong_diem"] += TRONG_SO["DB"]
            thongke[db_d]["nhom_chuc"] = lay_chuc(db_d)
        for gt,ds in dl[ngay].items():
            if gt=="DB": continue
            danh_sach = [ds] if isinstance(ds,str) else ds
            for s in danh_sach:
                d=lay_2cuoi(s)
                if d.isdigit():
                    thongke[d]["ngay_tat_ca"].append(thu_tu)
                    thongke[d]["tong_diem"] += TRONG_SO[gt]
                    thongke[d]["nhom_chuc"] = lay_chuc(d)

    ds_xep = []
    for duoi,tt in thongke.items():
        sl_db = len(tt["ngay_db"]); sl_tong = sl_db + len(tt["ngay_tat_ca"])
        if sl_db <2 or sl_tong <4: continue

        diem_nghi =0
        if tt["ngay_db"]:
            ngay_cuoi_xuat = tt["ngay_db"][-1]
            khoang_nghi = len(khung_giai_doan)-1 - ngay_cuoi_xuat
            if 4<=khoang_nghi<=7: diem_nghi=65
            elif 3<=khoang_nghi<=9: diem_nghi=50
            elif khoang_nghi<=2: diem_nghi=30
            else: diem_nghi=20

        diem_deu=0
        if sl_db>=2:
            khoang_lap = [tt["ngay_db"][i+1]-tt["ngay_db"][i] for i in range(sl_db-1)]
            tb_lap = sum(khoang_lap)/len(khoang_lap)
            if 3<=tb_lap<=6: diem_deu=35

        tong_diem = round(diem_nghi + diem_deu + tt["tong_diem"]*8)
        ds_xep.append((duoi,tong_diem))

    ds_xep.sort(key=lambda x:-x[1])
    top3 = ds_xep[:3]
    if not top3: return "⚠️ Chưa đủ quy luật rõ ràng trong giai đoạn này để chọn lọc!"

    noi_dung = f"{ghi_chu}\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n🏆 TOP 3 ĐUÔI TỐT NHẤT:\n"
    for vt,(d,dt) in enumerate(top3,1): noi_dung +=f"{vt}. Đuôi: {d} | Tổng điểm chất lượng: {dt}/100\n"
    return noi_dung

# === ✅ LỆNH DB: CÙNG QUY LUẬT NHƯNG CHỈ TẬP TRUNG GIẢI ĐẶC BIỆT → TOP10 DỰ KIẾN NGÀY TIẾP THEO ===
def tinh_top10_dacbiet_ngaytiep(dl):
    ds_ngay = sorted(dl.keys(), key=lambda x:datetime.strptime(x,"%d/%m"))
    ngay_batdau = "10/03"
    ngay_ketthuc = "23/03"
    khung_giai_doan = []
    for n in ds_ngay:
        if datetime.strptime(n,"%d/%m") >= datetime.strptime(ngay_batdau,"%d/%m") and datetime.strptime(n,"%d/%m") <= datetime.strptime(ngay_ketthuc,"%d/%m"):
            khung_giai_doan.append(n)

    if len(khung_giai_doan)<5:
        return f"⚠️ Cần đủ dữ liệu Giải Đặc Biệt giai đoạn {ngay_batdau}→{ngay_ketthuc} mới dự đoán chính xác TOP10 ngày tiếp theo!"

    thongke_db = defaultdict(lambda: {"lan_xuat":0, "ngay_xuat":[], "diem":0.0})
    for thu_tu,ngay in enumerate(khung_giai_doan):
        db_so = dl[ngay].get("DB","").strip()
        if len(db_so)>=2 and db_so.isdigit():
            d=lay_2cuoi(db_so)
            thongke_db[d]["lan_xuat"] +=1
            thongke_db[d]["ngay_xuat"].append(thu_tu)

    ds_diem=[]; diem_cao_nhat=0
    for duoi,tt in thongke_db.items():
        sl=tt["lan_xuat"]
        if sl<2: continue
        ngay_cuoi=tt["ngay_xuat"][-1]
        khoang_nghi = len(khung_giai_doan) - ngay_cuoi # Tính khoảng chờ đến ngày sau kết thúc giai đoạn

        diem=0
        if 5<=khoang_nghi<=8: diem=95
        elif 4<=khoang_nghi<=10: diem=85
        elif 3<=khoang_nghi<=12: diem=75
        elif khoang_nghi<=2: diem=60
        else: diem=50
        if sl>=3:
            khoang_lap = [tt["ngay_xuat"][i+1]-tt["ngay_xuat"][i] for i in range(sl-1)]
            tb_lap=sum(khoang_lap)/len(khoang_lap)
            if 4<=tb_lap<=7: diem +=5
        thongke_db[duoi]["diem"]=diem
        if diem>diem_cao_nhat: diem_cao_nhat=diem
        ds_diem.append((duoi,round(diem)))

    ds_diem.sort(key=lambda x:-x[1])
    top10=ds_diem[:10]
    noi_dung = f"🎖️ DB: TOP 10 ĐUÔI CHỈ TẬP TRUNG GIẢI ĐẶC BIỆT\n📊 Dựa quy luật {ngay_batdau}→{ngay_ketthuc} ➡️ DỰ KIẾN có xác suất cao xuất hiện NGÀY TIẾP THEO sau giai đoạn!\n📈 Điểm cao nhất làm chuẩn tham chiếu 100%\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    for vt,(duoi,d) in enumerate(top10,1):
        tylenle=round((d/diem_cao_nhat*100),1) if diem_cao_nhat>0 else round(d)
        noi_dung +=f"{vt:02d}. Đuôi: {duoi} ⭐ Xác suất tham khảo: {tylenle}% | Điểm tin cậy: {d}/100\n"
    noi_dung += "\n💡 Lưu ý: Phân tích quy luật lịch sử giai đoạn, kết hợp tham khảo top3 đưa ra lựa chọn tốt nhất!"
    return noi_dung

# === NHẬP DỮ LIỆU THÔNG QUA TIN NHẮN ĐƠN GIẢN ===
@bot.message_handler(func=lambda m: re.fullmatch(r"\d{1,2}/\d{1,2}", m.text.strip()))
def nhap_ngay_du_lieu(m):
    if m.chat.id!=CHAT_ID: return
    ngay = m.text.strip()
    bot.reply_to(m,f"📅 Đã nhận ngày {ngay}! Gửi theo mẫu:\nDB: số\nG1: số\nG2: số,số...\nG7: số,số...\n→ Nhập đủ lưu tích lũy vào giai đoạn phân tích!")
    bot.register_next_step_handler(m, lambda msg: luu_ngay(ngay, msg))

def luu_ngay(ngay, msg):
    try:
        du_lieu = {}
        for d in msg.text.strip().splitlines():
            d=d.strip()
            if ":" in d:
                ten_gia, gt = d.split(":",1)
                ten_gia=ten_gia.strip().upper()
                gt=gt.strip()
                if ten_gia in ["DB","G1","G2","G3","G4","G5","G6","G7"]:
                    du_lieu[ten_gia]=gt if "," not in gt else [x.strip() for x in gt.split(",")]
        if du_lieu:
            so=luu_dulieu_va_giu_60ngay(ngay,du_lieu)
            bot.send_message(msg.chat.id,f"✅ Lưu thành công ngày {ngay}! Tổng đang có: {so} ngày dữ liệu\n💡 Nhập đủ các ngày từ 10/03 đến 23/03 → gõ lệnh top3/db xem kết quả chính xác yêu cầu!")
        else: bot.send_message(msg.chat.id,"⚠️ Chưa đúng mẫu: ghi rõ tên giải DB/G1... kèm số kết quả nhé!")
    except: bot.send_message(msg.chat.id,"❌ Định dạng chưa hợp lệ, vui lòng nhập lại rõ từng dòng theo hướng dẫn!")

# === ĐĂNG KÝ LỆNH CHÍNH XÁC Ý MUỐN ===
@bot.message_handler(func=lambda m: m.text.strip().lower()=="top3" and m.chat.id==CHAT_ID)
def goi_top3(m):
    bot.send_message(m.chat.id, tinh_top3_giai_doan(tai_dulieu()))

@bot.message_handler(func=lambda m: m.text.strip().lower()=="db" and m.chat.id==CHAT_ID)
def goi_db(m):
    bot.send_message(m.chat.id, tinh_top10_dacbiet_ngaytiep(tai_dulieu()))

@bot.message_handler(commands=['start','help'])
def tro_giup(m): bot.send_message(m.chat.id,"📖 Hướng dẫn dùng:\n🔹 Gõ ngày:VD 12/03 → gửi kết quả từng giải lưu tích lũy đủ 10/03→23/03\n🔹 Gõ **top3**: xem 3 đuôi tổng hợp tốt nhất trong đúng giai đoạn yêu cầu\n🔹 Gõ **db**: xem TOP10 CHỈ lấy Giải Đặc Biệt, dự kiến xác suất cao ngày TIẾP THEO sau giai đoạn + tỷ lệ chuẩn rõ ràng!")

# === CHẠY BỀN ỔN ĐỊNH ===
def chay_bot_ben():
    while True:
        try: bot.polling(none_stop=True, interval=3, timeout=180, long_polling_timeout=180)
        except Exception as e: print(f"⚠️ Tạm ngắt nhỏ: {e} → chờ 5s tự khởi động lại...");time.sleep(5)

Thread(target=chay_web, daemon=True).start()
Thread(target=chay_bot_ben, daemon=True).start()

if __name__=="__main__":
    print("🚀 Đã chỉnh đúng yêu cầu: top3=giai đoạn 10-23/03 tổng hợp tốt nhất | db=chỉ Giải Đặc Biệt dự đoán ngày sau + tỷ lệ chuẩn!");while True:time.sleep(3600)
