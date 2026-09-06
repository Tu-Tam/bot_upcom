import requests
import json
import os

DATA_FILE_655 = "vietlott_655.json"
DATA_FILE_645 = "vietlott_645.json"

# Endpoint dữ liệu chuẩn cho cả 6/55 và 6/45
URL_655 = "https://raw.githubusercontent.com/vietvudanh/vietlott-data/main/data/power655.jsonl"
URL_645 = "https://raw.githubusercontent.com/vietvudanh/vietlott-data/main/data/mega645.jsonl"

def fetch_vietlott_655_data(limit=300):
    return _parse_and_save(URL_655, DATA_FILE_655, limit, default_year="2026")

def fetch_vietlott_645_data(limit=300):
    return _parse_and_save(URL_645, DATA_FILE_645, limit, default_year="2026")

def _parse_and_save(url, filename, limit, default_year="2026"):
    results = []

    try:
        res = requests.get(url, timeout=12)
        if res.status_code == 200:
            lines = res.text.strip().split('\n')
            for line in lines:
                if not line.strip():
                    continue
                try:
                    item = json.loads(line)
                    date_clean, nums = _extract_data(item, default_year)
                    if date_clean and len(nums) >= 6:
                        results.append({
                            "date": date_clean,
                            "result": sorted(nums[:6])
                        })
                except Exception:
                    continue
    except Exception as e:
        print(f"Lỗi fetch {url}: {e}")

    # Nếu tải lỗi, fallback về đọc file local
    if not results and os.path.exists(filename):
        try:
            with open(filename, "r", encoding="utf-8") as f:
                results = json.load(f)
        except Exception:
            pass

    # Xử lý lọc trùng ngày và lưu lại file
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

def _extract_data(item, default_year):
    # Lấy ngày
    date_raw = item.get("date") or item.get("draw_date") or item.get("run_date") or item.get("drawDate") or ""
    
    # Lấy chuỗi số
    nums_raw = item.get("result") or item.get("numbers") or item.get("draw_result") or item.get("drawResult") or []

    if not date_raw or not nums_raw:
        return None, []

    date_str = str(date_raw).split("T")[0].replace("/", "-")
    
    # Chuẩn hóa YYYY-MM-DD
    parts = date_str.split("-")
    if len(parts) == 3:
        if len(parts[0]) == 4:
            date_clean = f"{parts[0]}-{int(parts[1]):02d}-{int(parts[2]):02d}"
        else:
            date_clean = f"{parts[2]}-{int(parts[1]):02d}-{int(parts[0]):02d}"
    elif len(parts) == 2:
        date_clean = f"{default_year}-{int(parts[0]):02d}-{int(parts[1]):02d}"
    else:
        date_clean = date_str

    # Chuẩn hóa Dãy số
    nums = []
    if isinstance(nums_raw, str):
        nums = [int(x) for x in nums_raw.replace("|", ",").split(",") if x.strip().isdigit()]
    elif isinstance(nums_raw, list):
        nums = [int(x) for x in nums_raw if str(x).isdigit()]

    return date_clean, nums

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