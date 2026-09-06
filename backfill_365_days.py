import sys
import time
import json
from scraper import scrape_past_days
from database import count_results, get_all_results_by_game  # Giả định database có hàm lấy danh sách kết quả

DATA_FILE_655 = "vietlott_655.json"

def export_database_to_json():
    """
    Trích xuất dữ liệu Power 6/55 từ CSDL ra file vietlott_655.json 
    để backtest.py và analytics.py đọc trực tiếp.
    """
    try:
        # Nếu database.py có hàm lấy dữ liệu theo game
        raw_data = get_all_results_by_game("655")
        
        formatted_data = []
        for row in raw_data:
            # Giả định cấu trúc row: {"draw_date": "YYYY-MM-DD", "result": [1, 2, 3, 4, 5, 6]}
            date_str = row.get("draw_date") or row.get("date")
            results = row.get("result") or row.get("numbers")
            
            if date_str and results and len(results) >= 6:
                formatted_data.append({
                    "date": str(date_str),
                    "result": sorted([int(x) for x in results[:6]])
                })
                
        # Sắp xếp theo ngày tăng dần
        formatted_data.sort(key=lambda x: x["date"])

        if formatted_data:
            with open(DATA_FILE_655, "w", encoding="utf-8") as f:
                json.dump(formatted_data, f, ensure_ascii=False, indent=2)
            print(f"📦 Đã xuất {len(formatted_data)} kỳ quay Power 6/55 ra file {DATA_FILE_655}", flush=True)
            
    except Exception as e:
        print(f"⚠️ Không thể tự động xuất dữ liệu ra JSON: {e}", flush=True)

if __name__ == "__main__":
    print("🚀 Bắt đầu tiến trình tải dữ liệu lịch sử Vietlott...", flush=True)
    
    # Mặc định lấy 365 ngày (có thể truyền số ngày từ tham số dòng lệnh)
    days = 365
    if len(sys.argv) > 1:
        try:
            days = int(sys.argv[1])
        except ValueError:
            print("⚠️ Tham số số ngày không hợp lệ. Sử dụng mặc định 365 ngày.", flush=True)

    # 1. Thực hiện cào dữ liệu nạp vào CSDL
    total_records = scrape_past_days(days=days)
    
    # 2. Đồng bộ dữ liệu vừa cào ra file vietlott_655.json
    export_database_to_json()
    
    print("--------------------------------------------------", flush=True)
    print(f"✅ HOÀN THÀNH! Tổng số bản ghi hiện có trong CSDL: {total_records}", flush=True)