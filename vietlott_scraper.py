import json
import os
import copy
import requests
from bs4 import BeautifulSoup
from datetime import datetime

JSON_FILE = "vietlott_655.json"
DATASET = []

def load_data_from_json():
    """Đọc dữ liệu lịch sử từ file vietlott_655.json."""
    if os.path.exists(JSON_FILE):
        try:
            with open(JSON_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                print(f"📁 Đã nạp {len(data)} kỳ quay từ {JSON_FILE}", flush=True)
                return data
        except Exception as e:
            print(f"⚠️ Lỗi đọc file JSON: {e}", flush=True)
    return []

def save_data_to_json(data):
    """Ghi dữ liệu mới vào file vietlott_655.json."""
    try:
        with open(JSON_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"💾 Đã lưu dữ liệu mới vào {JSON_FILE}", flush=True)
    except Exception as e:
        print(f"⚠️ Không thể ghi file JSON: {e}", flush=True)

def fetch_vietlott_655_data():
    """Cào dữ liệu mới từ Vietlott và hợp nhất với file JSON local."""
    global DATASET
    # 1. Nạp dữ liệu hiện có từ file JSON
    local_data = load_data_from_json()
    existing_dates = {item["date"] for item in local_data}
    
    # 2. Cào dữ liệu mới từ web Vietlott
    url = "https://vietlott.vn/vi/trung-thuong/ket-qua-trung-thuong/655"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
    }
    
    new_results = []
    try:
        res = requests.get(url, headers=headers, timeout=8)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            rows = soup.select('table.table-hover tbody tr')
            for row in rows:
                cols = row.find_all('td')
                if len(cols) >= 2:
                    date_raw = cols[0].text.strip()
                    nums_raw = cols[1].find_all('span', class_='ball')
                    if len(nums_raw) >= 6:
                        date_str = datetime.strptime(date_raw, "%d/%m/%Y").strftime("%Y-%m-%d")
                        nums = [int(n.text.strip()) for n in nums_raw[:6]]
                        
                        # Chỉ thêm nếu kỳ này chưa có trong file JSON
                        if date_str not in existing_dates:
                            new_results.append({
                                "date": date_str, 
                                "game": "655", 
                                "result": sorted(nums)
                            })
    except Exception as e:
        print(f"⚠️ Lỗi cào web (Dùng dữ liệu JSON hiện có): {e}", flush=True)

    # 3. Tổng hợp và lưu lại nếu có kỳ mới
    if new_results:
        local_data.extend(new_results)
        save_data_to_json(local_data)

    # Đảm bảo DATASET toàn cục luôn được sắp xếp TĂNG DẦN theo ngày (CŨ -> MỚI)
    DATASET = sorted(local_data, key=lambda x: x["date"])
    return len(DATASET)

def get_dataset():
    """
    Trả về BẢN SAO ĐỘC LẬP (Deep Copy) của DATASET đã được sắp xếp từ CŨ -> MỚI.
    Đảm bảo việc lọc/sắp xếp ở bên ngoài không làm hỏng dữ liệu gốc trong RAM.
    """
    global DATASET
    if not DATASET:
        fetch_vietlott_655_data()
    
    # Luôn sắp xếp chuẩn từ CŨ -> MỚI và trả về bản sao độc lập hoàn toàn
    sorted_data = sorted(DATASET, key=lambda x: x["date"])
    return copy.deepcopy(sorted_data)