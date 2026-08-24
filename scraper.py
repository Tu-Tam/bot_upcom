import re
import time
import requests

from bs4 import BeautifulSoup
from datetime import datetime
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from database import save_result


# ============================================================
# CONFIG
# ============================================================

PRIMARY_URL = "https://xoso.com.vn/xsmb-100-ngay.html"

FALLBACK_URLS = [
    "https://xoso.com.vn/xsmb-30-ngay.html",
    "https://xsmb.com.vn/xsmb-sxmb-ket-qua-xo-so-mien-bac-truc-tiep",
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,"
        "application/xml;q=0.9,image/avif,image/webp,"
        "image/apng,*/*;q=0.8"
    ),
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}


REQUEST_TIMEOUT = 30
MAX_RETRIES = 3


# ============================================================
# HTTP SESSION
# ============================================================

def create_session():
    session = requests.Session()
    retry = Retry(
        total=MAX_RETRIES,
        connect=MAX_RETRIES,
        read=MAX_RETRIES,
        backoff_factor=1.5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session.headers.update(HEADERS)
    return session


# ============================================================
# FETCH PAGE
# ============================================================

def fetch_page(url):
    print("\n" + "="*60)
    print("[SCRAPER] FETCH")
    print("="*60)
    print(f"[SCRAPER] URL: {url}")

    session = create_session()
    try:
        response = session.get(url, timeout=REQUEST_TIMEOUT, allow_redirects=True)
        print(f"[SCRAPER] Status: {response.status_code} | Final URL: {response.url}")
        print(f"Size: {len(response.content)} bytes | Type: {response.headers.get('Content-Type')}")

        if response.status_code != 200:
            raise RuntimeError(f"HTTP {response.status_code} từ {url}")
        html = response.text
        if not html:
            raise RuntimeError("HTML rỗng!")

        low_html = html.lower()
        anti_bot = ["captcha", "cloudflare", "cf-chl", "checking your browser",
                    "verify you are human", "access denied", "forbidden", "bot detection"]
        detected = [w for w in anti_bot if w in low_html]
        if detected:
            print(f"⚠️ Anti-bot phát hiện: {detected}")

        print("✅ Có XSMB:", "xsmb" in low_html)
        print("✅ Có ĐB:", "đb" in low_html)
        return html
    finally:
        session.close()


# ============================================================
# NORMALIZE & PARSE TOÀN DIỆN
# ============================================================

def normalize_text(text):
    text = text.replace("\xa0", " ")
    text = text.replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n+", "\n", text)
    return text.strip()


def parse_html_table(html):
    soup = BeautifulSoup(html, "html.parser")
    results = []
    for script in soup(["script", "style", "noscript", "svg"]):
        script.decompose()

    blocks = soup.find_all("table")
    for tbl in blocks:
        text_block = tbl.get_text("\n")
        date_m = re.search(r"(\d{1,2}/\d{1,2}/\d{4})", text_block)
        if not date_m:
            continue
        date_str = date_m.group(1)
        try:
            dt = datetime.strptime(date_str, "%d/%m/%Y")
            date_id = dt.strftime("%Y-%m-%d")
            dow = dt.weekday()
        except ValueError:
            continue

        rec = {
            "date": date_id,
            "weekday": dow,
            "special": None,
            "g1": [], "g2": [], "g3": [], "g4": [], "g5": [], "g6": [], "g7": [],
            "loto_by_head": {}
        }

        rows = tbl.find_all("tr")
        for tr in rows:
            cells = [normalize_text(td.get_text(strip=True)) for td in tr.find_all(["td", "th"])]
            if len(cells) < 2:
                continue
            head = cells[0].upper().strip(":.")
            vals_txt = " ".join(cells[1:])
            nums = re.findall(r"\b\d{2,5}\b", vals_txt)

            if head in ("ĐB", "ĐẶC BIỆT") and nums and len(nums[0]) == 5:
                rec["special"] = nums[0]
            elif head == "1": rec["g1"].extend(nums)
            elif head == "2": rec["g2"].extend(nums)
            elif head == "3": rec["g3"].extend(nums)
            elif head == "4": rec["g4"].extend(nums)
            elif head == "5": rec["g5"].extend(nums)
            elif head == "6": rec["g6"].extend(nums)
            elif head == "7": rec["g7"].extend(nums)
            elif "ĐẦU" in head or "LOTO" in head or len(cells) == 2 and re.fullmatch(r"\d", cells[0]):
                d_head = re.match(r".*?(\d)\D*$", head) or re.match(r"^(\d)$", cells[0])
                if d_head:
                    d = d_head.group(1)
                    tails = re.findall(r"\b\d{2}\b", vals_txt)
                    rec["loto_by_head"][d] = tails

        if rec["special"]:
            results.append(rec)
            print(f"✅ Phân tích thành: {date_id} | ĐB={rec['special']}")
    return results


# ============================================================
# CHẠY CHÍNH
# ============================================================

def fetch_and_parse_all():
    urls = [PRIMARY_URL] + FALLBACK_URLS
    for url in urls:
        try:
            html = fetch_page(url)
            data = parse_html_table(html)
            if data:
                return data
        except Exception as e:
            print(f"❌ Lỗi nguồn {url}: {e}")
    return []


if __name__ == "__main__":
    from database import init_db
    init_db()
    print("🚀 Bắt đầu quét dữ liệu...")
    all_data = fetch_and_parse_all()
    print(f"📦 Tổng số ngày: {len(all_data)}")
    for item in all_data:
        save_result(item)
    print("✅ Hoàn tất lưu CSDL!")
