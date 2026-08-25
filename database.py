import sqlite3
import threading

db_lock = threading.Lock()

def init_db():
    """Khởi tạo bảng lưu trữ kết quả xổ số"""
    with db_lock:
        conn = sqlite3.connect('xosomb.db')
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS results (
                date TEXT PRIMARY KEY,
                numbers TEXT
            )
        ''')
        conn.commit()
        conn.close()

def save_result(date_str, numbers):
    """Lưu hoặc cập nhật kết quả 1 ngày (Nhận 2 tham số: date_str và numbers)"""
    with db_lock:
        try:
            conn = sqlite3.connect('xosomb.db')
            cursor = conn.cursor()
            
            numbers_str = ",".join(numbers) if isinstance(numbers, list) else str(numbers)
            
            cursor.execute('''
                INSERT OR REPLACE INTO results (date, numbers)
                VALUES (?, ?)
            ''', (date_str, numbers_str))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"⚠️ Lỗi CSDL khi lưu ngày {date_str}: {e}", flush=True)
            return False

def get_results(limit=365):
    """Lấy danh sách kết quả xổ số gần nhất từ CSDL (Mặc định 365 ngày)"""
    with db_lock:
        try:
            conn = sqlite3.connect('xosomb.db')
            cursor = conn.cursor()
            cursor.execute('SELECT date, numbers FROM results ORDER BY date DESC LIMIT ?', (limit,))
            rows = cursor.fetchall()
            conn.close()
            
            results = []
            for date, numbers_str in rows:
                num_list = numbers_str.split(',') if numbers_str else []
                results.append({'date': date, 'numbers': num_list})
            return results
        except Exception as e:
            print(f"⚠️ Lỗi lấy dữ liệu CSDL: {e}", flush=True)
            return []

def get_full(limit=365):
    """Alias cho get_results để tương thích với predictor.py"""
    return get_results(limit=limit)

def get_date_range():
    """Lấy ngày cũ nhất và mới nhất có trong CSDL"""
    with db_lock:
        try:
            conn = sqlite3.connect('xosomb.db')
            cursor = conn.cursor()
            cursor.execute('SELECT MIN(date), MAX(date) FROM results')
            row = cursor.fetchone()
            conn.close()
            if row and row[0] and row[1]:
                return row[0], row[1]
            return None, None
        except Exception as e:
            print(f"⚠️ Lỗi lấy phạm vi ngày CSDL: {e}", flush=True)
            return None, None

def count_results():
    """Đếm tổng số ngày đã lưu trong CSDL"""
    with db_lock:
        try:
            conn = sqlite3.connect('xosomb.db')
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM results')
            count = cursor.fetchone()[0]
            conn.close()
            return count
        except Exception as e:
            print(f"⚠️ Lỗi đếm CSDL: {e}", flush=True)
            return 0

# Tự động khởi tạo DB khi module được import
init_db()