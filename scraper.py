import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import time, random, re
from database import save_result, init_db

# ✅ Nguồn chính rất ổn định + dự phòng
SOURCES = [
    "https://ketqua-xo-so.vn/xo-so-mien-bac/",
    "https://xosomb.com/lich-su-xo-so-mien-bac/",
    "https://xosohn.com/xsmb-xo-so-mien-bac.html"
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "Chrome/130.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "vi-VN,vi;q=0.8,en-US;q=0.5,en;q=0.3"
}


def xu_ly_ngay(ngay: datetime, retries_per_source=2):
    date_id = ngay.strftime("%Y-%m-%d")
    ngay_thang = ngay.strftime("%d/%m/%Y")
    thu = ngay.weekday()

    for link in SOURCES:
        attempt = 0
        while attempt <= retries_per_source:
            try:
                attempt += 1
                print(f"🔍 Đọc {ngay_thang} từ: {link} (lần {attempt})")
                resp = requests.get(link, headers=HEADERS, params={"ngay": ngay_thang}, timeout=25)
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text, "html.parser")

                # 🔎 Cách tìm rộng hơn, phù hợp nhiều cấu trúc bảng
                cac_so = {
                    "special": None,
                    "g1": [], "g2": [], "g3": [], "g4": [], "g5": [], "g6": [], "g7": []
                }

                # ✅ Giải đặc biệt
                db_tag = soup.select_one(".dacbiet .so, .db, .special-number, td:contains('Đặc biệt') + td, .kq-db strong")
                if db_tag:
                    cac_so["special"] = db_tag.get_text(strip=True).strip()

                # ✅ Các giải 1–7
                cac_hang = soup.select("table.kq tr, .bang-kq tr, .result-row, tbody tr")
                stt_giai = 1
                for hang in cac_hang:
                    cac_cot = hang.find_all("td")
                    if len(cac_cot) >= 2:
                        # Lấy tất cả số 2/5 chữ số
                        so_hang = []
                        for cot in cac_cot[1:]:
                            van_ban = cot.get_text(" ", strip=True)
                            so_trong = [s.strip() for s in re.findall(r"\b\d{2,5}\b", van_ban)]
                            so_hang.extend(so_trong)
                        if so_hang and stt_giai <= 7:
                            cac_so[f"g{stt_giai}"] = so_hang
                            stt_giai += 1

                # ✅ Kiểm tra đủ dữ liệu cơ bản
                if cac_so["special"] and any(len(cac_so[f"g{i}"]) for i in range(1, 8)):
                    # Tạo nhóm đầu số theo cấu trúc CSDL của bạn
                    tat_ca = [cac_so["special"]]
                    for i in range(1, 8):
                        tat_ca.extend(cac_so[f"g{i}"])

                    dau_so = {str(i): [] for i in range(10)}
                    for s in tat_ca:
                        if s and len(s) >= 2:
                            dau_so[s[0]].append(s)

                    # 💾 Lưu chuẩn cấu trúc database.py
                    luu_ok = save_result({
                        "date": date_id,
                        "special": cac_so["special"],
                        "g1": cac_so["g1"],
                        "g2": cac_so["g2"],
                        "g3": cac_so["g3"],
                        "g4": cac_so["g4"],
                        "g5": cac_so["g5"],
                        "g6": cac_so["g6"],
                        "g7": cac_so["g7"],
                        "loto_by_head": dau_so,
                        "weekday": thu
                    })
                    if luu_ok:
                        print(f"✅ LƯU THÀNH CÔNG {date_id} | Đặc biệt: {cac_so['special']}")
                        return True
            except Exception as e:
                print(f"⚠️ Lỗi {link} → {str(e)[:120]}...")
                # nhẹ nhàng backoff nếu còn thử
                time.sleep(min(2 ** attempt, 8))
            # nghỉ nhỏ giữa 2 lần thử cùng nguồn
            time.sleep(random.uniform(0.4, 1.0))
    print(f"❌ KHÔNG LẤY ĐƯỢC: {ngay_thang}")
    return False


def tai_90_ngay_gan_nhat():
    init_db()
    dem = 0
    hom_nay = datetime.today()
    print(f"🚀 Bắt đầu quét liên tục 90 ngày...")
    for lui in range(90):
        ngay_can_lay = hom_nay - timedelta(days=lui)
        try:
            if xu_ly_ngay(ngay_can_lay):
                dem += 1
        except Exception as e:
            print(f"⚠️ Lỗi xử lý ngày {ngay_can_lay}: {e}")
        # Giảm tốc độ tổng thể để tránh bị rate-limit
        time.sleep(random.uniform(0.25, 0.9))
    print(f"\n===== 📊 KẾT THÚC: LẤY ĐƯỢC {dem}/90 NGÀY =====")
    return dem


if __name__ == "__main__":
    tai_90_ngay_gan_nhat()
