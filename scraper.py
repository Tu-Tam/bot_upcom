import re
import time
import random
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup
from database import save_result, init_db

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7"
}

def lay_ket_qua_knet(ngay_dt: datetime):
    """Cào dữ liệu chuẩn từ nguồn ketqua.net"""
    ngay_str = ngay_dt.strftime("%d-%m-%Y")
    url = f"https://ketqua.net/ket-qua-xosomb.php?ngay={ngay_str}"
    
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            return None

        soup = BeautifulSoup(resp.text, "html.parser")
        cac_so = {
            "special": None,
            "g1": [], "g2": [], "g3": [], "g4": [], "g5": [], "g6": [], "g7": []
        }

        # Bóc tách Giải Đặc Biệt
        db = soup.select_one("#rs_0_0")
        if db and db.text.strip().isdigit():
            cac_so["special"] = db.text.strip()

            # Bóc tách Giải 1 đến Giải 7
            for i in range(1, 8):
                elements = soup.select(f"[id^='rs_{i}_']")
                cac_so[f"g{i}"] = [e.text.strip() for e in elements if e.text.strip().isdigit()]

            return cac_so
    except Exception as e:
        print(f"Lỗi cào Knet: {e}")
    return None


def xu_ly_ngay(ngay: datetime):
    date_id = ngay.strftime("%Y-%m-%d")
    ngay_thang_vn = ngay.strftime("%d/%m/%Y")
    thu = ngay.weekday()

    print(f"🔍 Đang quét ngày {ngay_thang_vn}...")
    cac_so = lay_ket_qua_knet(ngay)

    if cac_so and cac_so["special"]:
        # Gom tất cả các dãy số thu thập được
        tat_ca = [cac_so["special"]]
        for i in range(1, 8):
            tat_ca.extend(cac_so[f"g{i}"])

        # Tạo nhóm Lô theo đầu số
        dau_so = {str(i): [] for i in range(10)}
        for s in tat_ca:
            if s and len(s) >= 2:
                dau_so[s[-2]].append(s)

        # Lưu kết quả vào CSDL
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
            print(f"✅ LƯU THÀNH CÔNG {date_id} | ĐB: {cac_so['special']}")
            return True

    print(f"❌ KHÔNG LẤY ĐƯỢC: {ngay_thang_vn}")
    return False


def tai_90_ngay_gan_nhat():
    init_db()
    dem = 0
    hom_nay = datetime.today()
    print("🚀 Bắt đầu quét liên tục 90 ngày...")
    
    for lui in range(90):
        ngay_can_lay = hom_nay - timedelta(days=lui)
        if xu_ly_ngay(ngay_can_lay):
            dem += 1
        time.sleep(random.uniform(0.3, 0.6))
        
    print(f"\n===== 📊 KẾT THÚC: LẤY ĐƯỢC {dem}/90 NGÀY =====")
    return dem


if __name__ == "__main__":
    tai_90_ngay_gan_nhat()