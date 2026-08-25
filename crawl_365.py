import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import time
from database import save_result, count_results, get_date_range

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def crawl_xsmb_single_day(date_obj):
    """Cào kết quả XSMB theo ngày sử dụng nguồn xoso.com.vn"""
    date_web = date_obj.strftime("%d-%m-%Y")
    date_db = date_obj.strftime("%Y-%m-%d")
    
    url = f"https://xoso.com.vn/ket-qua-theo-ngay.html?date={date_web}"
    try:
        res = requests.get(url, headers=HEADERS, timeout=8)
        if res.status_code != 200:
            return False

        soup = BeautifulSoup(res.content, 'html.parser')
        
        # Tìm tất cả các giải
        cells = soup.find_all('span', class_=['v-gdb', 'v-g1', 'v-g2', 'v-g3', 'v-g4', 'v-g5', 'v-g6', 'v-g7'])
        numbers = []
        for cell in cells:
            txt = cell.get_text(strip=True)
            if txt.isdigit() and len(txt) >= 2:
                numbers.append(txt)

        if len(numbers) >= 27:
            # Lưu trực tiếp vào xosomb.db qua hàm database.py
            save_result(date_db, numbers[:27])
            return True
        return False
    except Exception as e:
        print(f"Lỗi cào ngày {date_db}: {e}")
        return False

def main():
    print("🚀 Bắt đầu tiến trình cào dữ liệu 365 ngày vào xosomb.db...")
    today = datetime.now()
    success_count = 0

    for i in range(365):
        target_date = today - timedelta(days=i)
        date_db = target_date.strftime("%Y-%m-%d")
        
        print(f"🔄 [{i+1}/365] Đang kiểm tra/cào ngày {date_db}...", end=" ")
        
        if crawl_xsmb_single_day(target_date):
            print("✅ Thành công")
            success_count += 1
        else:
            print("⚠️ Không lấy được (hoặc đã có)")
            
        time.sleep(0.2) # Nghỉ để tránh bị chặn IP

    print("\n" + "="*40)
    print(f"🎉 HOÀN THÀNH!")
    print(f"📊 Tổng số ngày hiện có trong xosomb.db: {count_results()} ngày")
    min_d, max_d = get_date_range()
    print(f"📅 Khoảng dữ liệu: Từ {min_d} đến {max_d}")
    print("="*40)

if __name__ == "__main__":
    main()
