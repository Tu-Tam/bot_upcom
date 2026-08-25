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
        # Chuyển format YYYY-MM-DD sang DD-MM-YYYY
        d_obj = datetime.strptime(date_str, "%Y-%m-%d")
        formatted_date = d_obj.strftime("%d-%m-%Y")
        
        # Nguồn dữ liệu xosodaiphat / xoso
        url = f"https://xosodaiphat.com/xsmb-{formatted_date}.html"

        response = requests.get(url, headers=HEADERS, timeout=4)
        if response.status_code != 200:
            return None

        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Lấy tất cả các ô chứa số giải thưởng
        numbers = []
        # Tìm các class chứa kết quả xổ số
        for cell in soup.select('.table-xsmb span, .table-xsmb td'):
            txt = cell.text.strip()
            if txt.isdigit() and len(txt) >= 2:
                numbers.append(txt)

        # Một kết quả XSMB đủ phải có 27 giải (hoặc ít nhất 20 số)
        if len(numbers) >= 20:
            return numbers[:27]
            
        return None

    except Exception as e:
        print(f"  └─ ⚠️ Bỏ qua {date_str} (Lỗi: {e})")
        return None

def tai_90_ngay_gan_nhat():
    """
    Quét lùi 90 ngày tính từ ngày hôm qua (tránh cào ngày chưa quay)
    """
    print("🚀 Bắt đầu quét dữ liệu 90 ngày...")
    # Lấy từ ngày hôm qua để đảm bảo đã có kết quả
    start_date = datetime.now() - timedelta(days=1)
    thanh_cong = 0

    for i in range(90):
        current_date = (start_date - timedelta(days=i)).strftime("%Y-%m-%d")
        print(f"🔍 Đang quét ngày {current_date}...", flush=True)
        
        data = lay_ket_qua_ngay(current_date)
        if data:
            save_result(current_date, data)
            thanh_cong += 1
            print(f"  └─ ✅ Đã lưu thành công!", flush=True)
        else:
            print(f"  └─ ❌ Không tìm thấy dữ liệu.", flush=True)

        # Delay ngắn 0.3s để tăng tốc độ nhưng không bị block
        time.sleep(0.3)

    print(f"🎉 Hoàn tất! Đã lưu tổng cộng {thanh_cong} ngày vào CSDL.", flush=True)
    return count_results()