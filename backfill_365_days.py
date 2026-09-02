import sys
import time
from scraper import scrape_past_days
from database import count_results

if __name__ == "__main__":
    print("🚀 Bắt đầu tiến trình tải dữ liệu 365 ngày cho các giải Vietlott...", flush=True)
    
    # Mặc định lấy 365 ngày (có thể truyền số ngày từ tham số lệnh)
    days = 365
    if len(sys.argv) > 1:
        try:
            days = int(sys.argv[1])
        except ValueError:
            print("⚠️ Tham số số ngày không hợp lệ. Sử dụng mặc định 365 ngày.", flush=True)

    total_records = scrape_past_days(days=days)
    
    print("--------------------------------------------------", flush=True)
    print(f"✅ HOÀN THÀNH! Tổng số bản ghi hiện có trong CSDL: {total_records}", flush=True)
