import sqlite3
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import time

# --- CẤU HÌNH ---
DB_PATH = "database.db"  # Thay tên file CSDL của bạn (ví dụ: lottery.db)
NUM_DAYS = 365           # Số ngày cần cào lùi về quá khứ

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def init_db():
    """Khởi tạo bảng nếu chưa có (điều chỉnh schema cho đúng với DB của bạn)"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS lottery_results (
            date TEXT PRIMARY KEY,
            numbers TEXT
        )
    ''')
    conn.commit()
    conn.close()

def crawl_xsmb_date(date_str):
    """
    Cào kết quả XSMB theo ngày format 'DD-MM-YYYY' từ xoso.com.vn
    Nguồn dữ liệu tham khảo chính xác từ xoso.com.vn
    """
    url = f"https://xoso.com.vn/ket-qua-theo-ngay.html?date={date_str}"
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        if response.status_code != 200:
            return None
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Tìm bảng kết quả
        numbers = []
        # Lấy tất cả các ô chứa kết quả giải
        cells = soup.find_all('span', class_=['v-gdb', 'v-g1', 'v-g2', 'v-g3', 'v-g4', 'v-g5', 'v-g6', 'v-g7'])
        
        for cell in cells:
            txt = cell.get_text(strip=True)
            if txt.isdigit():
                # Lấy 2 số cuối (lô)
                numbers.append(txt[-2:])
                
        if len(numbers) >= 27:  # XSMB chuẩn có 27 giải
            return ",".join(numbers[:27])
        return None

    except Exception as e:
        print(f"❌ Lỗi khi cào ngày {date_str}: {e}")
        return None

def main():
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Tính ngày bắt đầu (hôm nay) và lùi lại 365 ngày
    today = datetime.now()
    saved_count = 0

    print(f"🚀 Bắt đầu cào dữ liệu XSMB trong {NUM_DAYS} ngày...")

    for i in range(NUM_DAYS):
        current_date = today - timedelta(days=i)
        date_str_db = current_date.strftime("%Y-%m-%d")    # Dùng lưu DB
        date_str_web = current_date.strftime("%d-%m-%Y")   # Dùng gọi URL

        # Kiểm tra xem ngày này đã có trong DB chưa
        cursor.execute("SELECT date FROM lottery_results WHERE date = ?", (date_str_db,))
        if cursor.fetchone():
            print(f"⏩ Ngày {date_str_db} đã có trong CSDL. Bỏ qua.")
            continue

        print(f"🔄 Đang cào ngày {date_str_web}...", end=" ")
        results = crawl_xsmb_date(date_str_web)

        if results:
            cursor.execute("INSERT OR REPLACE INTO lottery_results (date, numbers) VALUES (?, ?)", (date_str_db, results))
            conn.commit()
            saved_count += 1
            print("✅ Thành công!")
        else:
            print("⚠️ Không lấy được dữ liệu.")

        # Nghỉ 0.3s để tránh bị website chặn Request
        time.sleep(0.3)

    conn.close()
    print(f"\n🎉 Hoàn thành! Đã bổ sung thêm {saved_count} ngày vào CSDL.")

if __name__ == "__main__":
    main()
