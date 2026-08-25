import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import time
from database import save_result, count_results, get_date_range

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

def crawl_day(date_obj):
    date_web = date_obj.strftime("%d-%m-%Y")
    date_db = date_obj.strftime("%Y-%m-%d")
    url = f"https://xoso.com.vn/ket-qua-theo-ngay.html?date={date_web}"
    
    try:
        res = requests.get(url, headers=HEADERS, timeout=5)
        if res.status_code != 200:
            return False

        soup = BeautifulSoup(res.content, 'html.parser')
        cells = soup.find_all('span', class_=['v-gdb', 'v-g1', 'v-g2', 'v-g3', 'v-g4', 'v-g5', 'v-g6', 'v-g7'])
        numbers = [c.get_text(strip=True) for c in cells if c.get_text(strip=True).isdigit()]

        if len(numbers) >= 27:
            # Ghi chèn/cập nhật vào xosomb.db mà KHÔNG XÓA dữ liệu cũ
            save_result(date_db, numbers[:27])
            return True
        return False
    except Exception:
        return False

print("🚀 Đang tiến hành nạp lùi 365 ngày vào CSDL...")
today = datetime.now()
for i in range(365):
    target_date = today - timedelta(days=i)
    success = crawl_day(target_date)
    status = "✅" if success else "❌"
    print(f"[{i+1}/365] Ngày {target_date.strftime('%Y-%m-%d')}: {status}")
    time.sleep(0.1)

print("\n" + "="*30)
print(f"🎉 Hoàn thành! Tổng số ngày trong CSDL: {count_results()}")
oldest, newest = get_date_range()
print(f"📅 Dữ liệu từ {oldest} đến {newest}")
