import requests
from bs4 import BeautifulSoup
import re
import time
from datetime import datetime, timedelta
from database import save_result, count_results

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

def lay_ket_qua_ngay(date_str):
    """
    Cào kết quả XSMB theo ngày format YYYY-MM-DD
    """
    try:
        # Chuyển YYYY-MM-DD sang DD-MM-YYYY cho URL
        d_obj = datetime.strptime(date_str, "%Y-%m-%d")
        formatted_date = d_obj.strftime("%d-%m-%Y")
        url = f"https://xoso.com.vn/xsmb-{formatted_date}.html"

        # Thêm timeout 5s tránh treo luồng
        response = requests.get(url, headers=HEADERS, timeout=5)
        if response.status_code != 200:
            return None

        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Tìm bảng kết quả
        table = soup.find('table', class_='table-result')
        if not table:
            return None

        numbers = []
        # Lấy toàn bộ các giải
        for td in table.find_all('td', class_=re.compile(r'v-giai|number')):
            txt = td.text.strip()
            # Tìm các chuỗi số từ 2 đến 5 chữ số
            found = re.findall(r'\b\d{2,5}\b', txt)
            numbers.extend(found)

        if len(numbers) >= 20: # Một kỳ XSMB chuẩn có 27 giải
            return numbers
        return None

    except Exception as e:
        print(f"⚠️ Lỗi cào ngày {date_str}: {e}")
        return None

def tai_90_ngay_gan_nhat():
    """
    Quét lùi 90 ngày từ hôm nay, lưu vào CSDL
    """
    print("🚀 Bắt đầu quét dữ liệu 90 ngày...")
    today = datetime.now()
    thanh_cong = 0

    for i in range(90):
        current_date = (today - timedelta(days=i)).strftime("%Y-%m-%d")
        print(f"🔍 Đang quét ngày {current_date}...")
        
        data = lay_ket_qua_ngay(current_date)
        if data:
            save_result(current_date, data)
            thanh_cong += 1
            print(f"  └─ ✅ Đã lưu {current_date}")
        else:
            print(f"  └─ ❌ Bỏ qua/Không có số {current_date}")

        # Tạm dừng 0.5s giữa các request tránh bị chặn IP
        time.sleep(0.5)

    print(f"🎉 Hoàn tất! Đã lưu tổng cộng {thanh_cong} ngày.")
    return count_results()