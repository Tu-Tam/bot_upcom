import requests
from bs4 import BeautifulSoup
import time
from datetime import datetime, timedelta
from database import save_result, count_results

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

def lay_ket_qua_ngay(date_str):
    """Cào kết quả XSMB theo ngày (YYYY-MM-DD) sử dụng xoso.com.vn (Hỗ trợ 365+ ngày)"""
    try:
        d_obj = datetime.strptime(date_str, "%Y-%m-%d")
        formatted_date = d_obj.strftime("%d-%m-%Y")
        
        url = f"https://xoso.com.vn/ket-qua-theo-ngay.html?date={formatted_date}"
        response = requests.get(url, headers=HEADERS, timeout=6)
        
        if response.status_code != 200:
            return None

        soup = BeautifulSoup(response.text, 'html.parser')
        numbers = []
        
        # Bắt các class thẻ chứa giải thưởng của xoso.com.vn
        cells = soup.find_all('span', class_=['v-gdb', 'v-g1', 'v-g2', 'v-g3', 'v-g4', 'v-g5', 'v-g6', 'v-g7'])
        for cell in cells:
            txt = cell.get_text(strip=True)
            if txt.isdigit() and len(txt) >= 2:
                numbers.append(txt)

        if len(numbers) >= 20:
            return numbers[:27]
            
        return None

    except Exception as e:
        print(f"Lỗi cào ngày {date_str}: {e}", flush=True)
        return None

def scrape_past_days(days=365):
    """Quét dữ liệu lịch sử X ngày (Mặc định 365 ngày)"""
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

        time.sleep(0.2)

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

# Alias để giữ tính tương thích
tai_90_ngay_gan_nhat = scrape_past_days