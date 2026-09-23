def fetch_lottery_result(region, date_str):
    """
    Cào dữ liệu thực tế hỗ trợ đa tỉnh cho Miền Nam và Miền Trung
    """
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    d_str = dt.strftime("%d-%m-%Y")
    d_str_slash = dt.strftime("%d/%m/%Y")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'vi-VN,vi;q=0.9,en-US;q=0.8',
    }

    urls = []
    if region == 'mb':
        urls = [f"https://www.minhngoc.net.vn/ket-qua-xo-so/mien-bac/{d_str}.html"]
    elif region == 'mn':
        # Miền Nam và Trung có trên Minh Ngọc với cấu trúc chuẩn
        urls = [
            f"https://www.minhngoc.net.vn/ket-qua-xo-so/mien-nam/{d_str}.html",
            f"https://xosodaiphat.com/xs-mn-{d_str}.html"
        ]
    elif region == 'mt':
        urls = [
            f"https://www.minhngoc.net.vn/ket-qua-xo-so/mien-trung/{d_str}.html",
            f"https://xosodaiphat.com/xs-mt-{d_str}.html"
        ]

    for url in urls:
        try:
            res = requests.get(url, headers=headers, timeout=7)
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, 'html.parser')
                
                # Đối với Miền Nam và Miền Trung, giải đặc biệt nằm ở các cột của các tỉnh trong ngày.
                # Ta quét tất cả các ô có class chứa giải đặc biệt (gdb) hoặc dòng đặc biệt.
                cells = soup.find_all(['div', 'td', 'span'], class_=re.compile(r'(gdb|dacbiet|special)', re.I))
                
                for cell in cells:
                    text = cell.text.strip()
                    # Giải ĐB miền Nam/Trung có 6 chữ số (ví dụ: 123456), lấy 2 số cuối
                    match = re.search(r'\d{5,6}', text)
                    if match:
                        val = match.group(0)
                        return val[-2:]
                
                # Phương án quét phụ: Tìm các thẻ chứa chữ "Đặc biệt" hoặc "Giải ĐB"
                for tr in soup.find_all('tr'):
                    row_text = tr.text.lower()
                    if 'đặc biệt' in row_text or 'g.đb' in row_text:
                        # Lấy tất cả các số có 5 hoặc 6 chữ số trong dòng này
                        numbers = re.findall(r'\b\d{5,6}\b', tr.text)
                        if numbers:
                            # Lấy kết quả của tỉnh đầu tiên trong bảng ngày hôm đó
                            return numbers[0][-2:]
        except Exception:
            continue

    return None