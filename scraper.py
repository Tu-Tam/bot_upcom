import requests
from bs4 import BeautifulSoup
import time
from datetime import datetime, timedelta
from database import save_result, count_results

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Accept-Language': 'vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7',
}

def lay_ket_qua_ngay_nguon_chinh(date_str):
    """Nguồn 1: xosodaiphat.com"""
    try:
        d_obj = datetime.strptime(date_str, "%Y-%m-%d")
        formatted_date = d_obj.strftime("%d-%m-%Y")
        
        url = f"https://xosodaiphat.com/xsmb-{formatted_date}.html"
        response = requests.get(url, headers=HEADERS, timeout=7)
        
        if response.status_code != 200:
            return None

        soup = BeautifulSoup(response.text, 'html.parser')
        numbers = []
        
        table = soup.find('table', class_=['table-xsmb', 'results-table'])
        if table:
            for cell in table.find_all(['td', 'span']):
                txt = cell.get_text(strip=True)
                if txt.isdigit() and len(txt) >= 2:
                    numbers.append(txt)

        if len(numbers) >= 20:
            return numbers[:27]
            
        return None
    except Exception:
        return None

def lay_ket_qua_ngay_du_phong(date_str):
    """Nguồn 2 (Dự phòng): xoso.com.vn"""
    try:
        d_obj = datetime.strptime(date_str, "%Y-%m-%d")
        formatted_date = d_obj.strftime("%d-%m-%Y")
        
        url = f"https://xoso.com.vn/ket-qua-theo-ngay.html?date={formatted_date}"
        response = requests.get(url, headers=HEADERS, timeout=7)
        
        if response.status_code != 200:
            return None

        soup = BeautifulSoup(response.text, 'html.parser')
        numbers = []
        
        cells = soup.select('.table-result span, .table-result td, .v-gdb, .v-g1, .v-g2, .v-g3, .v-g4, .v-g5, .v-g6, .v-g7')
        for cell in cells:
            txt = cell.get_text(strip=True)
            if txt.isdigit() and len(txt) >= 2:
                numbers.append(txt)

        if len(numbers) >= 20:
            return numbers[:27]
            
        return None
    except Exception:
        return None

def lay_ket_qua_ngay(date_str):
    """Thử cào từ nguồn chính, nếu thất bại tự chuyển sang nguồn dự phòng"""
    res = lay_ket_qua_ngay_nguon_chinh(date_str)
    if not res:
        res = lay_ket_qua_ngay_du_phong(date_str)
    return res

def scrape_past_days(days=365):
    """Quét dữ liệu lịch sử X ngày (Mặc định 365 ngày)"""
    print(f"🚀 Bắt đầu quét dữ liệu {days} ngày...", flush=True)
    start_date = datetime.now() - timedelta(days=1)
    thanh_cong = 0

    for i in range(days):
        current_date = (start_date - timedelta(days=i)).strftime("%Y-%m-%d")
        
        data = lay_ket_qua_ngay(current_date)
        if data:
            save_result(current_date, data)
            thanh_cong += 1
            print(f"  └─ ✅ [{i+1}/{days}] Ngày {current_date}: Đã lưu {len(data)} giải", flush=True)
        else:
            print(f"  └─ ❌ [{i+1}/{days}] Ngày {current_date}: Không cào được dữ liệu", flush=True)

        time.sleep(0.3)

    print(f"🎉 Hoàn tất! Đã lưu tổng cộng {thanh_cong} ngày vào CSDL.", flush=True)
    return count_results()

def scrape_today():
    """Hàm cào kết quả hôm nay cho bot.py"""
    today_str = datetime.now().strftime("%Y-%m-%d")
    data = lay_ket_qua_ngay(today_str)
    if data:
        save_result(today_str, data)
        return True
    
    yesterday_str = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    data_yesterday = lay_ket_qua_ngay(yesterday_str)
    if data_yesterday:
        save_result(yesterday_str, data_yesterday)
        
    return False

# Alias giữ tính tương thích
tai_90_ngay_gan_nhat = scrape_past_days