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

# Số lần thử request
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
        status_forcelist=[
            429,
            500,
            502,
            503,
            504,
        ],
        allowed_methods=[
            "GET",
        ],
        raise_on_status=False,
    )

    adapter = HTTPAdapter(
        max_retries=retry
    )

    session.mount(
        "http://",
        adapter
    )

    session.mount(
        "https://",
        adapter
    )

    session.headers.update(
        HEADERS
    )

    return session


# ============================================================
# FETCH PAGE
# ============================================================

def fetch_page(url):

    print()
    print("=" * 60)
    print("[SCRAPER] FETCH")
    print("=" * 60)

    print(
        f"[SCRAPER] URL: {url}"
    )

    session = create_session()

    try:

        response = session.get(
            url,
            timeout=REQUEST_TIMEOUT,
            allow_redirects=True,
        )

        print(
            f"[SCRAPER] HTTP status: "
            f"{response.status_code}"
        )

        print(
            f"[SCRAPER] Final URL: "
            f"{response.url}"
        )

        print(
            f"[SCRAPER] Content-Type: "
            f"{response.headers.get('Content-Type')}"
        )

        print(
            f"[SCRAPER] Content-Length: "
            f"{len(response.content)} bytes"
        )

        if response.status_code != 200:

            raise RuntimeError(
                f"HTTP {response.status_code} "
                f"từ {url}"
            )

        html = response.text

        if not html:

            raise RuntimeError(
                "Website trả về HTML rỗng."
            )

        lower_html = html.lower()

        # ----------------------------------------------------
        # Anti-bot detection
        # ----------------------------------------------------

        anti_bot_keywords = [
            "captcha",
            "cloudflare",
            "cf-chl",
            "checking your browser",
            "verify you are human",
            "access denied",
            "forbidden",
            "bot detection",
        ]

        detected = [
            word
            for word in anti_bot_keywords
            if word in lower_html
        ]

        if detected:

            print(
                "[SCRAPER] ⚠️ Có dấu hiệu "
                f"anti-bot: {detected}"
            )

        # ----------------------------------------------------
        # Basic content check
        # ----------------------------------------------------

        print(
            "[SCRAPER] Có 'XSMB':",
            "xsmb" in lower_html
        )

        print(
            "[SCRAPER] Có 'ĐB':",
            "đb" in lower_html
        )

        print(
            "[SCRAPER] Có ngày dd/mm/yyyy:",
            bool(
                re.search(
                    r"\b\d{1,2}/\d{1,2}/\d{4}\b",
                    html
                )
            )
        )

        return html

    finally:

        session.close()


# ============================================================
# NORMALIZE TEXT
# ============================================================

def normalize_text(text):

    text = text.replace(
        "\xa0",
        " "
    )

    text = text.replace(
        "\r",
        "\n"
    )

    # Chuẩn hóa khoảng trắng ngang
    text = re.sub(
        r"[ \t]+",
        " ",
        text
    )

    # Chuẩn hóa nhiều dòng trống
    text = re.sub(
        r"\n+",
        "\n",
        text
    )

    return text.strip()


# ============================================================
# EXTRACT DATE
# ============================================================

def extract_date(text):

    patterns = [
        # 24/08/2026
        r"\b(\d{1,2}/\d{1,2}/\d{4})\b",

        # XSMB 24/08/2026
        r"XSMB[^\d]{0,50}"
        r"(\d{1,2}/\d{1,2}/\d{4})",
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            flags=re.IGNORECASE
        )

        if not match:
            continue

        date_text = match.group(1)

        try:

            dt = datetime.strptime(
                date_text,
                "%d/%m/%Y"
            )

            return dt.strftime(
                "%Y-%m-%d"
            )

        except ValueError:

            continue

    return None


# ============================================================
# EXTRACT SPECIAL FROM BLOCK
# ============================================================

def extract_special(block):

    # --------------------------------------------------------
    # Cách 1:
    #
    # ĐB | 37938
    #
    # hoặc:
    #
    # ĐB  | 37938
    # --------------------------------------------------------

    patterns = [

        r"ĐB\s*\|\s*(\d{5})",

        r"ĐB\s*[:\-]\s*(\d{5})",

        r"Đặc biệt\s*\|\s*(\d{5})",

        r"Đặc biệt\s*[:\-]\s*(\d{5})",
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            block,
            flags=re.IGNORECASE
        )

        if match:

            special = match.group(1)

            if len(special) == 5:

                return special

    # --------------------------------------------------------
    # Cách 2:
    #
    # Một số HTML chuyển bảng thành:
    #
    # ĐB
    # 37938
    # --------------------------------------------------------

    lines = [
        line.strip()
        for line in block.splitlines()
        if line.strip()
    ]

    for i, line in enumerate(lines):

        clean = line.lower()

        if clean in (
            "đb",
            "đ.b",
            "đặc biệt",
        ):

            if i + 1 < len(lines):

                candidate = (
                    lines[i + 1]
                )

                match = re.search(
                    r"\b(\d{5})\b",
                    candidate
                )

                if match:

                    return match.group(1)

    return None


# ============================================================
# PARSE USING TEXT BLOCKS
# ============================================================

def parse_by_text_blocks(html):

    print()
    print("=" * 60)
    print("[SCRAPER] PARSE TEXT BLOCKS")
    print("=" * 60)

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    # Loại bỏ thành phần không cần thiết
    for tag in soup([
        "script",
        "style",
        "noscript",
        "svg",
    ]):

        tag.decompose()

    text = soup.get_text(
        "\n"
    )

    text = normalize_text(
        text
    )

    print(
        f"[SCRAPER] Text length: "
        f"{len(text)}"
    )

    # --------------------------------------------------------
    # Tìm tất cả vị trí ngày
    # --------------------------------------------------------

    date_pattern = re.compile(
        r"\b\d{1,2}/\d{1,2}/\d{4}\b"
    )

    date_matches = list(
        date_pattern.finditer(text)
    )

    print(
        f"[SCRAPER] Tìm thấy "
        f"{len(date_matches)} ngày "
        f"trong HTML."
    )

    results = []

    for index, match in enumerate(
        date_matches
    ):

        date_text = match.group(0)

        try:

            dt = datetime.strptime(
                date_text,
                "%d/%m/%Y"
            )

        except ValueError:

            continue

        date = dt.strftime(
            "%Y-%m-%d"
        )

        # ----------------------------------------------------
        # Chỉ lấy vùng xung quanh ngày
        # ----------------------------------------------------

        start = match.start()

        if index + 1 < len(
            date_matches
        ):

            end = date_matches[
                index + 1
            ].start()

        else:

            end = min(
                len(text),
                start + 2500
            )

        block = text[
            max(0, start - 300):
            end
        ]

        # ----------------------------------------------------
        # Phải có XSMB gần ngày
        # ----------------------------------------------------

        if "XSMB" not in block.upper():

            continue

        special = extract_special(
            block
        )

        if not special:

            continue

        results.append({
            "date": date,
            "special": special,
        })

        print(
            f"[SCRAPER] FOUND: "
            f"{date} -> {special}"
        )

    return results


# ============================================================
# PARSE HTML TABLES
# ============================================================

def parse_by_tables(html):

    print()
    print("=" * 60)
    print("[SCRAPER] PARSE TABLES")
    print("=" * 60)

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    results = []

    tables = soup.find_all(
        "table"
    )

    print(
        f"[SCRAPER] Số table: "
        f"{len(tables)}"
    )

    for table in tables:

        table_text = normalize_text(
            table.get_text(
                "\n"
            )
        )

        # Phải có ĐB
        if not re.search(
            r"\bĐB\b",
            table_text,
            re.IGNORECASE
        ):

            continue

        # ----------------------------------------------------
        # Tìm special
        # ----------------------------------------------------

        special_match = re.search(
            r"\bĐB\b\s*\|?\s*"
            r"(\d{5})",
            table_text,
            re.IGNORECASE
        )

        if not special_match:

            # HTML table có thể chuyển thành:
            # ĐB \n 37938

            special_match = re.search(
                r"\bĐB\b.*?"
                r"\b(\d{5})\b",
                table_text,
                re.IGNORECASE |
                re.DOTALL
            )

        if not special_match:

            continue

        special = (
            special_match.group(1)
        )

        # ----------------------------------------------------
        # Tìm ngày trong parent
        # ----------------------------------------------------

        container = table.parent

        surrounding_text = ""

        # Đi ngược lên tối đa vài cấp
        for _ in range(5):

            if not container:
                break

            surrounding_text += "\n" + (
                container.get_text(
                    " ",
                    strip=True
                )
            )

            container = container.parent

        date = extract_date(
            surrounding_text
        )

        if not date:

            # Thử text phía trước table
            previous = table.find_previous(
                string=re.compile(
                    r"\d{1,2}/\d{1,2}/\d{4}"
                )
            )

            if previous:

                date = extract_date(
                    str(previous)
                )

        if not date:

            continue

        item = {
            "date": date,
            "special": special,
        }

        results.append(
            item
        )

        print(
            f"[SCRAPER] TABLE FOUND: "
            f"{date} -> {special}"
        )

    return results


# ============================================================
# MERGE RESULTS
# ============================================================

def merge_results(*result_lists):

    unique = {}

    for result_list in result_lists:

        for item in result_list:

            date = item.get(
                "date"
            )

            special = item.get(
                "special"
            )

            if not date or not special:
                continue

            if not re.fullmatch(
                r"\d{5}",
                str(special)
            ):
                continue

            unique[date] = str(
                special
            ).zfill(5)

    results = [
        {
            "date": date,
            "special": special,
        }
        for date, special
        in unique.items()
    ]

    results.sort(
        key=lambda x: x["date"],
        reverse=True
    )

    return results


# ============================================================
# PARSE RESULTS
# ============================================================

def parse_results(html):

    print()
    print("=" * 60)
    print("[SCRAPER] BẮT ĐẦU PARSE")
    print("=" * 60)

    # Parser 1
    text_results = parse_by_text_blocks(
        html
    )

    # Parser 2
    table_results = parse_by_tables(
        html
    )

    results = merge_results(
        text_results,
        table_results
    )

    print()
    print(
        f"[SCRAPER] Tổng kết quả parse: "
        f"{len(results)}"
    )

    if results:

        print(
            "[SCRAPER] Mới nhất:"
        )

        for item in results[:10]:

            print(
                f"  "
                f"{item['date']} "
                f"-> "
                f"{item['special']}"
            )

    return results


# ============================================================
# VALIDATE RESULTS
# ============================================================

def validate_results(results):

    valid = []

    for item in results:

        date = item.get(
            "date"
        )

        special = str(
            item.get(
                "special",
                ""
            )
        ).strip()

        # ----------------------------------------------------
        # Validate date
        # ----------------------------------------------------

        try:

            datetime.strptime(
                date,
                "%Y-%m-%d"
            )

        except (
            ValueError,
            TypeError
        ):

            print(
                "[SCRAPER] Bỏ ngày lỗi:",
                date
            )

            continue

        # ----------------------------------------------------
        # Validate special
        # ----------------------------------------------------

        if not re.fullmatch(
            r"\d{5}",
            special
        ):

            print(
                "[SCRAPER] Bỏ ĐB lỗi:",
                special
            )

            continue

        valid.append({
            "date": date,
            "special": special,
        })

    return valid


# ============================================================
# UPDATE DATABASE
# ============================================================

def update_database():

    print()
    print("=" * 60)
    print("[SCRAPER] BẮT ĐẦU UPDATE")
    print("=" * 60)

    all_results = []

    urls = [
        PRIMARY_URL
    ] + FALLBACK_URLS

    last_error = None

    # --------------------------------------------------------
    # Try sources
    # --------------------------------------------------------

    for index, url in enumerate(
        urls,
        start=1
    ):

        print()
        print(
            f"[SCRAPER] Source "
            f"{index}/{len(urls)}"
        )

        try:

            html = fetch_page(
                url
            )

            results = parse_results(
                html
            )

            results = validate_results(
                results
            )

            print(
                f"[SCRAPER] Source trả về "
                f"{len(results)} kết quả."
            )

            if results:

                all_results = merge_results(
                    all_results,
                    results
                )

                # Nếu nguồn chính đã có dữ liệu
                # thì không cần tiếp tục fallback.
                if len(all_results) >= 10:

                    break

        except Exception as e:

            last_error = e

            print(
                f"[SCRAPER] ERROR "
                f"{url}: {repr(e)}"
            )

            continue

        # Tránh request liên tục
        time.sleep(
            1
        )

    # --------------------------------------------------------
    # No result
    # --------------------------------------------------------

    if not all_results:

        raise RuntimeError(
            "Scraper không lấy được kết quả XSMB "
            "từ các nguồn dữ liệu.\n"
            f"Lỗi cuối: {last_error}"
        )

    # --------------------------------------------------------
    # Save database
    # --------------------------------------------------------

    print()
    print(
        "=" * 60
    )

    print(
        f"[SCRAPER] Chuẩn bị lưu "
        f"{len(all_results)} kết quả."
    )

    count = 0

    for item in all_results:

        try:

            save_result(
                item["date"],
                item["special"]
            )

            count += 1

        except Exception as e:

            print(
                f"[SCRAPER] Không lưu được "
                f"{item['date']}: "
                f"{repr(e)}"
            )

    print(
        f"[SCRAPER] Đã lưu "
        f"{count} kết quả."
    )

    print(
        "=" * 60
    )

    print(
        "[SCRAPER] UPDATE HOÀN TẤT"
    )

    print(
        "=" * 60
    )

    return count


# ============================================================
# DIRECT TEST
# ============================================================

if __name__ == "__main__":

    try:

        count = update_database()

        print()
        print(
            f"Đã cập nhật {count} kết quả."
        )

    except Exception as e:

        print()
        print(
            "SCRAPER ERROR:"
        )

        print(
            repr(e)
        )

        raise
