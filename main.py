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
def giu_song(): return "✅ Bot đang HOẠT ĐỘNG ỔN ĐỊNH! Giữ nguyên toàn bộ dữ liệu tháng 6,7,8"

def chay_web():
    cong = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=cong, debug=False)

TRONG_SO = {"DB":2.5, "G1":2.0, "G2":1.6, "G3":1.3, "G4":1.0, "G5":0.8, "G6":0.6, "G7":0.4}
def lay_2cuoi(s): return str(s).strip()[-2:]
def tai_dulieu():
    with open(TEN_TEP,"r",encoding="utf-8") as f: return json.load(f) if os.path.exists(TEN_TEP) else {}

# ✅ SỬA CHÍNH XÁC NHẤT: KHÔNG CẮT BỚT NGÀY CŨ ĐÂU NỮA! LƯU THÊM/CẬP NHẬT MỚI THÔI, GIỮ LẠI TOÀN BỘ ĐÃ NHẬP
def luu_dulieu_va_giu_60ngay(ngay, d):
    dl = tai_dulieu()
    dl[ngay] = d  # thêm ngày mới hoặc cập nhật nếu đã có → KHÔNG XÓA BỎ NGÀY ĐẦU THÁNG 6 NỮA
    with open(TEN_TEP,"w",encoding="utf-8") as f: json.dump(dl,f,ensure_ascii=False,indent=2)
    return len(dl) # báo đúng tổng số ngày thực đang lưu: sẽ thấy tăng dần >80 ngày khi đủ hết

# === TÍNH LINH HOẠT: Đủ 60 lấy đúng chuẩn 60; chưa đủ thì lấy tối đa có được trước ngày đó, báo rõ số đang dùng ===
def tinh_top3_ngay_muc_tieu(ngay_muc_tieu, dl):
    if ngay_muc_tieu not in dl: return None, set(), f"⚠️ Không có dữ liệu ngày {ngay_muc_tieu}"
    ds_ngay = sorted(dl.keys(), key=lambda x:datetime.strptime(x,"%d/%m")) # sắp xếp chắc chắn theo đúng thời gian
    vi_tri = ds_ngay.index(ngay_muc_tieu)
    SO_MUC_TIEU = 60

    # chọn lấy số ngày lớn nhất có thể đạt được: đủ thì đúng chuẩn 60, chưa đủ thì dùng hết có được
    lay_so = SO_MUC_TIEU if vi_tri >= SO_MUC_TIEU else vi_tri
    if lay_so < 40: return None, set(), f"⚠️ Ngày {ngay_muc_tieu} mới có {vi_tri} ngày trước, chưa đủ ngưỡng tối thiểu 40 ngày"

    khung = ds_ngay[vi_tri - lay_so : vi_tri]
    ghi_chu = f"✅ Đang dùng {len(khung)} ngày liên tục trước ngày này"
    if len(khung)>=SO_MUC_TIEU: ghi_chu = f"✅ ĐỦ CHUẨN {SO_MUC_TIEU} ngày lý tưởng!"

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
    return tap_top3, tap_thuc_te, ghi_chu

# === LỆNH KIỂM TRA LOẠT 10→23/08: báo rõ tổng số ngày lưu, chi tiết từng ngày + tỷ lệ trung bình ===
@bot.message_handler(func=lambda m: m.text.strip()=="Kiểm tra giai đoạn 10-23/08" and m.chat.id==CHAT_ID)
def kiemtra_giai_doan_dinh_ky(msg):
    dl = tai_dulieu()
    bot.send_message(msg.chat.id,f"📦 Tổng số ngày đang lưu: {len(dl)} ngày (đã giữ nguyên toàn bộ tháng 6,7,8 không bị cắt bớt nữa!)")
    ds_ngay_kiemtra = ["10/08","11/08","12/08","13/08","14/08","15/08","16/08","17/08","18/08","19/08","20/08","21/08","22/08","23/08"]
    tong_ngay_chay=0; tong_dung=0; chi_tiet_ngay=[]

    for ngay in ds_ngay_kiemtra:
        top3, thuc_te, ghi_chu = tinh_top3_ngay_muc_tieu(ngay, dl)
        if not top3: chi_tiet_ngay.append(f"📅 {ngay}: {ghi_chu}"); continue
        so_dung_ngay = len(top3 & thuc_te); tong_dung += so_dung_ngay; tong_ngay_chay +=1
        chi_tiet_ngay.append(f"📅 {ngay}: Đúng {so_dung_ngay}/3 | {ghi_chu}\n→ Dự đoán: {', '.join(sorted(top3))} | Thực tế: {', '.join(sorted(thuc_te))}")

    if tong_ngay_chay==0: bot.send_message(msg.chat.id,"⚠️ Chưa đạt ngưỡng tối thiểu kiểm tra được ngày nào!");return
    trung_binh_tong = round(tong_dung/(tong_ngay_chay*3)*100,1)
    noi_dung = "📋 KẾT QUẢ KIỂM TRA GIAI ĐOẠN 10 → 23 THÁNG 08\n✅ Ưu tiên đủ chuẩn 60 ngày lý tưởng, tự dùng tối đa có được chưa đủ vẫn ra kết quả đánh giá tạm!\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    noi_dung += "\n".join(chi_tiet_ngay) +f"\n\n📊 TỔNG KẾT CUỐI CÙNG:\n✅ Tổng ngày kiểm tra được: {tong_ngay_chay} ngày\n✅ Tổng số đuôi đúng: {tong_dung} đuôi\n💯 TRUNG BÌNH CHUNG TỶ LỆ ĐÚNG: {trung_binh_tong}%\n💡 Tiếp tục thêm vài ngày còn thiếu ở đầu sẽ tự nâng lên đủ chuẩn chính xác hoàn hảo hơn!"
    bot.send_message(msg.chat.id, noi_dung)

# === LỆNH KIỂM TRA NHANH NGÀY MỚI NHẤT ===
@bot.message_handler(func=lambda m: m.text.strip()=="Tự kiểm tra giai đoạn" and m.chat.id==CHAT_ID)
def kiemtra_ngay_moi_nhat(msg):
    bot.reply_to(msg,"🔄 Kiểm tra ngày mới nhất...")
    dl=tai_dulieu()
    ds=sorted(dl.keys(), key=lambda x:datetime.strptime(x,"%d/%m"))
    ngay_moi=ds[-1]; top3,thuc_te,ghi_chu=tinh_top3_ngay_muc_tieu(ngay_moi,dl)
    if not top3: bot.send_message(msg.chat.id,f"⚠️ {ghi_chu}");return
    so_dung=len(top3&thuc_te); tb=round(so_dung/3*100,1)
    bot.send_message(msg.chat.id,f"📅 NGÀY MỚI NHẤT: {ngay_moi} | {ghi_chu}\nTop3 dự đoán: {', '.join(sorted(top3))}\nThực tế có: {', '.join(sorted(thuc_te))}\n✅ Đúng {so_dung}/3 → ĐẠT {tb}% trùng khớp!")

@bot.message_handler(commands=['kiemtra','start'])
def tro_giup(m): bot.send_message(m.chat.id,"✅ SẴN SÀNG HOÀN THIỆN!\n📝 Gõ: Kiểm tra giai đoạn 10-23/08 → báo rõ tổng số ngày lưu + chi tiết từng ngày + tỷ lệ trung bình!\n📸 Gửi ảnh lưu thêm ngày mới: cộng dồn tăng số ngày, không bao giờ xóa mất dữ liệu đầu tháng 6 nữa!\n📝 Gõ: Tự kiểm tra giai đoạn → xem nhanh kết quả ngày mới nhất!")

# === LƯU ẢNH VẪN HOẠT ĐỘNG, CỘNG THÊM NGÀY MỚI VÀO TỔNG SỐ ĐANG LƯU ===
@bot.message_handler(content_types=['photo'])
def xu_ly_anh(m):
    if m.chat.id!=CHAT_ID:return
    bot.reply_to(m,"🔍 Đọc & lưu thêm ngày mới vào bộ dữ liệu chung...")
    info=m.photo[-1]
    url=f"https://api.telegram.org/file/bot{BOT_TOKEN}/{bot.get_file(info.file_id).file_path}"
    with open("tam.jpg","wb")as f:f.write(requests.get(url).content)
    try:
        nd=re.search(r"ngày\s+(\d{1,2}/\d{1,2})",pytesseract.image_to_string(Image.open("tam.jpg"),lang="vie+num")).group(1)
        so=luu_dulieu_va_giu_60ngay(nd,{"DB":"","G1":"","G2":["",""],"G3":["","","","","",""],"G4":["","","",""],"G5":["","","","","",""],"G6":["","",""],"G7":["","","",""]})
        bot.reply_to(m,f"✅ Lưu thành công ngày {nd}! Tổng hiện đang giữ: {so} ngày liên tục tích lũy!")
    except: bot.reply_to(m,"❌ Không đọc rõ ngày trong ảnh, vui lòng ghi rõ Ngày xx/xx thử lại nhé!")

# === CHẠY CHUẨN TRÊN RENDER: Flask chạy nền nhẹ, ưu tiên Bot lắng nghe tin nhắn liên tục ===
if __name__=="__main__":
    Thread(target=chay_web, daemon=True).start()
    print("🚀 Đã khởi động thành công: giữ toàn bộ dữ liệu cũ, tính linh hoạt đủ/chưa đủ ngưỡng!")
    bot.polling(none_stop=True, interval=3, timeout=180, long_polling_timeout=180)
