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

def lay_ket_qua_xsthantai(ngay_dt: datetime):
    """Cào từ nguồn xsthantai / ketqua.vn (Rất ổn định cho dữ liệu quá khứ)"""
    date_str_url = ngay_dt.strftime("%d-%m-%Y")
    url = f"https://ketqua01.net/so-ket-qua/mien-bac/{date_str_url}"
    
    resp = requests.get(url, headers=HEADERS, timeout=15)
    if resp.status_code != 200:
        return None

    soup = BeautifulSoup(resp.text, "html.parser")
    
    # Tìm bảng kết quả
    table = soup.find("table", id=lambda x: x and "kq" in x.lower()) or soup.find("table")
    if not table:
        return None

    cac_so = {
        "special": None,
        "g1": [], "g2": [], "g3": [], "g4": [], "g5": [], "g6": [], "g7": []
    }

    # Bóc tách Giải đặc biệt
    db_node = soup.select_one("#rs_0_0, .rs_0, .dacbiet, .special-code")
    if db_node:
        cac_so["special"] = db_node.get_text(strip=True)

    # Bóc tách các giải 1-7
    for g in range(1, 8):
        nodes = soup.select(f"#rs_{g}_0, #rs_{g}_1, #rs_{g}_2, #rs_{g}_3, #rs_{g}_4, #rs_{g}_5, .rs_{g}")
        if nodes:
            cac_so[f"g{g}"] = [n.get_text(strip=True) for n in nodes if n.get_text(strip=True).isdigit()]

    if cac_so["special"]:
        return cac_so
    return None


def xu_ly_ngay(ngay: datetime):
    date_id = ngay.strftime("%Y-%m-%d")
    ngay_thang_vn = ngay.strftime("%d/%m/%Y")
    thu = ngay.weekday()

    # Thử lấy dữ liệu từ nguồn API/HTML chuẩn
    try:
        print(f"🔍 Đang quét ngày {ngay_thang_vn}...")
        
        # Nguồn 1: Ketqua.net API / Direct Page
        url_knet = f"https://ketqua.net/ket-qua-xosomb.php?ngay={ngay.strftime('%d-%m-%Y')}"
        resp = requests.get(url_knet, headers=HEADERS, timeout=15)
        
        cac_so = {
            "special": None,
            "g1": [], "g2": [], "g3": [], "g4": [], "g5": [], "g6": [], "g7": []
        }

        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            
            # Tìm giải đặc biệt
            db = soup.select_one("#rs_0_0")
            if db and db.text.strip().isdigit():
                cac_so["special"] = db.text.strip()

                # Tìm giải 1 đến 7
                for i in range(1, 8):
                    elements = soup.select(f"[id^='rs_{i}_']")
                    cac_so[f"g{i}"] = [e.text.strip() for e in elements if e.text.strip().isdigit()]

        # Nếu Nguồn 1 xịt, chuyển sang Nguồn dự phòng
        if not cac_so["special"]:
            data_dp = lay_ket_qua_xsthantai(ngay)
            if data_dp:
                cac_so = data_dp

        # Kiểm tra nếu cào thành công
        if cac_so["special"]:
            tat_ca = [cac_so["special"]]
            for i in range(1, 8):
                tat_ca.extend(cac_so[f"g{i}"])

            dau_so = {str(i): [] for i in range(10)}
            for s in tat_ca:
                if s and len(s) >= 2:
                    dau_so[s[-2]].append(s) # Lấy 2 số cuối (Lô)

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

    except Exception as e:
        print(f"⚠️ Lỗi ngày {date_id}: {str(e)[:50]}")

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
