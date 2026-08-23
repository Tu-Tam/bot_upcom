import telebot, json, os, re
from datetime import datetime
from collections import defaultdict
from flask import Flask
from threading import Thread
import pytesseract
from PIL import Image
import requests

# ======================== BIẾN MÔI TRƯỜNG AN TOÀN ========================
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
CHAT_ID = int(os.getenv("CHAT_ID", 0))

if not BOT_TOKEN or ":" not in BOT_TOKEN:
    print("❌ Lỗi BOT_TOKEN không hợp lệ!")
    exit(1)
if CHAT_ID <= 0:
    print("❌ Lỗi CHAT_ID phải là số dương!")
    exit(1)
# ===========================================================================

bot = telebot.TeleBot(BOT_TOKEN)
TEN_TEP = "dulieu_xsmb.json" # GIỮ TOÀN BỘ DỮ LIỆU THÁNG 6,7,8 KHÔNG CẮT BỚT NỮA

app = Flask(__name__)
@app.route('/')
def giu_song(): return "✅ Bot đang HOẠT ĐỘNG ỔN ĐỊNH! Giữ kết nối thành công!"

def chay_web():
    cong = int(os.environ.get("PORT", 10000)) # Đọc đúng cổng động Render cấp
    app.run(host="0.0.0.0", port=cong, debug=False)

TRONG_SO = {"DB":2.5, "G1":2.0, "G2":1.6, "G3":1.3, "G4":1.0, "G5":0.8, "G6":0.6, "G7":0.4}
def lay_2cuoi(s): return str(s).strip()[-2:]
def tai_dulieu():
    with open(TEN_TEP,"r",encoding="utf-8") as f: return json.load(f) if os.path.exists(TEN_TEP) else {}

# ✅ QUAN TRỌNG: KHÔNG XÓA NGÀY ĐẦU THÁNG 6 NỮA, CỘNG THÊM/CẬP NHẬT MỚI THÔI
def luu_dulieu_va_giu_60ngay(ngay, d):
    dl = tai_dulieu()
    dl[ngay] = d
    with open(TEN_TEP,"w",encoding="utf-8") as f: json.dump(dl,f,ensure_ascii=False,indent=2)
    return len(dl)

# === Lấy CHÍNH XÁC 60 ngày lùi TRƯỚC từng ngày kiểm tra ===
def tinh_top3_ngay_muc_tieu(ngay_muc_tieu, dl):
    if ngay_muc_tieu not in dl: return None, set(), f"⚠️ Không có dữ liệu ngày {ngay_muc_tieu}"
    ds_ngay = sorted(dl.keys(), key=lambda x:datetime.strptime(x,"%d/%m"))
    vi_tri = ds_ngay.index(ngay_muc_tieu)
    SO_CAN = 60
    if vi_tri >= SO_CAN:
        khung = ds_ngay[vi_tri - SO_CAN : vi_tri]
        ghi = "✅ Đủ chuẩn 60 ngày"
    else: return None, set(), f"⚠️ Chưa đủ {SO_CAN} ngày trước ngày này"

    thongke = defaultdict(lambda: {"diem":0, "ngay_xuat":[], "nguon":[]})
    for thu_tu,ngay in enumerate(khung):
        for gt,ds in dl[ngay].items():
            for s in ([ds] if isinstance(ds,str) else ds):
                if s:
                    d=lay_2cuoi(s); thongke[d]["diem"]+=TRONG_SO[gt]
                    thongke[d]["ngay_xuat"].append(thu_tu); thongke[d]["nguon"].append(gt)

    ds_xep = []
    for duoi,tt in thongke.items():
        sl=len(tt["ngay_xuat"])
        if sl<4:continue
        ngay_nghi = len(khung)-1 - tt["ngay_xuat"][-1]
        if 4 <= ngay_nghi <=12: diem_nghi=30
        elif 3<=ngay_nghi<=15: diem_nghi=18
        else: diem_nghi=max(0, 5-abs(ngay_nghi-8))
        lan_gan = sum(1 for v in tt["ngay_xuat"] if v >= len(khung)-15)
        diem_gan = lan_gan *7
        khoang = [tt["ngay_xuat"][i+1]-tt["ngay_xuat"][i] for i in range(sl-1)]
        tb_khoang = sum(khoang)/len(khoang) if khoang else 99
        lech = sum(abs(x-tb_khoang) for x in khoang)/len(khoang) if khoang else 50
        diem_deu = max(0,45-lech)
        tong_diem = round(tt["diem"]*8 + diem_deu + diem_nghi + diem_gan)
        ds_xep.append((duoi,tong_diem))

    top3 = sorted(ds_xep, key=lambda x:-x[1])[:3]
    tap_top3 = set(x[0] for x in top3)
    tap_thuc_te = set()
    for gt,ds in dl[ngay_muc_tieu].items():
        for s in ([ds]if isinstance(ds,str)else ds):
            if s: tap_thuc_te.add(lay_2cuoi(s))
    return tap_top3, tap_thuc_te, ghi

# === LỆNH KIỂM TRA LOẠT 10-23/08 ĐÚNG ĐỦ ===
@bot.message_handler(func=lambda m: m.text.strip()=="Kiểm tra giai đoạn 10-23/08" and m.chat.id==CHAT_ID)
def kiemtra_giai_doan(msg):
    dl = tai_dulieu()
    bot.send_message(msg.chat.id,f"📦 Tổng số ngày đang lưu: {len(dl)} ngày (giữ nguyên từ đầu tháng 6!)")
    ds_ngay = ["10/08","11/08","12/08","13/08","14/08","15/08","16/08","17/08","18/08","19/08","20/08","21/08","22/08","23/08"]
    tong_ngay=0; tong_dung=0; chi_tiet=[]
    for ngay in ds_ngay:
        kq,tt,ghi = tinh_top3_ngay_muc_tieu(ngay,dl)
        if not kq: chi_tiet.append(f"📅 {ngay}: {ghi}");continue
        so_dung=len(kq&tt); tong_dung+=so_dung; tong_ngay+=1
        chi_tiet.append(f"📅 {ngay}: Đúng {so_dung}/3 | {ghi}\nDự đoán: {', '.join(sorted(kq))} | Thực tế: {', '.join(sorted(tt))}")
    if tong_ngay==0: bot.send_message(msg.chat.id,"⚠️ Chưa đủ điều kiện ngày nào trong giai đoạn!");return
    tb_chung = round(tong_dung/(tong_ngay*3)*100,1)
    nd_bao = "📋 KẾT QUẢ KIỂM TRA 10→23/08\n━━━━━━━━━━━━━━━━━━━━\n"+"\n".join(chi_tiet)+f"\n\n📊 TRUNG BÌNH CHUNG: {tb_chung}% đúng!\n✅ Đánh giá chính xác hiệu quả logic!"
    bot.send_message(msg.chat.id,nd_bao)

# === LỆNH PHỤ, LƯU ẢNH VẪN HOẠT ĐỘNG ===
@bot.message_handler(func=lambda m: m.text.strip()=="Tự kiểm tra giai đoạn" and m.chat.id==CHAT_ID)
def kiemtra_ngay_moi(msg):
    dl=tai_dulieu(); ds=sorted(dl.keys(), key=lambda x:datetime.strptime(x,"%d/%m"))
    if len(ds)<60: bot.send_message(msg.chat.id,f"⚠️ Tổng {len(ds)} ngày, cần đủ ít nhất 60!");return
    ngay_moi=ds[-1];kq,tt,ghi=tinh_top3_ngay_muc_tieu(ngay_moi,dl)
    so_dung=len(kq&tt);tb=round(so_dung/3*100,1)
    bot.send_message(msg.chat.id,f"📅 Ngày mới nhất: {ngay_moi} | {ghi}\nTop3: {', '.join(sorted(kq))}\nThực tế: {', '.join(sorted(tt))}\n✅ Đúng {so_dung}/3 → {tb}%")

@bot.message_handler(commands=['kiemtra','start'])
def tro_giup(m): bot.send_message(m.chat.id,"✅ SẴN SÀNG!\n📝 Kiểm tra giai đoạn 10-23/08 → báo đủ số ngày & tỷ lệ trung bình!\n📸 Gửi ảnh lưu tiếp giữ nguyên dữ liệu cũ không mất!")

@bot.message_handler(content_types=['photo'])
def xu_ly_anh(m):
    if m.chat.id!=CHAT_ID:return
    bot.reply_to(m,"🔍 Đọc & lưu thêm ngày mới...")
    info=m.photo[-1]
    url=f"https://api.telegram.org/file/bot{BOT_TOKEN}/{bot.get_file(info.file_id).file_path}"
    with open("tam.jpg","wb")as f:f.write(requests.get(url).content)
    try:
        nd=re.search(r"ngày\s+(\d{1,2}/\d{1,2})",pytesseract.image_to_string(Image.open("tam.jpg"),lang="vie+num")).group(1)
        so=luu_dulieu_va_giu_60ngay(nd,{"DB":"","G1":"","G2":["",""],"G3":["","","","","",""],"G4":["","","",""],"G5":["","","","","",""],"G6":["","",""],"G7":["","","",""]})
        bot.reply_to(m,f"✅ Lưu thành công ngày {nd}! Tổng đang giữ: {so} ngày!")
    except: bot.reply_to(m,"❌ Không đọc rõ ngày, ghi rõ Ngày xx/xx nhé!")

# === ✅ CÁCH KHỞI ĐỘNG CHUẨN: Chạy Flask luồng phụ trước, ưu tiên luồng chính lắng nghe tin nhắn ===
if __name__=="__main__":
    Thread(target=chay_web, daemon=True).start() # chạy nền nhẹ, không chiếm luồng chính
    print("🚀 Bot đã khởi động thành công, lắng nghe tin nhắn...")
    bot.polling(none_stop=True, interval=3, timeout=180, long_polling_timeout=180)
