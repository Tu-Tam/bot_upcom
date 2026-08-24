import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import time, random, json
from database import save_result, init_db

# Nguồn đáng tin cậy & dự phòng nhau
SOURCES = [
    {"url": "https://xosoketqua.com/xo-so-mien-bac-ngay-", "type": "html5"},
    {"url": "https://xosohn.com/xsmb-xo-so-mien-bac.html", "type": "table"},
    {"url": "https://ketqua1.net/xsmb/", "type": "div_layout"}
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Accept-Language": "vi-VN,vi;q=0.9,en;q=0.8",
    "Referer": "https://www.google.com/"
}


def format_date_url(date_obj):
    """Tạo định dạng ngày chuẩn để ghép vào link nếu cần"""
    return date_obj.strftime("%d-%m-%Y")


def parse_date_for_db(date_obj):
    """Định dạng ngày lưu vào CSDL: YYYY-MM-DD"""
    return date_obj.strftime("%Y-%m-%d")


def build_loto_by_head(all_numbers):
    """Tạo nhóm theo đầu số khớp cấu trúc database của bạn"""
    heads = {str(i): [] for i in range(10)}
    for num in all_numbers:
        s = str(num).strip()
        if len(s) >= 2:
            heads[s[0]].append(s)
    return heads


def extract_numbers(raw_list):
    """Làm sạch, chỉ lấy số có độ dài hợp lệ XSMB"""
    res = []
    for txt in raw_list:
        clean = "".join(c for c in txt if c.isdigit())
        if len(clean) in (2, 5):
            res.append(clean)
    return res


def lay_du_lieu_ngay(ngay: datetime):
    """Quét thử từng nguồn cho đến khi ra dữ liệu hoàn chỉnh"""
    date_str_db = parse_date_for_db(ngay)
    weekday = ngay.weekday()

    for src in SOURCES:
        try:
            link = src["url"] + format_date_url(ngay) if "ngay-" in src["url"] else src["url"]
            resp = requests.get(link, headers=HEADERS, timeout=20)
            resp.raise_for_status()
            resp.encoding = "utf-8"
            soup = BeautifulSoup(resp.text, "html.parser")

            # Trích xuất theo cấu trúc linh hoạt
            dac_biet = soup.select_one(".db span, .dacbiet b, td.special, div.ketqua-db strong")
            cac_giai = {f"g{i}": [] for i in range(1, 8)}

            # Lấy giải đặc biệt
            if dac_biet:
                db_val = "".join(c for c in dac_biet.get_text(strip=True) if c.isdigit())
            else:
                db_val = None

            # Quét các giải từ 1 → 7
            rows = soup.select("table.kq-table tr, .bang-ketqua tr, .result-block tr, tbody tr")
            hang_giai = 1
            for r in rows:
                cac_otd = [td.get_text(strip=True) for td in r.find_all(["td", "span", "div"], recursive=True) if td.get_text(strip=True)]
                if not cac_otd:
                    continue
                so_hop_le = extract_numbers(cac_otd)
                if 0 < hang_giai <= 7 and so_hop_le:
                    cac_giai[f"g{hang_giai}"] = so_hop_le
                    hang_giai += 1

            # Xác nhận đủ thành phần cơ bản
            if db_val and any(cac_giai[f"g{i}"] for i in range(1, 8)):
                toan_bo_so = [db_val]
                for i in range(1, 8):
                    toan_bo_so.extend(cac_giai[f"g{i}"])
                loto_head = build_loto_by_head(toan_bo_so)

                # 💡 Lưu theo cấu trúc chính xác của database.py
                luu_thanh_cong = save_result({
                    "date": date_str_db,
                    "special": db_val,
                    "g1": cac_giai["g1"],
                    "g2": cac_giai["g2"],
                    "g3": cac_giai["g3"],
                    "g4": cac_giai["g4"],
                    "g5": cac_giai["g5"],
                    "g6": cac_giai["g6"],
                    "g7": cac_giai["g7"],
                    "loto_by_head": loto_head,
                    "weekday": weekday
                })
                if luu_thanh_cong:
                    print(f"✅ [{date_str_db}] OK — Đặc biệt: {db_val}")
                    return True
        except Exception as e:
            print(f"⚠️ Nguồn lỗi {link} — {str(e)[:65]}...")
            time.sleep(random.uniform(0.35, 0.7))
    print(f"❌ [{date_str_db}] KHÔNG TÌM THẤY DỮ LIỆU HỢP LỆ")
    return False


def tai_90_ngay_gan_nhat():
    """Quét liên tục đủ 90 ngày, trả về số ngày lưu thành công"""
    init_db()
    bat_dau = datetime.today()
    dem_ok = 0
    for lui_ve in range(90):
        ngay_can = bat_dau - timedelta(days=lui_ve)
        if lay_du_lieu_ngay(ngay_can):
            dem_ok += 1
        time.sleep(random.uniform(0.25, 0.85))  # Tránh bị chặn tường lửa
    print(f"\n=== 📊 KẾT THÚC: Đã lấy được {dem_ok}/90 ngày ===")
    return dem_ok


if __name__ == "__main__":
    print("🚀 Bắt đầu quét 90 ngày kiểm tra cục bộ...")
    tai_90_ngay_gan_nhat()
