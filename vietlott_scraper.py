import requests
import json
import os

DATA_FILE_655 = "vietlott_655.json"
DATA_FILE_645 = "vietlott_645.json"

# Nguồn dữ liệu Vietlott từ GitHub CDN
GITHUB_655_URLS = [
    "https://raw.githubusercontent.com/vietvudanh/vietlott-data/main/data/power655.jsonl",
    "https://raw.githubusercontent.com/fatesinger/vietlott/main/data/power655.json"
]

GITHUB_645_URLS = [
    "https://raw.githubusercontent.com/vietvudanh/vietlott-data/main/data/mega645.jsonl",
    "https://raw.githubusercontent.com/fatesinger/vietlott/main/data/mega645.json"
]

def fetch_vietlott_655_data(limit=300):
    return _fetch_multi_source(GITHUB_655_URLS, DATA_FILE_655, limit)

def fetch_vietlott_645_data(limit=300):
    return _fetch_multi_source(GITHUB_645_URLS, DATA_FILE_645, limit)

def _fetch_multi_source(urls, filename, limit):
    results = []

    for url in urls:
        try:
            res = requests.get(url, timeout=10)
            if res.status_code == 200:
                text_data = res.text.strip()
                
                # Trường hợp 1: File JSON Lines (.jsonl)
                if "\n" in text_data and not text_data.startswith("["):
                    for line in text_data.split('\n'):
                        if line.strip():
                            try:
                                item = json.loads(line)
                                parsed = _extract_item(item)
                                if parsed:
                                    results.append(parsed)
                            except Exception:
                                continue
                # Trường hợp 2: File mảng JSON chuẩn (.json)
                else:
                    data_list = json.loads(text_data)
                    if isinstance(data_list, list):
                        for item in data_list:
                            parsed = _extract_item(item)
                            if parsed:
                                results.append(parsed)

                if results:
                    break # Lấy thành công từ nguồn tốt nhất thì dừng loop
        except Exception as e:
            print(f"Lỗi fetch {url}: {e}")

    # Nếu fetch thất bại hoàn toàn, đọc cache từ đĩa local
    if not results and os.path.exists(filename):
        try:
            with open(filename, "r", encoding="utf-8") as f:
                results = json.load(f)
        except Exception:
            pass

    # Lọc trùng lặp ngày và sắp xếp từ CŨ đến MỚI
    if results:
        unique_map = {}
        for item in results:
            unique_map[item['date']] = item
            
        results = sorted(list(unique_map.values()), key=lambda x: x["date"])
        
        if limit and len(results) > limit:
            results = results[-limit:]

        try:
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    return results

def _extract_item(item):
    """ Bóc tách ngày và dãy số linh hoạt bất chấp cấu trúc key JSON """
    if not isinstance(item, dict):
        return None

    # Tìm field ngày
    date_raw = (
        item.get("date") or item.get("draw_date") or 
        item.get("run_date") or item.get("drawDate") or 
        item.get("periodDate") or ""
    )
    
    # Tìm field kết quả
    nums_raw = (
        item.get("result") or item.get("numbers") or 
        item.get("draw_result") or item.get("drawResult") or 
        item.get("winning_numbers") or []
    )

    if not date_raw or not nums_raw:
        return None

    # Định dạng ngày YYYY-MM-DD
    date_clean = str(date_raw).split("T")[0].replace("/", "-")
    if "/" in str(date_raw):
        parts = str(date_raw).split("/")
        if len(parts) == 3:
            date_clean = f"{parts[2]}-{int(parts[1]):02d}-{int(parts[0]):02d}"

    # Xử lý dãy số
    nums = []
    if isinstance(nums_raw, str):
        nums = [int(x) for x in nums_raw.replace("|", ",").split(",") if x.strip().isdigit()]
    elif isinstance(nums_raw, list):
        nums = [int(x) for x in nums_raw if str(x).isdigit()]

    if len(nums) >= 6:
        return {
            "date": date_clean,
            "result": sorted(nums[:6])
        }
    
    return None

fetch_and_update_vietlott_655 = fetch_vietlott_655_data

def get_dataset(game="655"):
    target_file = DATA_FILE_645 if str(game) == "645" else DATA_FILE_655
    fetch_fn = fetch_vietlott_645_data if str(game) == "645" else fetch_vietlott_655_data
    
    if os.path.exists(target_file):
        try:
            with open(target_file, "r", encoding="utf-8") as f:
                d = json.load(f)
                if d and len(d) > 0:
                    return d
        except Exception:
            pass
            
    return fetch_fn()