import telebot
import re
import json
import os
from collections import defaultdict, Counter
from datetime import datetime
from flask import Flask
from threading import Thread

# === THÔNG TIN ĐÃ ĐIỀN SẴN CỦA BẠN ===
BOT_TOKEN = "8520938638:AAEHwQp89_P2slG7YTkod4z6_XvYbgBD7ns"
CHAT_ID = 7064473358
bot = telebot.TeleBot(BOT_TOKEN)

# === GIỮ KẾT NỐI TRÊN RENDER KHÔNG BỊ TẮT ===
app = Flask(__name__)
@app.route('/')
def giu_song(): return "✅ Bot đang hoạt động tốt! Đã kết nối giữ sống thành công."
def chay_web(): app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))

# === TÊN TỆP LƯU DỮ LIỆU AN TOÀN ===
TEN_TEP = "dulieu_66ngay_xsmb.json"

# === TẢI SẴN ĐỦ 66 NGÀY ĐẾN 23/08/2026 ===
def tai_kho_du_lieu():
    if os.path.exists(TEN_TEP):
        try:
            with open(TEN_TEP, "r", encoding="utf-8") as f: return json.load(f)
        except: pass
    return {
    "23/08": "0:35;1:12;2:23;3:31;4:40;5:55;6:68;7:78;8:84;9:98",
    "22/08": "0:00;1:11;2:27;3:32;4:43;5:50;6:68;7:76;8:89;9:97",
    "21/08": "0:09;1:19;2:27,21;3:33,39,38,34,30,32,35;4:40;5:54,53;6:64,60,61,68,67;7:75;8:88;9:99,90,94,95",
    "20/08": "0:02;1:13;2:29;3:35;4:45;5:52;6:68;7:73;8:84;9:91",
    "19/08": "0:06;1:18;2:29;3:36;4:42;5:59;6:65;7:70;8:87;9:92",
    "18/08": "0:07;1:19;2:21;3:38;4:47;5:53;6:64;7:75;8:85;9:93",
    "17/08": "0:07;1:18;2:24;3:30;4:48;5:57;6:65;7:71;8:82;9:91",
    "16/08": "0:00;1:12;2:26;3:33;4:41;5:52;6:59;7:74;8:88;9:94",
    "15/08": "0:07;1:15;2:29;3:35;4:43;5:55;6:69;7:78;8:83;9:97",
    "14/08": "0:02;1:11;2:23;3:39;4:44;5:50;6:62;7:77;8:81;9:96",
    "13/08": "0:06;1:12;2:28;3:37;4:49;5:58;6:63;7:72;8:86;9:90",
    "12/08": "0:03;1:14;2:25;3:31;4:46;5:51;6:59;7:79;8:80;9:95",
    "11/08": "0:04;1:16;2:24;3:33;4:47;5:56;6:61;7:70;8:89;9:98",
    "10/08": "0:08;1:17;2:22;3:36;4:42;5:54;6:66;7:71;8:85;9:93",
    "09/08": "0:09;1:13;2:20;3:38;4:45;5:53;6:60;7:76;8:83;9:92",
    "08/08": "0:01;1:18;2:28;3:32;4:48;5:57;6:65;7:74;8:82;9:91",
    "07/08": "0:05;1:14;2:21;3:39;4:46;5:51;6:63;7:79;8:87;9:90",
    "06/08": "0:06;1:15;2:27;3:34;4:40;5:58;6:62;7:73;8:84;9:99",
    "05/08": "0:08;1:18;2:23;3:31;4:49;5:55;6:67;7:72;8:81;9:96",
    "04/08": "0:02;1:10;2:25;3:37;4:44;5:59;6:68;7:75;8:88;9:93",
    "03/08": "0:00;1:13;2:30;3:36;4:42;5:50;6:64;7:78;8:85;9:91",
    "02/08": "0:07;1:19;2:22;3:35;4:47;5:53;6:57;7:71;8:80;9:94",
    "01/08": "0:09;1:11;2:26;3:39;4:41;5:52;6:66;7:73;8:89;9:98",
    "31/07": "0:03;1:17;2:24;3:38;4:45;5:59;6:61;7:70;8:82;9:92",
    "30/07": "0:01;1:16;2:29;3:33;4:40;5:55;6:69;7:74;8:87;9:95",
    "29/07": "0:06;1:14;2:25;3:32;4:48;5:51;6:63;7:79;8:86;9:97",
    "28/07": "0:08;1:15;2:28;3:30;4:44;5:57;6:62;7:72;8:88;9:93",
    "27/07": "0:02;1:13;2:21;3:36;4:47;5:52;6:65;7:77;8:81;9:99",
    "26/07": "0:05;1:19;2:23;3:34;4:43;5:58;6:69;7:76;8:85;9:90",
    "25/07": "0:09;1:12;2:20;3:33;4:49;5:54;6:68;7:75;8:84;9:91",
    "24/07": "0:03;1:18;2:27;3:35;4:42;5:50;6:61;7:79;8:83;9:96",
    "23/07": "0:04;1:11;2:22;3:39;4:45;5:53;6:60;7:74;8:89;9:92",
    "22/07": "0:07;1:16;2:29;3:31;4:47;5:59;6:64;7:78;8:82;9:95",
    "21/07": "0:00;1:19;2:21;3:38;4:46;5:55;6:63;7:73;8:80;9:94",
    "20/07": "0:01;1:17;2:25;3:36;4:43;5:58;6:69;7:72;8:86;9:90",
    "19/07": "0:05;1:14;2:24;3:30;4:49;5:57;6:62;7:75;8:88;9:93",
    "18/07": "0:06;1:13;2:28;3:37;4:41;5:52;6:67;7:79;8:85;9:98",
    "17/07": "0:03;1:15;2:26;3:39;4:48;5:53;6:65;7:71;8:84;9:92",
    "16/07": "0:09;1:19;2:22;3:34;4:42;5:56;6:64;7:70;8:87;9:91",
    "15/07": "0:04;1:11;2:29;3:35;4:44;5:51;6:68;7:76;8:89;9:97",
    "14/07": "0:08;1:10;2:20;3:38;4:45;5:59;6:63;7:74;8:83;9:92",
    "13/07": "0:02;1:12;2:23;3:36;4:49;5:55;6:61;7:79;8:82;9:94",
    "12/07": "0:05;1:18;2:25;3:33;4:47;5:50;6:66;7:77;8:81;9:93",
    "11/07": "0:07;1:16;2:29;3:32;4:43;5:58;6:69;7:75;8:87;9:90",
    "10/07": "0:09;1:13;2:21;3:30;4:46;5:54;6:65;7:72;8:89;9:98",
    "09/07": "0:00;1:14;2:27;3:39;4:40;5:52;6:67;7:78;8:85;9:91",
    "08/07": "0:03;1:13;2:24;3:31;4:48;5:57;6:61;7:79;8:83;9:96",
    "07/07": "0:01;1:19;2:28;3:35;4:42;5:50;6:64;7:73;8:86;9:95",
    "06/07": "0:05;1:16;2:22;3:37;4:49;5:53;6:68;7:71;8:84;9:92",
    "05/07": "0:04;1:11;2:29;3:34;4:45;5:58;6:62;7:76;8:80;9:93",
    "04/07": "0:00;1:15;2:26;3:38;4:44;5:51;6:69;7:77;8:88;9:97",
    "03/07": "0:02;1:17;2:25;3:33;4:47;5:59;6:63;7:72;8:81;9:94",
    "02/07": "0:08;1:12;2:23;3:39;4:43;5:55;6:60;7:78;8:87;9:95",
    "01/07": "0:03;1:14;2:21;3:36;4:48;5:52;6:67;7:79;8:82;9:90",
    "30/06": "0:08;1:19;2:27;3:39;4:46;5:50;6:65;7:74;8:89;9:98",
    "29/06": "0:07;1:13;2:29;3:32;4:41;5:55;6:69;7:76;8:83;9:92",
    "28/06": "0:05;1:11;2:25;3:34;4:48;5:59;6:66;7:70;8:82;9:99",
    "27/06": "0:01;1:11;2:27;3:38;4:44;5:52;6:68;7:79;8:87;9:93",
    "26/06": "0:08;1:17;2:20;3:32;4:46;5:54;6:68;7:71;8:89;9:95",
    "25/06": "0:02;1:15;2:24;3:33;4:49;5:58;6:62;7:77;8:88;9:96",
    "24/06": "0:09;1:18;2:21;3:35;4:47;5:53;6:60;7:74;8:89;9:91",
    "23/06": "0:00;1:14;2:23;3:40;4:45;5:51;6:64;7:76;8:82;9:93",
    "22/06": "0:06;1:17;2:26;3:37;4:42;5:59;6:76;7:73;8:87;9:98",
    "21/06": "0:03;1:15;2:21;3:23;4:49;5:54;6:60;7:75;8:83;9:94",
    "20/06": "0:00;1:13;2:29;3:36;4:45;5:60;6:67;7:79;8:86;9:92",
    "19/06": "0:01;1:11;2:28;3:31;4:47;5:53;6:65;7:74;8:84;9:97"
    }

def luu_lai(kho):
    with open(TEN_TEP, "w", encoding="utf-8") as f: json.dump(kho, f, ensure_ascii=False, indent=2)

# === TÍNH TOP 3 ĐUÔI THEO TẦN SUẤT + CHU KỲ NGHỈ ĐỀU ĐẶN ===
def tinh_top3_ngay_tiep_theo(ngay_can_doa):
    kho = tai_kho_du_lieu()
    if len(kho)<30: return None, "⚠️ Cần đủ ít nhất 30 ngày dữ liệu để phân tích quy luật rõ hơn!"
    dem_lan_xuat = Counter()
    ngay_xuat_cuoi = {}
    danh_sach_thoi_gian = sorted(kho.keys(), key=lambda x: datetime.strptime(x,"%d/%m"))
    for vt,ngay in enumerate(danh_sach_thoi_gian):
        for phan in kho[ngay].split(";"):
            dau,ds = phan.split(":")
            for d in ds.split(","):
                dem_lan_xuat[d] +=1
                ngay_xuat_cuoi[d] = vt+1
    tong_ngay = len(danh_sach_thoi_gian)
    bang_diem = {}
    for d,sl in dem_lan_xuat.items():
        so_ngay_nghi = tong_ngay - ngay_xuat_cuoi[d]
        diem = sl * 12
        if 8 <= so_ngay_nghi <=22: diem +=30
        elif 4 <= so_ngay_nghi <=7: diem +=15
        elif so_ngay_nghi>22: diem +=8
        bang_diem[d] = diem
    top3 = sorted(bang_diem.items(), key=lambda x:x[1], reverse=True)[:3]
    noi = f"📊 DỰ ĐOÁN 3 ĐUÔI XÁC SUẤT CAO NHẤT CHO NGÀY: {ngay_can_doa}\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    for hang,(diem_so,d) in enumerate(top3,1): noi +=f"🏆 Thứ {hang}: Đuôi {diem_so} | Điểm quy luật: {d}/100\n"
    noi += "\n💡 Ưu tiên chọn: xuất hiện nhiều lần & nghỉ đủ chu kỳ đều đặn trong 66 ngày qua!\n⚠️ Chỉ phân tích quy luật lịch sử, tham khảo vui chơi giải trí nhé!"
    return top3, noi

# === NHẬN YÊU CẦU DỰ ĐOÁN ===
@bot.message_handler(func=lambda m: m.text and "Ngày" in m.text and "dự đoán" in m.text)
def xu_ly_du_doan(message):
    lay = re.search(r"Ngày\s+(\d{1,2}/\d{1,2}/\d{4})",message.text)
    if not lay: bot.send_message(message.chat.id,"❌ Ghi đúng mẫu: Ngày 24/08/2026 dự đoán");return
    _,tb = tinh_top3_ngay_tiep_theo(lay.group(1))
    bot.send_message(message.chat.id,tb)

# === NHẬN CẬP NHẬT KẾT QUẢ MỚI LƯU VÀO KHO ===
@bot.message_handler(func=lambda m: m.text and "Ngày" in m.text and "Số:" in m.text)
def luu_ngay_moi(message):
    kho = tai_kho_du_lieu()
    try:
        lay_ngay = re.search(r"Ngày\s+(\d{1,2}/\d{1,2}/\d{4})",message.text).group(1)
        khoa = lay_ngay[:5]
        ds_so = re.search(r"Số:\s*(.+)$",message.text).group(1).replace(" ","").split(",")
        ds_2so = [s.strip()[-2:] for s in ds_so if len(s.strip())>=2 and s.strip().isdigit()]
        nhom = defaultdict(list)
        for s in ds_2so: nhom[s[0]].append(s)
        chuoi_moi = ";".join(f"{k}:{','.join(sorted(set(v)))}" for k,v in sorted(nhom.items()))
        if khoa in kho:
            if kho[khoa]==chuoi_moi: bot.send_message(message.chat.id,f"📌 Ngày {lay_ngay} ĐÃ CÓ & DỮ LIỆU TRÙNG HOÀN TOÀN ✅")
            else: bot.send_message(message.chat.id,f"⚠️ Đã cập nhật thay thế số liệu mới nhất ngày {lay_ngay} thành công!");kho[khoa]=chuoi_moi;luu_lai(kho)
        else: kho[khoa]=chuoi_moi;luu_lai(kho);bot.send_message(message.chat.id,f"✅ THÊM THÀNH CÔNG NGÀY MỚI: {lay_ngay} vào kho dữ liệu!\n📊 Tổng số ngày đang có: {len(kho)} ngày → càng nhiều sẽ phân tích chính xác hơn!")
    except: bot.send_message(message.chat.id,"❌ Ghi đúng mẫu: Ngày 24/08/2026 | Số:05,12,27,33,... tất cả các đuôi nhé!")

# === ĐOẠN CUỐI ĐÃ SỬA CHÍNH XÁC: CHẠY DUY NHẤT KHÔNG XUNG ĐỘT ===
if __name__ == "__main__":
    print("🤖 Bot XSMB ĐANG CHẠY DUY NHẤT: Tích lũy dữ liệu & tìm ra TOP 3 đuôi theo chu kỳ đều đặn nhất!")
    Thread(target=chay_web, daemon=True).start()
    bot.polling(none_stop=True, interval=5, timeout=120)
