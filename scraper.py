import requests
from bs4 import BeautifulSoup
import time
from datetime import datetime, timedelta
from database import save_result, count_results

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

def lay_ket_qua_ngay(date_str):
    """Cào kết quả XSMB theo ngày (YYYY-MM-DD)"""
    try:
        d_obj = datetime.strptime(date_str, "%Y-%m-%d")
        formatted_date = d_obj.strftime("%d-%m-%Y")
        
        url = f"https://xosodaiphat.com/xsmb-{formatted_date}.html"
        response = requests.get(url, headers=HEADERS, timeout=5)
        
        if response.status_code != 200:
            return None

        soup = BeautifulSoup(response.text, 'html.parser')
        numbers = []
        
        for cell in soup.select('.table-xsmb span, .table-xsmb td'):
            txt = cell.text.strip()
            if txt.isdigit() and len(txt) >= 2:
                numbers.append(txt)

        if len(numbers) >= 20:
            return numbers[:27]
            
        return None

    except Exception as e:
        print(f"Lỗi cào ngày {date_str}: {e}", flush=True)
        return None

def scrape_past_days(days=90):
    """Quét dữ liệu lịch sử X ngày (Đã alias tên hàm để tương thích hoàn toàn với bot.py)"""
    print(f"🚀 Bắt đầu quét dữ liệu {days} ngày...", flush=True)
    start_date = datetime.now() - timedelta(days=1)
    thanh_cong = 0

    for i in range(days):
        current_date = (start_date - timedelta(days=i)).strftime("%Y-%m-%d")
        print(f"🔍 Đang quét ngày {current_date}...", flush=True)
        
        data = lay_ket_qua_ngay(current_date)
        if data:
            save_result(current_date, data)
            thanh_cong += 1
            print(f"  └─ ✅ Đã lưu thành công!", flush=True)
        else:
            print(f"  └─ ❌ Không tìm thấy hoặc lỗi dữ liệu.", flush=True)

        time.sleep(0.3)

    print(f"🎉 Hoàn tất! Đã lưu tổng cộng {thanh_cong} ngày.", flush=True)
    return count_results()

def scrape_today():
    """Hàm cào kết quả hôm nay cho bot.py"""
    today_str = datetime.now().strftime("%Y-%m-%d")
    data = lay_ket_qua_ngay(today_str)
    if data:
        save_result(today_str, data)
        return True
    return False

# Giữ lại tên hàm cũ để tránh đứt gãy nếu có module khác gọi
tai_90_ngay_gan_nhat = scrape_past_days