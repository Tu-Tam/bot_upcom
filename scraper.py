import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import time
import random

# Danh sách nguồn tin cậy, dự phòng nhau
NGUON = [
    "https://xosohn.com/xsmb-xo-so-mien-bac.html",
    "https://ketqua.vn/xo-so-mien-bac",
    "https://xsmb.vn/lich-su-xo-so-mien-bac"
]

def lay_ket_qua_mien_bac_90_ngay():
    """Quét tự động đủ 90 ngày gần nhất, trả về danh sách dict: ngày + tất cả các giải"""
    du_lieu = []
    ngay_hien_tai = datetime.today()

    for i in range(90):
        ngay_can_lay = ngay_hien_tai - timedelta(days=i)
        ngay_str = ngay_can_lay.strftime("%d/%m/%Y")
        da_lay_du = False

        for link in NGUON:
            try:
                tieu_de = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                                  "(KHTML, như Gecko) Chrome/120.0.0.0 Safari/537.36"
                }
                resp = requests.get(link, headers=tieu_de, timeout=15)
                resp.encoding = "utf-8"
                soup = BeautifulSoup(resp.text, "html.parser")

                # Tìm bảng kết quả theo ngày (cấu trúc phổ biến)
                bang = soup.find("table", class_="table-kq") or soup.find("div", class_="ketqua-ngay")
                if not bang:
                    continue

                cac_giai = []
                for hang in bang.find_all("tr"):
                    o_td = hang.find_all("td")
                    if len(o_td) >= 2:
                        # Lấy tất cả số trong mỗi giải
                        cac_so = [s.get_text(strip=True) for s in o_td if s.get_text(strip=True).isdigit() or len(s.get_text(strip=True)) in [2,5,6]]
                        if cac_so:
                            cac_giai.extend(cac_so)

                if len(cac_giai) >= 10:  # Đủ số lượng giải tối thiểu XSMB
                    du_lieu.append({
                        "ngay": ngay_str,
                        "cac_giai": cac_giai
                    })
                    print(f"✅ Đã lấy: {ngay_str} – {len(cac_giai)} số")
                    da_lay_du = True
                    break
            except Exception as e:
                print(f"⚠️ Lỗi {ngay_str} – thử nguồn khác: {str(e)[:40]}...")
                continue

        if not da_lay_du:
            print(f"❌ Không lấy được: {ngay_str}")

        # Nghỉ ngẫu nhiên để không bị chặn
        time.sleep(random.uniform(0.4, 1.2))

    return du_lieu


def cap_nhat_vao_csdl(du_lieu, ham_luu_ngay):
    """Chèn dữ liệu đã quét vào DB, kiểm tra trùng thông minh"""
    dem_moi = 0
    for ban_ghi in du_lieu:
        if ham_luu_ngay(ban_ghi["ngay"], ban_ghi["cac_giai"]):
            dem_moi += 1
    return dem_moi
