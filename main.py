import telebot, json, os, re
from datetime import datetime
from collections import defaultdict
from flask import Flask
from threading import Thread
import pytesseract
from PIL import Image
import requests

# ======================== THÔNG TIN ĐÚNG CỦA BẠN ========================
BOT_TOKEN = os.getenv("BOT_TOKEN", "8520938638:AAEHwQp89_P2slG7YTkod4z6_XvYbgBD7ns")
CHAT_ID = int(os.getenv("CHAT_ID", 7064473358))

if not BOT_TOKEN or ":" not in BOT_TOKEN:
    print("❌ Lỗi BOT_TOKEN thiếu dấu hai chấm!")
    exit(1)
if CHAT_ID <= 0:
    print("❌ Lỗi CHAT_ID không phải số hợp lệ!")
    exit(1)
# ==========================================================================

bot = telebot.TeleBot(BOT_TOKEN)
TEN_TEP = "dulieu_xsmb.json"
SO_NGAY_GIU = 60

app = Flask(__name__)
@app.route('/')
def giu_song(): return "✅ Bot XSMB đang chạy giữ kết nối!"
def chay_web(): app.run(host="0.0.0.0", port=int(os.environ.get("PORT",8080)))

TRONG_SO = {"DB":2.5, "G1":2.0, "G2":1.6, "G3":1.3, "G4":1.0, "G5":0.8, "G6":0.6, "G7":0.4}

def lay_2cuoi(so_nguyen): return str(so_nguyen).strip()[-2:]
def tai_dulieu():
    if os.path.exists(TEN_TEP):
        with open(TEN_TEP,"r",encoding="utf-8") as f: return json.load(f)
    return {}

def luu_dulieu_va_giu_60ngay(ngay_moi, dict_ngay):
    dl = tai_dulieu()
    dl[ngay_moi] = dict_ngay
    try:
        ds_sapxep = sorted(dl.keys(), key=lambda x: datetime.strptime(x,"%d/%m"))
    except:
        ds_sapxep = sorted(dl.keys())
    while len(ds_sapxep) > SO_NGAY_GIU:
        ngay_cu_nhat = ds_sapxep.pop(0)
        del dl[ngay_cu_nhat]
    with open(TEN_TEP,"w",encoding="utf-8") as f: json.dump(dl,f,ensure_ascii=False,indent=2)
    return len(ds_sapxep)

def tinh_top3_tat_ca_giai(ngay_can_doi):
    dl = tai_dulieu()
    ds_ngay = sorted(dl.keys(), key=lambda x:datetime.strptime(x,"%d/%m"))
    if len(ds_ngay)<60: return f"⚠️ Hiện có {len(ds_ngay)} ngày dữ liệu, cần đủ ít nhất 60 ngày để tính chính xác!"
    
    vi_tri = ds_ngay.index(ngay_can_doi)
    khung_60 = ds_ngay[vi_tri-60:vi_tri]

    thongke = defaultdict(lambda: {"diem":0, "ngay_xuat":[], "nguon_giai":[]})
    for thu_tu,ngay in enumerate(khung_60):
        dict_giai = dl[ngay]
        for ten_giai, danh_sach_so in dict_giai.items():
            if isinstance(danh_sach_so, str): danh_sach_so = [danh_sach_so]
            for so_nguyen_day_du in danh_sach_so:
                if not so_nguyen_day_du: continue
                duoi = lay_2cuoi(so_nguyen_day_du)
                thongke[duoi]["diem"] += TRONG_SO[ten_giai]
                thongke[duoi]["ngay_xuat"].append(thu_tu)
                thongke[duoi]["nguon_giai"].append(ten_giai)

    ketqua_danh_sach = []
    for duoi, chi_tiet in thongke.items():
        so_lan = len(chi_tiet["ngay_xuat"])
        if so_lan < 3: continue
        khoang_cach = [chi_tiet["ngay_xuat"][i+1]-chi_tiet["ngay_xuat"][i] for i in range(so_lan-1)]
        tb_khoang = sum(khoang_cach)/len(khoang_cach) if khoang_cach else 99
        diem_deu = max(0, 40 - sum(abs(x-tb_khoang) for x in khoang_cach)/len(khoang_cach)) if khoang_cach else 0
        ngay_da_nghi = len(khung_60)-1 - chi_tiet["ngay_xuat"][-1]
        diem_nghi = 30 if 5 <= ngay_da_nghi <= 12 else max(0, 25 - abs(ngay_da_nghi - 8))
        lan_gan = sum(1 for vt in chi_tiet["ngay_xuat"] if vt >= len(khung_60)-15)
        diem_gan = lan_gan *5
        tong_diem_cuoi = round(chi_tiet["diem"]*7 + diem_deu + diem_nghi + diem_gan)
        ketqua_danh_sach.append( (duoi, tong_diem_cuoi, round(tb_khoang), list(set(chi_tiet["nguon_giai"]))) )

    sap_xep_cao_xuong = sorted(ketqua_danh_sach, key=lambda x:x[1], reverse=True)[:3]
    nd = datetime.strptime(ngay_can_doi,"%d/%m")
    ngaysau = nd.replace(day=nd.day+1).strftime("%d/%m")

    noi_dung = f"🔮 TOP 3 ĐUÔI CÓ XÁC SUẤT CAO NHẤT NGÀY {ngaysau}\n✅ Phân tích chung TẤT CẢ các giải, ưu tiên Giải Đặc biệt cao nhất\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    for stt,(duoi,diem,tb,nguon) in enumerate(sap_xep_cao_xuong,1):
        noi_dung += f"🥇{stt}. Đuôi: {duoi} | Tổng điểm: {diem}/100\n👉 Trung bình lặp mỗi {tb} ngày; chủ yếu từ: {', '.join(nguon)}\n\n"
    return noi_dung if sap_xep_cao_xuong else "⚠️ Cần thêm vài ngày dữ liệu nữa để đủ quy luật!"

# === LỆNH KIỂM TRA HOẠT ĐỘNG NGAY LẬP TỨC ===
@bot.message_handler(commands=['kiemtra','start'])
def kiemtra(msg):
    bot.send_message(msg.chat.id, "✅ Bot XSMB đang HOẠT ĐỘNG! 🟢\n📸 Gửi ảnh kết quả hoặc /kiemtra đều trả lời được rồi nhé!")

# === NHẬN ẢNH & XỬ LÝ ===
@bot.message_handler(content_types=['photo'])
def xu_ly_anh(msg):
    # Chỉ xử lý đúng Chat ID của bạn an toàn
    if msg.chat.id != CHAT_ID: return
    bot.reply_to(msg,"🔍 Đang đọc ảnh, lưu số đủ & phân tích...")
    info = msg.photo[-1]
    file_info = bot.get_file(info.file_id)
    url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_info.file_path}"
    img_data = requests.get(url).content
    with open("tam.jpg","wb") as f: f.write(img_data)
    try:
        text_doc = pytesseract.image_to_string(Image.open("tam.jpg"), lang="vie+num")
        tim_ngay = re.search(r"ngày\s+(\d{1,2}/\d{1,2})", text_doc)
        if not tim_ngay: bot.reply_to(msg,"❌ Không nhận rõ ngày, ghi rõ: Ngày xx/xx giúp bot nhé!");return
        ngay = tim_ngay.group(1)
        du_lieu_ngay = {"DB":"", "G1":"", "G2":["",""], "G3":["","","","","",""], "G4":["","","",""], "G5":["","","","","",""], "G6":["","",""], "G7":["","","",""]}
        so_con = luu_dulieu_va_giu_60ngay(ngay, du_lieu_ngay)
        bot.reply_to(msg,f"✅ Đã lưu thành công ngày {ngay}\n📦 Đang giữ {so_con} ngày mới nhất\n\n{tinh_top3_tat_ca_giai(ngay)}")
    except Exception as e: bot.reply_to(msg,f"❌ Lỗi: {str(e)}")

if __name__=="__main__":
    Thread(target=chay_web, daemon=True).start()
    bot.polling(none_stop=True, interval=3, timeout=180, long_polling_timeout=180)
