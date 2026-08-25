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
    """Lưu hoặc cập nhật kết quả 1 ngày (Nhận đúng 2 tham số: date_str và numbers)"""
    with db_lock:
        try:
            conn = sqlite3.connect('xosomb.db')
            cursor = conn.cursor()
            
            # Chuẩn hóa danh sách số thành chuỗi cách nhau bằng dấu phẩy
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

# Tự động khởi tạo database khi import file
init_db()