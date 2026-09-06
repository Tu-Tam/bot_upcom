import requests
import json
import os

DATA_FILE_655 = "vietlott_655.json"
DATA_FILE_645 = "vietlott_645.json"

# Kho dữ liệu Vietlott tự động cập nhật liên tục (Bypass 100% Render IP Block)
GITHUB_RAW_655 = "https://raw.githubusercontent.com/vietvudanh/vietlott-data/main/data/power655.jsonl"
GITHUB_RAW_645 = "https://raw.githubusercontent.com/vietvudanh/vietlott-data/main/data/mega645.jsonl"

def fetch_vietlott_655_data(limit=300):
    return _fetch_from_github_cdn(GITHUB_RAW_655, DATA_FILE_655, limit)

def fetch_vietlott_645_data(limit=300):
    return _fetch_from_github_cdn(GITHUB_RAW_645, DATA_FILE_645, limit)

def _fetch_from_github_cdn(github_url, filename, limit):
    results = []

    # 1. Tải CSDL trực tiếp từ CDN GitHub
    try:
        res = requests.get(github_url, timeout=10)
        if res.status_code == 200:
            lines = res.text.strip().split('\n')
            for line in lines:
                if not line.strip():
                    continue
                try:
                    item = json.loads(line)
                    # Parse ngày và kết quả từ dữ liệu GitHub
                    date_raw = item.get("date") or item.get("draw_date") or item.get("run_date", "")
                    nums = item.get("result") or item.get("numbers") or item.get("draw_result", [])
                    
                    if date_raw and nums:
                        date_clean = str(date_raw).split("T")[0].replace("/", "-")
                        if isinstance(nums, str):
                            nums = [int(x) for x in nums.replace("|", ",").split(",") if x.strip().isdigit()]
                        
                        if len(nums) >= 6:
                            results.append({
                                "date": date_clean,
                                "result": sorted([int(n) for n in nums[:6]])
                            })
                except Exception:
                    continue
    except Exception as e:
        print(f"Lỗi tải dữ liệu GitHub: {e}")

    # 2. Nếu lỗi mạng, đọc file lưu trên đĩa nội bộ Render
    if not results and os.path.exists(filename):
        try:
            with open(filename, "r", encoding="utf-8") as f:
                results = json.load(f)
        except Exception:
            pass

    # 3. Lọc trùng lặp và sắp xếp lại theo thời gian (Từ Cũ đến Mới)
    if results:
        unique_results = {item['date']: item for item in results}.values()
        results = sorted(list(unique_results), key=lambda x: x["date"])
        
        # Chỉ giữ lại đúng số kỳ giới hạn gần nhất nếu cần (hoặc lấy tất cả)
        if limit and len(results) > limit:
            results = results[-limit:]

        # Lưu vào cache file
        try:
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    return results

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