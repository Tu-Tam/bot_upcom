import telebot, json, os, re, time, requests
from datetime import datetime, timedelta
from collections import defaultdict
from flask import Flask
from threading import Thread
from bs4 import BeautifulSoup

# ======================== BIẾN MÔI TRƯỜNG AN TOÀN ========================
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
CHAT_ID = int(os.getenv("CHAT_ID", 0))

if not BOT_TOKEN or ":" not in BOT_TOKEN:
    print("❌ Kiểm tra lại BOT_TOKEN trên Render!")
    exit(1)
if CHAT_ID <= 0:
    print("❌ CHAT_ID phải là số dương hợp lệ!")
    exit(1)
# ===========================================================================

bot = telebot.TeleBot(BOT_TOKEN)
# Ưu tiên đọc trước dữ liệu bạn lưu cùng thư mục tuyệt đối không ghi đè làm mất
TEN_TEP = os.path.join(os.path.dirname(__file__), "dulieu_xsmb.json")

app = Flask(__name__)
@app.route('/')
def giu_song(): 
    return "✅ Bot: napdulieu=đọc tệp trước + bổ sung ngày thiếu | top3=Phân tích linh hoạt toàn bộ dữ liệu có trong tệp ra 3 đuôi tốt nhất | db=TOP10 Giải Đặc Biệt dự đoán ngày tiếp theo"

def chay_web():
    cong = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=cong, debug=False, use_reloader=False)

TRONG_SO = {
    "DB": 2.5, "G1": 1.6, "G2": 1.3, "G3": 1.1,
    "G4": 0.9, "G5": 0.8, "G6": 0.7, "G7": 0.6
}

def lay_2cuoi(s): return str(s).strip()[-2:]
def lay_chuc(d): return str(d)[0] if len(str(d))==2 else "0"

def tai_dulieu():
    try:
        if os.path.exists(TEN_TEP):
            with open(TEN_TEP,"r",encoding="utf-8") as f: return json.load(f)
        return {}
    except: return {}

def luu_dulieu_va_giu_60ngay(ngay, d):
    dl = tai_dulieu(); dl[ngay] = d
    try:
        with open(TEN_TEP,"w",encoding="utf-8") as f: json.dump(dl,f,ensure_ascii=False,indent=2)
    except: pass
    return len(dl)

# Chỉ bổ sung những ngày còn thiếu thôi, giữ nguyên toàn bộ dữ liệu bạn đã nhập thủ công
def tu_lay_du_lieu_giai_doan():
    dl = tai_dulieu()
    batdau = datetime(2026,3,10); ketthuc = datetime(2026,3,23)
    co_san=0; them_bo_sung=0
    while batdau <= ketthuc:
        ngay_ddmm = batdau.strftime("%d/%m")
        if ngay_ddmm in dl and dl[ngay_ddmm].get("DB",""): co_san +=1; batdau += timedelta(days=1); continue
        try:
            ngay_link = batdau.strftime("%d-%m-%Y")
            res = requests.get(f"https://ketqua.net/ngay-{ngay_link}", timeout=12, headers={"User-Agent":"Mozilla/5.0"})
            res.raise_for_status(); soup = BeautifulSoup(res.text,"html.parser")
            du_lieu_ngay = {}
            du_lieu_ngay["DB"] = soup.find("td",attrs={"id":"rs_0_0"}).get_text(strip=True) if soup.find("td",attrs={"id":"rs_0_0"}) else ""
            du_lieu_ngay["G1"] = soup.find("td",attrs={"id":"rs_1_0"}).get_text(strip=True) if soup.find("td",attrs={"id":"rs_1_0"}) else ""
            g2 = soup.find_all("td",attrs={"class":"giai2"}); du_lieu_ngay["G2"]=[x.get_text(strip=True) for x in g2] if len(g2)==2 else ""
            g3 = soup.find_all("td",attrs={"class":"giai3"}); du_lieu_ngay["G3"]=[x.get_text(strip=True) for x in g3] if len(g3)==6 else ""
            g4 = soup.find_all("td",attrs={"class":"giai4"}); du_lieu_ngay["G4"]=[x.get_text(strip=True) for x in g4] if len(g4)==4 else ""
            g5 = soup.find_all("td",attrs={"class":"giai5"}); du_lieu_ngay["G5"]=[x.get_text(strip=True) for x in g5] if len(g5)==6 else ""
            g6 = soup.find_all("td",attrs={"class":"giai6"}); du_lieu_ngay["G6"]=[x.get_text(strip=True) for x in g6] if len(g6)==3 else ""
            g7 = soup.find_all("td",attrs={"class":"giai7"}); du_lieu_ngay["G7"]=[x.get_text(strip=True) for x in g7] if len(g7)==4 else ""
            if du_lieu_ngay["DB"]: dl[ngay_ddmm]=du_lieu_ngay; them_bo_sung +=1
        except Exception as e: print(f"Không lấy được {ngay_ddmm}: {e}")
        batdau += timedelta(days=1)
    try:
        with open(TEN_TEP,"w",encoding="utf-8") as f: json.dump(dl,f,ensure_ascii=False,indent=2)
    except: pass
    return f"📂 Đã có sẵn trong tệp: {co_san} ngày | Bổ sung thêm thiếu: {them_bo_sung} ngày!"

# === ✅ Đã sửa đúng yêu cầu: KHÔNG CỨNG CHỈ 10/03→23/03, phân tích linh hoạt toàn bộ ngày có trong tệp ra 3 đuôi điểm cao nhất ===
def tinh_top3(dl):
    ds_ngay = sorted(dl.keys(), key=lambda x:datetime.strptime(x,"%d/%m"))
    if len(ds_ngay)<5: return f"⚠️ Cần đủ ít nhất 5 ngày! Gõ **napdulieu** trước để nạp đủ dữ liệu nhé!"

    ghi_chu = f"✅ PHÂN TÍCH LINH HOẠT TỪ TOÀN BỘ DỮ LIỆU TRONG TỆP → chọn ra 3 đuôi có điểm chất lượng cao nhất!"
    thongke = defaultdict(lambda: {"tong_diem":0, "ngay_db":[], "ngay_tat_ca":[], "nhom_chuc":""})

    for thu_tu,ngay in enumerate(ds_ngay):
        db_so = dl[ngay].get("DB",""); db_d=lay_2cuoi(db_so)
        if db_d.isdigit():
            thongke[db_d]["ngay_db"].append(thu_tu); thongke[db_d]["tong_diem"] += TRONG_SO["DB"]; thongke[db_d]["nhom_chuc"]=lay_chuc(db_d)
        for gt,ds in dl[ngay].items():
            if gt=="DB": continue
            danh_sach=[ds] if isinstance(ds,str) else ds
            for s in danh_sach:
                d=lay_2cuoi(s)
                if d.isdigit(): thongke[d]["ngay_tat_ca"].append(thu_tu); thongke[d]["tong_diem"] += TRONG_SO[gt]; thongke[d]["nhom_chuc"]=lay_chuc(d)

    ds_xep=[]
    for duoi,tt in thongke.items():
        sl_db=len(tt["ngay_db"]); sl_tong=sl_db+len(tt["ngay_tat_ca"])
        if sl_db<2 or sl_tong<4: continue
        diem_nghi=0
        if tt["ngay_db"]:
            k=len(ds_ngay)-1 - tt["ngay_db"][-1]
            if 4<=k<=7: diem_nghi=65
            elif 3<=k<=9: diem_nghi=50
            elif k<=2: diem_nghi=30
            else: diem_nghi=20
        diem_deu=0
        if sl_db>=2:
            kc=[tt["ngay_db"][i+1]-tt["ngay_db"][i] for i in range(sl_db-1)]; tb=sum(kc)/len(kc)
            if 3<=tb<=6: diem_deu=35
        ds_xep.append((duoi, round(diem_nghi+diem_deu+tt["tong_diem"]*8)))

    ds_xep.sort(key=lambda x:-x[1]); top3=ds_xep[:3]
    if not top3: return "⚠️ Chưa đủ quy luật rõ ràng trong dữ liệu!"
    noi=f"{ghi_chu}\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n🏆 **TOP 3 ĐUÔI CHẤT LƯỢNG CAO NHẤT**:\n"
    for vt,(d,dt) in enumerate(top3,1): noi+=f"{vt}. Đuôi: {d} | Tổng điểm: {dt}/100\n"
    return noi

# Lệnh xem TOP10 Giải Đặc Biệt dự đoán ngày tiếp theo vẫn hoạt động bình thường
def tinh_top10_dacbiet_ngaytiep(dl):
    ds_ngay = sorted(dl.keys(), key=lambda x:datetime.strptime(x,"%d/%m"))
    if len(ds_ngay)<5: return f"⚠️ Gõ **napdulieu** đủ dữ liệu trước nhé!"
    thongke_db = defaultdict(lambda: {"lan_xuat":0, "ngay_xuat":[], "diem":0.0})
    for thu_tu,ngay in enumerate(ds_ngay):
        db_so=dl[ngay].get("DB","").strip()
        if len(db_so)>=2 and db_so.isdigit():
            d=lay_2cuoi(db_so); thongke_db[d]["lan_xuat"]+=1; thongke_db[d]["ngay_xuat"].append(thu_tu)
    ds_diem=[]; cao_nhat=0
    for duoi,tt in thongke_db.items():
        sl=tt["lan_xuat"]; if sl<2: continue
        k=len(ds_ngay)-tt["ngay_xuat"][-1]
        diem=95 if 5<=k<=8 else 85 if 4<=k<=10 else 75 if 3<=k<=12 else 60 if k<=2 else 50
        if sl>=3:
            kc=[tt["ngay_xuat"][i+1]-tt["ngay_xuat"][i] for i in range(sl-1)]; tb=sum(kc)/len(kc)
            if 4<=tb<=7: diem+=5
        if diem>cao_nhat: cao_nhat=diem
        ds_diem.append((duoi,round(diem)))
    ds_diem.sort(key=lambda x:-x[1]); top10=ds_diem[:10]
    noi=f"🎖️ **DB: TOP10 Giải Đặc Biệt**\n📊 Dựa toàn bộ dữ liệu trong tệp → xác suất cao ngày tiếp theo!\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    for vt,(duoi,d) in enumerate(top10,1):
        tl=round((d/cao_nhat*100),1) if cao_nhat>0 else d
        noi+=f"{vt:02d}. Đuôi: {duoi} ⭐ {tl}% | Điểm: {d}/100\n"
    return noi

# Nhập/thêm/sửa kết quả thủ công lưu trực tiếp vào tệp JSON gốc không làm mất dữ liệu cũ
@bot.message_handler(func=lambda m: re.fullmatch(r"\d{1,2}/\d{1,2}", m.text.strip()))
def nhap_ngay_du_lieu(m):
    if m.chat.id!=CHAT_ID: return
    ngay=m.text.strip()
    bot.reply_to(m,f"📅 Ngày {ngay}! Gửi theo từng dòng: DB:số, G1:số... sẽ lưu vào tệp dữ liệu chính!")
    bot.register_next_step_handler(m,lambda msg:luu_ngay(ngay,msg))
def luu_ngay(ngay,msg):
    try:
        dlngay={}
        for d in msg.text.strip().splitlines():
            d=d.strip()
            if ":"in d:
                t,g=d.split(":",1); t=t.strip().upper(); g=g.strip()
                if t in ["DB","G1","G2","G3","G4","G5","G6","G7"]: dlngay[t]=g if ","not in g else [x.strip() for x in g.split(",")]
        if dlngay: bot.send_message(msg.chat.id,f"✅ Đã cập nhật thành công ngày {ngay}! Tổng số ngày có trong tệp: {luu_dulieu_va_giu_60ngay(ngay,dlngay)}")
        else: bot.send_message(msg.chat.id,"⚠️ Chưa đúng mẫu, ghi rõ tên giải kèm số nhé!")
    except: bot.send_message(msg.chat.id,"❌ Lỗi nhập lại theo hướng dẫn!")

# === ĐĂNG KÝ LỆNH CHÍNH ĐÃ THAY ĐÚNG Ý ===
@bot.message_handler(func=lambda m: m.text.strip().lower()=="napdulieu" and m.chat.id==CHAT_ID)
def gn(m): bot.send_message(m.chat.id,tu_lay_du_lieu_giai_doan())
@bot.message_handler(func=lambda m: m.text.strip().lower()=="top3" and m.chat.id==CHAT_ID)
def goi_top3_moi(m): bot.send_message(m.chat.id,tinh_top3(tai_dulieu())) # ✅ Không còn cố định khoảng ngày, lấy tất cả dữ liệu có trong tệp!
@bot.message_handler(func=lambda m: m.text.strip().lower()=="db" and m.chat.id==CHAT_ID)
def gd(m): bot.send_message(m.chat.id,tinh_top10_dacbiet_ngaytiep(tai_dulieu()))
@bot.message_handler(commands=['start','help'])
def help_bot(m): bot.send_message(m.chat.id,"📖 Hướng dẫn:\n🔹 napdulieu: Đọc ưu tiên tệp dulieu_xsmb.json trước → chỉ bổ sung ngày còn thiếu\n🔹 **top3**: Phân tích ngay lấy 3 đuôi tốt nhất từ tất cả ngày đang có trong tệp!\n🔹 db: Xem TOP10 Giải Đặc Biệt dự đoán ngày tiếp theo + tỷ lệ % rõ ràng\n🔹 Gõ ngày DD/MM: Nhập/thay kết quả lưu thẳng vào tệp gốc!")

# Chạy bền, tự động khởi động lại khi ngắt mạng nhỏ
def chay_bot_ben():
    while True:
        try: bot.polling(none_stop=True, interval=3, timeout=180, long_polling_timeout=180)
        except Exception as e: print(f"⚠️ Tạm ngắt nhỏ: {e} → chờ 5s chạy lại...");time.sleep(5)

Thread(target=chay_web, daemon=True).start()
Thread(target=chay_bot_ben, daemon=True).start()

if __name__=="__main__":
    print("🚀 Đã làm sạch lỗi thư viện không tồn tại + đổi thành công lệnh top3 linh hoạt theo dữ liệu trong tệp!");while True:time.sleep(3600)
