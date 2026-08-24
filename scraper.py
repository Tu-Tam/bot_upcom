import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import time, random, json
from database import save_result, init_db

# Nguồn dự phòng & ổn định
SOURCES = [
    {"url": "https://xosohn.com/xsmb-xo-so-mien-bac.html", "type": "table"},
    {"url": "https://ketqua.vn/xo-so-mien-bac", "type": "div"},
    {"url": "https://xsmb.vn/lich-su-xo-so-mien-bac", "type": "classic"}
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "Chrome/125.0.0.0 Safari/537.36",
    "Accept-Language": "vi-VN,vi;q=0.9,en;q=0.8"
}


def parse_date_slug(d, m, y):
    return f"{y}-{m:02d}-{d:02d}"


def extract_numbers(text_list):
    """Làm sạch & chỉ lấy số có độ dài hợp lệ xổ số (2, 5 chữ số)"""
    nums = []
    for txt in text_list:
        s = "".join(c for c in txt if c.isdigit())
        if len(s) in (2, 5):
            nums.append(s)
    return nums


def build_loto_by_head(all_numbers):
    """Tạo nhóm theo đầu số (0→9) giống cấu trúc CSDL của bạn"""
    heads = {str(i): [] for i in range(10)}
    for num in all_numbers:
        if isinstance(num, str) and len(num) >= 2:
            first = num[0]
            heads[first].append(num)
    return heads


def lay_ngay_va_luu(ngay):
    """Lấy 1 ngày & gọi trực tiếp save_result() của database.py"""
    date_id = parse_date_slug(ngay.day, ngay.month, ngay.year)
    weekday = ngay.weekday()
    found = False

    for src in SOURCES:
        try:
            resp = requests.get(src["url"], headers=HEADERS, timeout=18)
            resp.raise_for_status()
            resp.encoding = "utf-8"
            soup = BeautifulSoup(resp.text, "html.parser")

            # Tìm theo nhiều cấu trúc bảng/dữ liệu phổ biến
            rows = soup.select("table.kq-table tr, .bang-kq tr, .result-table tr")
            data = {"special": None, "g1": [], "g2": [], "g3": [], "g4": [], "g5": [], "g6": [], "g7": []}

            for r in rows:
                cells = [c.get_text(strip=True) for c in r.find_all(["td", "div", "span"]) if c.get_text(strip=True)]
                if not cells:
                    continue
                label = cells[0].upper()
                vals = extract_numbers(cells[1:])
                if "ĐẶC BIỆT" in label or "DB" in label:
                    data["special"] = vals[0] if vals else None
                elif "GIẢI 1" in label:
                    data["g1"] = vals
                elif "GIẢI 2" in label:
                    data["g2"] = vals
                elif "GIẢI 3" in label:
                    data["g3"] = vals
                elif "GIẢI 4" in label:
                    data["g4"] = vals
                elif "GIẢI 5" in label:
                    data["g5"] = vals
                elif "GIẢI 6" in label:
                    data["g6"] = vals
                elif "GIẢI 7" in label:
                    data["g7"] = vals

            if data["special"] and any(len(data[f"g{i}"]) for i in range(1, 8)):
                full_list = [data["special"]]
                for i in range(1, 8):
                    full_list.extend(data[f"g{i}"])
                loto_head = build_loto_by_head(full_list)

                # ✅ Định dạng CHUẨN để hàm save_result của bạn đọc ngay không lỗi
                save_result({
                    "date": date_id,
                    "special": data["special"],
                    "g1": data["g1"],
                    "g2": data["g2"],
                    "g3": data["g3"],
                    "g4": data["g4"],
                    "g5": data["g5"],
                    "g6": data["g6"],
                    "g7": data["g7"],
                    "loto_by_head": loto_head,
                    "weekday": weekday
                })
                print(f"✅ {date_id} | Đặc biệt: {data['special']}")
                found = True
                break

        except Exception as e:
            print(f"⚠️ Nguồn {src['url']} lỗi {date_id}: {str(e)[:60]}...")
            time.sleep(0.3)

    if not found:
        print(f"❌ Không lấy được: {date_id}")
    return found


def tai_90_ngay_gan_nhat():
    """Quét liên tục đủ 90 ngày & báo tổng kết"""
    init_db()
    start_point = datetime.today()
    ok = 0
    for day_back in range(90):
        day = start_point - timedelta(days=day_back)
        if lay_ngay_va_luu(day):
            ok += 1
        time.sleep(random.uniform(0.25, 0.9))  # chống chặn

    print(f"\n=== 📊 HOÀN TẤN: Đã xử lý {ok}/90 ngày vào CSDL ===")
    return ok


if __name__ == "__main__":
    tai_90_ngay_gan_nhat()
