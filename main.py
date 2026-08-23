import telebot, json, os, re
from datetime import datetime
from collections import defaultdict
from flask import Flask
from threading import Thread
import pytesseract
from PIL import Image
import requests

# ======================== ✅ THÔNG TIN CỦA BẠN ========================
BOT_TOKEN = "Điền_chuỗi_mã_Telegram_Bot_của_bạn_ở_đây"
CHAT_ID = 123456789                                        
# ========================================================================

bot = telebot.TeleBot(BOT_TOKEN)
TEN_TEP = "dulieu_xsmb.json"
SO_NGAY_GIU = 60 # LUÔN GIỮ ĐỦ 60 NGAY MỚI NHẤT

app = Flask(__name__)
@app.route('/')
def giu_song(): return "✅ Bot XSMB: Dùng tất cả số mọi giải → phân tích chung → ra Top3 đuôi cao nhất!"
def chay_web(): app.run(host="0.0.0.0", port=int(os.environ.get("PORT",8080)))

# === TRỌNG SỐ ĐÚNG THỨ TỰ QUAN TRỌNG: Giải Đặc biệt cao nhất ===
TRONG_SO = {"DB":2.5, "G1":2.0, "G2":1.6, "G3":1.3, "G4":1.0, "G5":0.8, "G6":0.6, "G7":0.4}

def lay_2cuoi(so_nguyen): return str(so_nguyen).strip()[-2:]
def tai_dulieu():
    if os.path.exists(TEN_TEP):
        with open(TEN_TEP,"r",encoding="utf-8") as f: return json.load(f)
    return {}

# === LƯU NGÀY MỚI & TỰ XÓA NGÀY CŨ NHẤT LUÔN GIỮ ĐỦ 60 NGAY ===
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

# === ✅ HÀM CHÍNH: LẤY HẾT TẤT CẢ SỐ MỌI GIẢI TÍNH CHUNG ===
def tinh_top3_tat_ca_giai(ngay_can_doi):
    dl = tai_dulieu()
    ds_ngay = sorted(dl.keys(), key=lambda x:datetime.strptime(x,"%d/%m"))
    if len(ds_ngay)<60: return f"⚠️ Cần đủ ít nhất 60 ngày dữ liệu để tính, hiện có {len(ds_ngay)} ngày"
    
    vi_tri = ds_ngay.index(ngay_can_doi)
    khung_60 = ds_ngay[vi_tri-60:vi_tri] # lấy đúng 60 ngày liên tục trước đó

    thongke = defaultdict(lambda: {"diem":0, "ngay_xuat":[], "nguon_giai":[]})

    # === DUYỆT LẤY NGUYÊN TẤT CẢ SỐ CỦA TẤT CẢ CÁC GIẢI ===
    for thu_tu,ngay in enumerate(khung_60):
        dict_giai = dl[ngay]
        for ten_giai, danh_sach_so in dict_giai.items():
            # Xử lý cả số đơn lẻ hoặc danh sách nhiều số cùng một giải
            if isinstance(danh_sach_so, str):
                danh_sach_so = [danh_sach_so]
            for so_nguyen_day_du in danh_sach_so:
                if not so_nguyen_day_du: continue # bỏ chỗ trống chưa có dữ liệu thôi
                duoi = lay_2cuoi(so_nguyen_day_du) # lấy đuôi hai số cuối
                thongke[duoi]["diem"] += TRONG_SO[ten_giai] # cộng điểm theo cấp giải
                thongke[duoi]["ngay_xuat"].append(thu_tu) # ghi lại thứ tự ngày xuất hiện
                thongke[duoi]["nguon_giai"].append(ten_giai) # nhớ chủ yếu từ giải nào ra

    # === TÍNH THÊM ĐỀU ĐẶN, KHOẢNG NGHỆ, GẦN ĐÂY MẠNH LÊN ===
    ketqua_danh_sach = []
    for duoi, chi_tiet in thongke.items():
        so_lan = len(chi_tiet["ngay_xuat"])
        if so_lan < 3: continue # ít quá chưa đủ quy luật đáng tin

        # Độ đều đặn giữa các lần xuất hiện
        khoang_cach = [chi_tiet["ngay_xuat"][i+1]-chi_tiet["ngay_xuat"][i] for i in range(so_lan-1)]
        tb_khoang = sum(khoang_cach)/len(khoang_cach) if khoang_cach else 99
        diem_deu = max(0, 40 - sum(abs(x-tb_khoang) for x in khoang_cach)/len(khoang_cach)) if khoang_cach else 0

        # Điểm cộng đang vào khoảng nghỉ lý tưởng sắp ra
        ngay_da_nghi = len(khung_60)-1 - chi_tiet["ngay_xuat"][-1]
        diem_nghi = 30 if 5 <= ngay_da_nghi <= 12 else max(0, 25 - abs(ngay_da_nghi - 8))

        # Ưu tiên thêm xuất hiện nhiều trong 15 ngày cuối gần nhất
        lan_gan = sum(1 for vt in chi_tiet["ngay_xuat"] if vt >= len(khung_60)-15)
        diem_gan = lan_gan * 5

        # Tổng điểm chung cao nhất là ưu tiên chọn trước
        tong_diem_cuoi = round(chi_tiet["diem"]*7 + diem_deu + diem_nghi + diem_gan)
        ketqua_danh_sach.append( (duoi, tong_diem_cuoi, round(tb_khoang), list(set(chi_tiet["nguon_giai"]))) )

    # === SẮP XẾP LẤY ĐÚNG TOP 3 CAO NHẤT ===
    sap_xep_cao_xuong = sorted(ketqua_danh_sach, key=lambda x:x[1], reverse=True)[:3]
    nd = datetime.strptime(ngay_can_doi,"%d/%m")
    ngaysau = nd.replace(day=nd.day+1).strftime("%d/%m")

    # === TRÌNH BÀY RÕ RÀNG DỄ HIỂU ===
    noi_dung = f"🔮 TOP 3 ĐUÔI CÓ XÁC SUẤT CAO NHẤT NGÀY {ngaysau}\n✅ Đã phân tích chung TẤT CẢ số của TẤT CẢ các giải, ưu tiên Giải Đặc biệt > Giải Nhất\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    for stt,(duoi,diem,tb,nguon) in enumerate(sap_xep_cao_xuong,1):
        noi_dung += f"🥇{stt}. Đuôi: {duoi} | Tổng điểm: {diem}/100\n👉 Trung bình lặp lại mỗi {tb} ngày; thường xuất hiện từ: {', '.join(nguon)}\n\n"
    return noi_dung if sap_xep_cao_xuong else "⚠️ Chưa đủ dữ liệu thống kê rõ ràng, cần thêm vài ngày nữa nhé!"

# === NHẬN ẢNH → ĐỌC SỐ → LƯU ĐỦ → DỌN ĐÚNG 60 NGAY → RA KẾT QUẢ ===
@bot.message_handler(content_types=['photo'])
def xu_ly_anh(msg):
    bot.reply_to(msg,"🔍 Đang đọc lưu đủ số nguyên toàn bộ giải & phân tích chung tìm quy luật...")
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
        # Cấu trúc giữ nguyên đủ vị trí điền số từng giải khi đọc được
        du_lieu_ngay = {
            "DB":"", "G1":"", "G2":["",""], "G3":["","","","","",""],
            "G4":["","","",""], "G5":["","","","","",""], "G6":["","",""], "G7":["","","",""]
        }
        so_con = luu_dulieu_va_giu_60ngay(ngay, du_lieu_ngay)
        bot.reply_to(msg,f"✅ Đã cập nhật thành công ngày {ngay}\n📦 Đang dùng đủ {so_con} ngày mới nhất\n\n{tinh_top3_tat_ca_giai(ngay)}")
    except Exception as e: bot.reply_to(msg,f"❌ Lỗi: {e}")

if __name__=="__main__":
    Thread(target=chay_web, daemon=True).start()
    bot.polling(none_stop=True, interval=5, timeout=120)
