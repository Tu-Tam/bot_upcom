import re
import time
import requests

from bs4 import BeautifulSoup
from datetime import datetime

from database import save_result


# ============================================================
# CONFIG
# ============================================================

URL = "https://xsmb.com.vn/so-ket-qua-xsmb-100-ngay"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,"
        "application/xml;q=0.9,image/avif,image/webp,"
        "image/apng,*/*;q=0.8"
    ),
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
    "Connection": "keep-alive",
}


REQUEST_TIMEOUT = 30
MAX_RETRIES = 3

# Trang này được yêu cầu là 100 ngày.
MAX_RESULTS = 100


# ============================================================
# SESSION
# ============================================================

session = requests.Session()
session.headers.update(HEADERS)


# ============================================================
# FETCH PAGE
# ============================================================

def fetch_page():
    """
    Tải HTML từ website.

    Có retry để tránh lỗi mạng tạm thời.
    Nếu sau tất cả lần thử vẫn lỗi -> raise exception.
    """

    last_error = None

    for attempt in range(1, MAX_RETRIES + 1):

        try:

            print(
                f"[SCRAPER] Đang tải dữ liệu "
                f"(lần {attempt}/{MAX_RETRIES})..."
            )

            response = session.get(
                URL,
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
                f"[SCRAPER] Content length: "
                f"{len(response.text)} bytes"
            )

            response.raise_for_status()

            if not response.text.strip():

                raise RuntimeError(
                    "Website trả về HTML rỗng."
                )

            return response.text

        except requests.RequestException as e:

            last_error = e

            print(
                f"[SCRAPER] Request lỗi: {repr(e)}"
            )

            if attempt < MAX_RETRIES:

                time.sleep(2)

    raise RuntimeError(
        f"Không thể tải dữ liệu từ website: "
        f"{last_error}"
    )


# ============================================================
# DATE PARSER
# ============================================================

def parse_date(date_text):
    """
    Chuyển ngày DD/MM/YYYY thành YYYY-MM-DD.
    """

    if not date_text:
        return None

    date_text = date_text.strip()

    match = re.search(
        r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b",
        date_text
    )

    if not match:
        return None

    try:

        day = int(match.group(1))
        month = int(match.group(2))
        year = int(match.group(3))

        dt = datetime(
            year,
            month,
            day
        )

        return dt.strftime("%Y-%m-%d")

    except ValueError:

        return None


# ============================================================
# NORMALIZE NUMBER
# ============================================================

def normalize_special(number):
    """
    Chuẩn hóa giải đặc biệt thành đúng 5 chữ số.

    Ví dụ:
        12345 -> 12345
        "12345" -> 12345
        "01234" -> 01234
    """

    if number is None:
        return None

    number = str(number).strip()

    # Chỉ giữ chữ số
    number = re.sub(
        r"\D",
        "",
        number
    )

    if not number:
        return None

    # Giải ĐB phải là 5 chữ số.
    if len(number) != 5:
        return None

    return number


# ============================================================
# FIND SPECIAL PRIZE
# ============================================================

def find_special_number(text):
    """
    Tìm giải đặc biệt trong một block text.

    Không phụ thuộc tuyệt đối vào:
        ĐB | 12345

    Hỗ trợ nhiều dạng thường gặp:
        ĐB | 12345
        ĐB 12345
        ĐB: 12345
        Đặc biệt 12345
        Đặc Biệt: 12345
    """

    if not text:
        return None

    # Chuẩn hóa khoảng trắng
    normalized = re.sub(
        r"[ \t]+",
        " ",
        text
    )

    # --------------------------------------------------------
    # Strategy 1
    # ĐB | 12345
    # --------------------------------------------------------

    patterns = [

        r"(?:ĐB|Đặc\s*biệt)"
        r"\s*[\|\:\-]?\s*"
        r"(\d{5})",

        # Trường hợp ĐB xuống dòng rồi số
        r"(?:ĐB|Đặc\s*biệt)"
        r"\s*\n+\s*"
        r"(\d{5})",

        # Trường hợp có nhiều whitespace / separator
        r"(?:ĐB|Đặc\s*biệt)"
        r"[\s\|\:\-]+"
        r"(\d{5})",
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            normalized,
            flags=re.IGNORECASE
        )

        if match:

            number = normalize_special(
                match.group(1)
            )

            if number:
                return number

    return None


# ============================================================
# EXTRACT BLOCKS
# ============================================================

def extract_candidate_blocks(soup):
    """
    Tìm các block HTML có khả năng chứa kết quả của từng ngày.

    Ưu tiên:
        table
        tr
        div
        section
        article

    Nếu không tìm được block phù hợp,
    fallback về toàn bộ text.
    """

    blocks = []

    # --------------------------------------------------------
    # Strategy 1: TABLE
    # --------------------------------------------------------

    tables = soup.find_all("table")

    for table in tables:

        text = table.get_text(
            "\n",
            strip=True
        )

        if not text:
            continue

        if re.search(
            r"\b\d{1,2}/\d{1,2}/\d{4}\b",
            text
        ) and re.search(
            r"(?:ĐB|Đặc\s*biệt)",
            text,
            flags=re.IGNORECASE
        ):

            blocks.append(
                table
            )

    if blocks:
        return blocks

    # --------------------------------------------------------
    # Strategy 2: TR
    # --------------------------------------------------------

    rows = soup.find_all("tr")

    for row in rows:

        text = row.get_text(
            "\n",
            strip=True
        )

        if not text:
            continue

        if re.search(
            r"\b\d{1,2}/\d{1,2}/\d{4}\b",
            text
        ) and re.search(
            r"(?:ĐB|Đặc\s*biệt)",
            text,
            flags=re.IGNORECASE
        ):

            blocks.append(
                row
            )

    if blocks:
        return blocks

    # --------------------------------------------------------
    # Strategy 3: DIV / SECTION / ARTICLE
    # --------------------------------------------------------

    for tag_name in (
        "article",
        "section",
        "div",
    ):

        elements = soup.find_all(
            tag_name
        )

        for element in elements:

            text = element.get_text(
                "\n",
                strip=True
            )

            if not text:
                continue

            if not re.search(
                r"\b\d{1,2}/\d{1,2}/\d{4}\b",
                text
            ):
                continue

            if not re.search(
                r"(?:ĐB|Đặc\s*biệt)",
                text,
                flags=re.IGNORECASE
            ):
                continue

            # Không lấy block quá lớn.
            # Block của một ngày thường không cần
            # hàng chục nghìn ký tự.
            if len(text) <= 10000:

                blocks.append(
                    element
                )

        if blocks:
            return blocks

    return []


# ============================================================
# PARSE BLOCK
# ============================================================

def parse_block_text(text):
    """
    Parse một block chứa kết quả.
    """

    if not text:
        return None

    # Chuẩn hóa line
    lines = []

    for line in text.splitlines():

        line = line.strip()

        if line:
            lines.append(line)

    clean_text = "\n".join(
        lines
    )

    # --------------------------------------------------------
    # Tìm ngày
    # --------------------------------------------------------

    date_matches = re.findall(
        r"\b\d{1,2}/\d{1,2}/\d{4}\b",
        clean_text
    )

    if not date_matches:
        return None

    date = parse_date(
        date_matches[0]
    )

    if not date:
        return None

    # --------------------------------------------------------
    # Tìm ĐB
    # --------------------------------------------------------

    special = find_special_number(
        clean_text
    )

    if not special:
        return None

    return {
        "date": date,
        "special": special,
    }


# ============================================================
# PARSE RESULTS
# ============================================================

def parse_results(html):
    """
    Parse dữ liệu từ HTML.

    Có nhiều tầng fallback để tránh phụ thuộc
    vào một cấu trúc HTML duy nhất.
    """

    print(
        "[SCRAPER] Bắt đầu parse HTML..."
    )

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    print(
        f"[SCRAPER] HTML length: "
        f"{len(html)}"
    )

    # --------------------------------------------------------
    # Debug cơ bản
    # --------------------------------------------------------

    page_text = soup.get_text(
        "\n",
        strip=True
    )

    print(
        f"[SCRAPER] Text length: "
        f"{len(page_text)}"
    )

    print(
        f"[SCRAPER] Có 'XSMB': "
        f"{'XSMB' in page_text}"
    )

    print(
        f"[SCRAPER] Có 'ĐB': "
        f"{'ĐB' in page_text}"
    )

    print(
        f"[SCRAPER] Có 'Đặc biệt': "
        f"{'Đặc biệt' in page_text}"
    )

    # --------------------------------------------------------
    # Strategy 1:
    # Parse các block HTML
    # --------------------------------------------------------

    blocks = extract_candidate_blocks(
        soup
    )

    print(
        f"[SCRAPER] Candidate blocks: "
        f"{len(blocks)}"
    )

    results = []

    for block in blocks:

        text = block.get_text(
            "\n",
            strip=True
        )

        result = parse_block_text(
            text
        )

        if result:

            results.append(
                result
            )

    print(
        f"[SCRAPER] Block parser tìm thấy: "
        f"{len(results)} kết quả"
    )

    # --------------------------------------------------------
    # Strategy 2:
    # Fallback regex trên toàn bộ text
    #
    # Chỉ dùng nếu block parser không tìm được.
    # --------------------------------------------------------

    if not results:

        print(
            "[SCRAPER] Block parser không tìm thấy dữ liệu."
        )

        print(
            "[SCRAPER] Chuyển sang fallback parser..."
        )

        # Chuẩn hóa whitespace
        text = re.sub(
            r"[ \t]+",
            " ",
            page_text
        )

        # Tìm tất cả ngày
        date_matches = list(
            re.finditer(
                r"\b\d{1,2}/\d{1,2}/\d{4}\b",
                text
            )
        )

        print(
            f"[SCRAPER] Fallback tìm thấy "
            f"{len(date_matches)} ngày."
        )

        for index, date_match in enumerate(
            date_matches
        ):

            start = date_match.start()

            # Chỉ xét một vùng text sau ngày.
            #
            # Không để regex ăn toàn bộ trang.
            end = (
                date_matches[index + 1].start()
                if index + 1 < len(date_matches)
                else min(
                    len(text),
                    start + 5000
                )
            )

            block_text = text[
                start:end
            ]

            date = parse_date(
                date_match.group(0)
            )

            special = find_special_number(
                block_text
            )

            if date and special:

                results.append({
                    "date": date,
                    "special": special,
                })

    # --------------------------------------------------------
    # Loại bỏ dữ liệu lỗi / trùng ngày
    # --------------------------------------------------------

    unique = {}

    for item in results:

        date = item.get("date")
        special = item.get("special")

        if not date:
            continue

        if not special:
            continue

        if not re.fullmatch(
            r"\d{5}",
            special
        ):
            continue

        unique[date] = special

    results = [
        {
            "date": date,
            "special": special,
        }
        for date, special in unique.items()
    ]

    # --------------------------------------------------------
    # Sort mới nhất trước
    # --------------------------------------------------------

    results.sort(
        key=lambda item: item["date"],
        reverse=True
    )

    # --------------------------------------------------------
    # Giới hạn tối đa 100 ngày
    # --------------------------------------------------------

    results = results[
        :MAX_RESULTS
    ]

    # --------------------------------------------------------
    # Debug kết quả
    # --------------------------------------------------------

    print(
        f"[SCRAPER] Tổng kết quả hợp lệ: "
        f"{len(results)}"
    )

    if results:

        print(
            "[SCRAPER] Dữ liệu mới nhất:"
        )

        for item in results[:5]:

            print(
                f"  {item['date']} "
                f"-> {item['special']}"
            )

    else:

        print(
            "[SCRAPER] WARNING: "
            "Không parse được kết quả nào."
        )

        # In một đoạn text để debug trên Render.
        preview = page_text[:3000]

        print(
            "[SCRAPER] PAGE PREVIEW:"
        )

        print(
            preview
        )

    return results


# ============================================================
# UPDATE DATABASE
# ============================================================

def update_database():
    """
    Tải dữ liệu -> parse -> lưu database.

    Giữ nguyên tên hàm để bot.py hiện tại
    không cần thay đổi.
    """

    print(
        "========================================"
    )

    print(
        "[SCRAPER] BẮT ĐẦU UPDATE"
    )

    print(
        "========================================"
    )

    # --------------------------------------------------------
    # Fetch
    # --------------------------------------------------------

    html = fetch_page()

    # --------------------------------------------------------
    # Parse
    # --------------------------------------------------------

    results = parse_results(
        html
    )

    print(
        f"[SCRAPER] Parser trả về "
        f"{len(results)} kết quả."
    )

    if not results:

        raise RuntimeError(
            "Scraper không tìm thấy kết quả XSMB. "
            "Có thể website đã thay đổi cấu trúc "
            "hoặc đang trả về trang chống bot."
        )

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    count = 0

    errors = []

    for item in results:

        try:

            save_result(
                item["date"],
                item["special"]
            )

            count += 1

        except Exception as e:

            error_message = (
                f"{item['date']} -> "
                f"{repr(e)}"
            )

            print(
                "[SCRAPER] Lỗi save:",
                error_message
            )

            errors.append(
                error_message
            )

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    print(
        f"[SCRAPER] Đã xử lý: "
        f"{len(results)} kết quả."
    )

    print(
        f"[SCRAPER] save_result thành công: "
        f"{count}"
    )

    print(
        f"[SCRAPER] save_result lỗi: "
        f"{len(errors)}"
    )

    print(
        "========================================"
    )

    print(
        "[SCRAPER] KẾT THÚC UPDATE"
    )

    print(
        "========================================"
    )

    # Nếu toàn bộ save đều lỗi,
    # báo lỗi rõ ràng thay vì trả về 0.
    if count == 0 and errors:

        raise RuntimeError(
            "Đã lấy được dữ liệu nhưng "
            "không lưu được bản ghi nào vào database. "
            f"Lỗi đầu tiên: {errors[0]}"
        )

    return count


# ============================================================
# TEST LOCAL
# ============================================================

if __name__ == "__main__":

    try:

        count = update_database()

        print(
            f"[SCRAPER] Đã cập nhật "
            f"{count} kết quả."
        )

    except Exception as e:

        print(
            "[SCRAPER] FATAL ERROR:",
            repr(e)
        )

        raise
